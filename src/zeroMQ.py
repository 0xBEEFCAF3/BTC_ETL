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
from mempoolState import BLOCK_RESOURCE

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
                    'mempoolgrowthrate': self.mempool_state.state[BLOCK_RESOURCE.MEMPOOL_GROWTH_RATE.name],
                    'networkdifficulty': self.mempool_state.state[BLOCK_RESOURCE.NETWORK_DIFFICULTY.name],
                    'averageconfirmationtime': self.mempool_state.state[BLOCK_RESOURCE.AVERAGE_CONFIRMATION_TIME.name],
                    'mempoolsize': self.mempool_state.state[BLOCK_RESOURCE.MEMPOOL_SIZE.name],
                    'minerrevenue': self.mempool_state.state[BLOCK_RESOURCE.MINER_REVENUE.name],
                    'totalhashrate': self.mempool_state.state[BLOCK_RESOURCE.TOTAL_HASH_RATE.name],
                    'marketprice': self.mempool_state.state[BLOCK_RESOURCE.MARKET_PRICE.name],
                    'dayofweek': self.mempool_state.state[BLOCK_RESOURCE.DAY_OF_WEEK.name],
                    'hourofday': self.mempool_state.state[BLOCK_RESOURCE.HOUR_OF_DAY.name]
                }, **serialized_tx})
            print(tx)
            self.rocks.write_mempool_tx(tx)
        except:
            self.logging.error(
                '[Mempool Entries]: Failed to decode and persist tx ')
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
            for tx in block['tx'][1:]:
                self.rocks.update_tx_conf_time(tx, int(time.time()))
        asyncio.ensure_future(self.handle())

    def start(self):
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
        self.zmqContext.destroy()
