#!/usr/bin/env python3

import time
import binascii
import asyncio
import zmq
import zmq.asyncio
import signal
import struct
import sys
import os
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

SATS_PER_BTC = 100000000


class ZMQHandler():
    def __init__(self, logging, rocks, mempool_state):
        if ('RPC_USER' not in os.environ
            or 'RPC_PASSWORD' not in os.environ
            or 'RPC_HOST' not in os.environ
                or 'RPC_PORT' not in os.environ):
            raise Exception(
                'Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')

        if 'ZMQ_PORT' not in os.environ or 'ZMQ_HOST' not in os.environ:
            raise Exception('Need to specify ZMQ_PORT and ZMQ_HOST environs')

        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" %
                                               (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.loop = asyncio.get_event_loop()
        self.zmqContext = zmq.asyncio.Context()

        self.zmqSubSocket = self.zmqContext.socket(zmq.SUB)
        self.zmqSubSocket.setsockopt(zmq.RCVHWM, 0)
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashblock")
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawtx")
        self.zmqSubSocket.connect(
            "tcp://%s:%s" % (os.environ['ZMQ_HOST'], os.environ['ZMQ_PORT']))
        self.logging = logging
        self.rocks = rocks
        self.mempool_state = mempool_state

        # Keep a cache of txs entering and leaving the mempool for providing mempool stats
        self.mempool_txs = []

    def is_in_cache(self, txId):
        return len(filter(lambda tx: tx['txid'] == txId, self.mempool_txs)) > 0

    def average_fee(self):
        return sum(tx['fee'] for tx in self.mempool_txs) / len(self.mempool_txs)

    def average_fee_rate(self):
        return sum(tx['feerate'] for tx in self.mempool_txs) / len(self.mempool_txs)

    def mempool_size(self):
        return len(self.mempool_txs)

    def average_tx_size(self):
        return sum(tx['size'] for tx in self.mempool_txs) / len(self.mempool_txs)

    def evict_cache(self, txId):
        self.mempool_txs = list(
            filter(lambda tx: tx['txId'] != txId, self.mempool_txs))

    def add_tx(self, serialized_tx):
        try:
            # Skip coin base tx
            if len(serialized_tx['vin']) == 1 and 'coinbase' in serialized_tx['vin'][0]:
                return
            # Decode tx id and save in rocks
            fees = self.getTransactionFees(serialized_tx)
            fee_rate = fees / serialized_tx['size']
            # Delete inputs and outputs to perserve space
            serialized_tx.pop('vin', None)
            serialized_tx.pop('vout', None)
            serialized_tx.pop('hex', None)
            # Concat tx obj with mempool state
            tx = (
                {**{
                    'feerate': float(fee_rate),
                    'fee': float(fees),
                    'mempooldate': int(time.time()),
                    'mempoolgrowthrate': self.mempool_state.mempool_growth_rate_service.growth_rate,
                    'networkdifficulty': self.mempool_state.network_difficulty.network_difficulty,
                    'averageconfirmationtime': self.mempool_state.average_confirmation_time_service.average_confirmation_time,
                    'mempoolsize': self.mempool_size(),
                    'minerrevenue': self.mempool_state.miner_revenue_service.miner_revenue,
                    'totalhashrate': self.mempool_state.total_hash_rate_service.total_hash_rate,
                    'marketprice': self.mempool_state.market_price_service.market_price,
                    'dayofweek': self.mempool_state.date_service.day_of_week,
                    'hourofday': self.mempool_state.date_service.hour_of_day,
                    'monthofyear': self.mempool_state.date_service.month_of_year,
                    'averagemempoolfee': self.average_fee(),
                    'averagemempoolfeerate': self.average_fee_rate(),
                    'averagemempooltxsize': self.average_tx_size(),
                }, **serialized_tx})
            print(tx)
            self.rocks.write_mempool_tx(tx)

            # Do we need to update our cache
            if (not self.is_in_cache(serialized_tx['txId'])):
                self.mempool_txs.append(serialized_tx)

        except Exception as e:
            self.logging.error(
                '[Mempool Entries]: Failed to decode and persist tx ')

            self.logging.error(e)
            return

    def getInputValue(self, txid, vout):

        serialized_tx = self.rpc_connection.decoderawtransaction(
            self.rpc_connection.getrawtransaction(txid))
        output = next((d for (index, d) in enumerate(
            serialized_tx['vout']) if d["n"] == vout), None)
        return output['value']

    def getTransactionFees(self, tx):
        # Add up output values
        output_value = 0
        [output_value := output_value + vout['value'] for vout in tx['vout']]
        # Add up input values
        input_value = 0
        [input_value := input_value +
            self.getInputValue(vin['txid'], vin['vout']) for vin in tx['vin']]

        assert(input_value > output_value)
        return float((input_value - output_value) * SATS_PER_BTC)

    async def handle(self):
        self.logging.info('[ZMQ]: Starting to handel zmq topics')
        topic, body, seq = await self.zmqSubSocket.recv_multipart()
        self.logging.info('[ZMQ]: Body %s %s' % (topic, seq))
        sequence = "Unknown"
        if len(seq) == 4:
            sequence = str(struct.unpack('<I', seq)[-1])
        if topic == b"rawtx":
            # Tx entering mempool
            try:
                self.logging.info('[ZMQ]: Recieved Raw TX')
                serialized_tx = self.rpc_connection.decoderawtransaction(
                    binascii.hexlify(body).decode("utf-8"))
                # TODO use class cache for this check
                existing_tx = self.rocks.get_tx(serialized_tx['txid'])
                if existing_tx == None:
                    self.add_tx(serialized_tx)
            except Exception as e:
                self.logging.info('[ZMQ]: Failed to write mempool entry')
                self.logging.info(e)
        if topic == b"hashblock":
            block_hash = binascii.hexlify(body).decode("utf-8")
            block = self.rpc_connection.getblock(block_hash)
            # Skip coin base tx
            for txId in block['tx'][1:]:
                self.rocks.update_tx_conf_time(txId, int(time.time()))
                # Drop from local cache
                if (self.is_in_cache(txId)):
                    self.evict_cache(txId)
        asyncio.ensure_future(self.handle())

    def start(self):
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
        self.zmqContext.destroy()
