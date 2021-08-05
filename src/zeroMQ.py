#!/usr/bin/env python3 

import binascii
import asyncio
import zmq
import zmq.asyncio
import signal
import struct
import sys

port = 28333
host = '192.168.1.168'
class ZMQHandler():
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.zmqContext = zmq.asyncio.Context()

        self.zmqSubSocket = self.zmqContext.socket(zmq.SUB)
        self.zmqSubSocket.setsockopt(zmq.RCVHWM, 0)
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashblock")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "hashtx")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawblock")
        self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "rawtx")
        # self.zmqSubSocket.setsockopt_string(zmq.SUBSCRIBE, "sequence")
        self.zmqSubSocket.connect("tcp://%s:%i" % (host, port))

    async def handle(self):
        topic, body, seq = await self.zmqSubSocket.recv_multipart()
        sequence = "Unknown"
        if len(seq) == 4:
            sequence = str(struct.unpack('<I', seq)[-1])
        elif topic == b"rawtx":
            print('- RAW TX ('+sequence+') -')
            print(binascii.hexlify(body))
        # if topic == b"hashblock":
        #     print('- HASH BLOCK ('+sequence+') -')
        #     print(binascii.hexlify(body))
        # elif topic == b"hashtx":
        #     print('- HASH TX  ('+sequence+') -')
        #     print(binascii.hexlify(body))
        # if topic == b"rawblock":
        #     print('- RAW BLOCK HEADER ('+sequence+') -')
        #     print(binascii.hexlify(body[:80]))
        
        # elif topic == b"sequence":
        #     hash = binascii.hexlify(body[:32])
        #     label = chr(body[32])
        #     mempool_sequence = None if len(body) != 32+1+8 else struct.unpack("<Q", body[32+1:])[0]
        #     print('- SEQUENCE ('+sequence+') -')
        #     print(hash, label, mempool_sequence)
        # schedule ourselves to receive the next message
        asyncio.ensure_future(self.handle())

    def start(self):
        print('Starting event loop')
        self.loop.add_signal_handler(signal.SIGINT, self.stop)
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
        self.zmqContext.destroy()
