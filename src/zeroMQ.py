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

port = 28333
host = '192.168.1.168'
class ZMQHandler():
    def __init__(self, logging, rocks):
        if ('RPC_USER' not in os.environ
        or 'RPC_PASSWORD' not in os.environ
        or 'RPC_HOST' not in os.environ
        or 'RPC_PORT' not in os.environ) :
            raise Exception('Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')
        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" %
            (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.loop = asyncio.get_event_loop()
        self.zmqContext = zmq.asyncio.Context()

        self.zmqSubSocket = self.zmqContext.socket(zmq.SUB)
        self.zmqSubSocket.setsockopt(zmq.RCVHWM, 0)
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashblock")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashtx")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawblock")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "sequence")
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawtx")
        self.zmqSubSocket.connect("tcp://%s:%i" % (host, port))
        self.logging = logging
        self.rocks = rocks

    async def handle(self):
        self.logging.info('[ZMQ]: Starting to handel zmq topics')
        topic, body, seq = await self.zmqSubSocket.recv_multipart()
        self.logging.info('[ZMQ]: Body %s %s' % (topic, seq))
        sequence = "Unknown"
        if len(seq) == 4:
            sequence = str(struct.unpack('<I', seq)[-1])
        if topic == b"rawtx":
            self.logging.info('[ZMQ]: Recieved Raw TX')
            serialized_tx = self.rpc_connection.decoderawtransaction(binascii.hexlify(body).decode("utf-8") )
            self.rocks.update_tx_conf_time(serialized_tx['txid'], int(time.time()))
            print(serialized_tx)
        # if topic == b"hashblock":
        #     print('- HASH BLOCK ('+sequence+') -')
        #     print(binascii.hexlify(body))
        # elif topic == b"hashtx":
        #     print('- HASH TX  ('+sequence+') -')
        #     print(binascii.hexlify(body))
        # if topic == b"rawblock":
        #     print('- RAW BLOCK HEADER ('+sequence+') -')
        #     print(binascii.hexlify(body[:80]))
        # await asyncio.sleep(2)
        asyncio.ensure_future(self.handle())

    def start(self):
        print('Starting event loop')
        self.loop.add_signal_handler(signal.SIGINT, self.stop)
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
        self.zmqContext.destroy()
