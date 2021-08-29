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

class ZMQHandler():
    def __init__(self, logging, rocks, mempool):
        if ('RPC_USER' not in os.environ
        or 'RPC_PASSWORD' not in os.environ
        or 'RPC_HOST' not in os.environ
        or 'RPC_PORT' not in os.environ) :
            raise Exception('Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')

        if 'ZMQ_PORT' not in os.environ or 'ZMQ_HOST' not in os.environ :
            raise Exception('Need to specify ZMQ_PORT and ZMQ_HOST environs')

        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" %
            (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.loop = asyncio.get_event_loop()
        self.zmqContext = zmq.asyncio.Context()

        self.zmqSubSocket = self.zmqContext.socket(zmq.SUB)
        self.zmqSubSocket.setsockopt(zmq.RCVHWM, 0)
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashblock")
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawtx")
        self.zmqSubSocket.connect("tcp://%s:%s" % (os.environ['ZMQ_HOST'] , os.environ['ZMQ_PORT']))
        self.logging = logging
        self.rocks = rocks
        self.mempool = mempool

    async def handle(self):
        self.logging.info('[ZMQ]: Starting to handel zmq topics')
        topic, body, seq = await self.zmqSubSocket.recv_multipart()
        self.logging.info('[ZMQ]: Body %s %s' % (topic, seq))
        sequence = "Unknown"
        if len(seq) == 4:
            sequence = str(struct.unpack('<I', seq)[-1])
        if topic == b"rawtx":
            ## Tx entering mempool
            self.logging.info('[ZMQ]: Recieved Raw TX')
            serialized_tx = self.rpc_connection.decoderawtransaction(binascii.hexlify(body).decode("utf-8"))
            self.rocks.write_mempool_tx(serialized_tx)
        if topic == b"hashblock":
            block_hash = binascii.hexlify(body).decode("utf-8")
            block = self.rpc_connection.getblock(block_hash)
            txs = block['tx']
            for tx in txs:
                serialized_tx = self.rpc_connection.gettransaction(tx)
                self.rocks.update_tx_conf_time(serialized_tx['txid'], int(time.time()))

        # await asyncio.sleep(2)
        asyncio.ensure_future(self.handle())

    def start(self):
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
        self.zmqContext.destroy()
