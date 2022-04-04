# Collect statistcal information from a starting block, traversing to gensis block

import json
import os
import sys
from mempoolState import BlockStatsService
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


class BlockStatsCollector():
    def __init__(self):
        if ('RPC_USER' not in os.environ
            or 'RPC_PASSWORD' not in os.environ
            or 'RPC_HOST' not in os.environ
                or 'RPC_PORT' not in os.environ):
            raise Exception(
                'Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')

        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s"
                                               % (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.blocks = []
        self.blockStatsService = BlockStatsService(self.rpc_connection)

    def save(self):
        with open('block_stats_dump.json', 'w') as outfile:
            outfile.write(json.dumps(self.blocks))

    def start(self, start_height, stop_height=0):
        height = start_height
        while True:
            self.blocks.append(self.blockStatsService.update(
                block_height=height))
            height -= 1
            if (height == stop_height):
                break
        self.save()


if __name__ == "__main__":
    if (sys.version_info.major, sys.version_info.minor) < (3, 5):
        print("Only works with Python 3.5 and greater")
        sys.exit(1)

    blockCollector = BlockStatsCollector()
    blockCollector.start(start_height=727_609, stop_height=717_609)
