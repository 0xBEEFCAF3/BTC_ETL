import asyncio
import requests
from enum import Enum
import datetime as dt
import json
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os


class BLOCK_CHAIN_API_RESOURCE(Enum):
    MEMPOOL_SIZE = 'https://api.blockchain.info/charts/mempool-size?timespan=5days&sampled=true&metadata=false&cors=true&format=json'
    MEMPOOL_GROWTH_RATE = 'https://api.blockchain.info/charts/mempool-growth?timespan=5days&sampled=true&metadata=false&cors=true&format=json'
    NETWORK_DIFFICULTY = 'https://api.blockchain.info/charts/difficulty?timespan=5days&sampled=true&metadata=false&cors=true&format=json'
    AVERAGE_CONFIRMATION_TIME = 'https://api.blockchain.info/charts/avg-confirmation-time?timespan=5days&sampled=true&metadata=false&cors=true&format=json'
    MEDIAN_CONFIRMATION_TIME = 'https://api.blockchain.info/charts/median-confirmation-time?timespan=5days&sampled=true&metadata=false&cors=true&format=json'
    MINER_REVENUE = 'https://api.blockchain.info/charts/miners-revenue?timespan=30days&sampled=true&metadata=false&cors=true&format=json'
    TOTAL_HASH_RATE = 'https://api.blockchain.info/charts/hash-rate?daysAverageString=7D&timespan=1year&sampled=true&metadata=false&cors=true&format=json'
    MARKET_PRICE = 'https://api.blockchain.info/charts/market-price?timespan=30days&sampled=true&metadata=false&cors=true&format=json'
    DAY_OF_WEEK = 'placeholder',
    HOUR_OF_DAY = 'placeholder',
    MONTH_OF_YEAR = 'placeholder',


class NetworkDifficulty():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection
        self.update()

    def update(self):
        self.network_difficulty = self.rpc_connection.getbestblockhash()


class BlockStats():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection

    def update(self, block_height):
        print(block_height)
        stats = self.rpc_connection.getblockstats(block_height)
        self.current_stats = stats
        return stats

        # self.avg_fee = stats['avgfee']
        # self.avg_fee_rate = stats['avgfeerate']
        # self.avg_tx_size = stats['avgtxsize']
        # self.fee_rate_percentiles_10 = stats['feerate_percentiles'][0]
        # self.fee_rate_percentiles_25 = stats['feerate_percentiles'][1]
        # self.fee_rate_percentiles_50 = stats['feerate_percentiles'][2]
        # self.fee_rate_percentiles_75 = stats['feerate_percentiles'][3]
        # self.fee_rate_percentiles_90 = stats['feerate_percentiles'][4]

        # self.max_fee = stats['maxfee']
        # self.max_fee_rate = stats['maxfeerate']
        # self.max_tx_size = stats['maxtxsize']
        # self.median_fee = stats['medianfee']
        # self.median_time = stats['mediantime']
        # self.median_tx_size = stats['mediantxsize']
        # self.min_fee = stats['minfee']
        # self.min_fee_rate = stats['minfeerate']
        # self.min_tx_size = stats['mintxsize']
        # self.min_tx_size = stats['mintxsize']

        # self.total_fee = stats['totalfee']


class MempoolState():
    def __init__(self, logging):
        if ('RPC_USER' not in os.environ
            or 'RPC_PASSWORD' not in os.environ
            or 'RPC_HOST' not in os.environ
                or 'RPC_PORT' not in os.environ):
            raise Exception(
                'Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')
        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" %
                                               (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))

        self.logging = logging

        self.resources = [BlockStats(
            self.rpc_connection), NetworkDifficulty(self.rpc_connection), ]

        self.loop = asyncio.get_event_loop()

    def get_resource(self, resource_uri):
        return requests.get(resource_uri).json()["values"][-1]["y"]

    def get_new_stats(self):
        best_block_hash = self.rpc_connection.getbestblockhash()
        stats = self.rpc_connection.getblockstats(best_block_hash)

        self.avg_fee = stats['avgfee']
        self.avg_fee_rate = stats['avgfeerate']
        self.avg_tx_size = stats['avgtxsize']
        self.fee_rate_percentiles_10 = stats['feerate_percentiles'][0]
        self.fee_rate_percentiles_25 = stats['feerate_percentiles'][1]
        self.fee_rate_percentiles_50 = stats['feerate_percentiles'][2]
        self.fee_rate_percentiles_75 = stats['feerate_percentiles'][3]
        self.fee_rate_percentiles_90 = stats['feerate_percentiles'][4]

        self.max_fee = stats['maxfee']
        self.max_fee_rate = stats['maxfeerate']
        self.max_tx_size = stats['maxtxsize']
        self.median_fee = stats['medianfee']
        self.median_time = stats['mediantime']
        self.median_tx_size = stats['mediantxsize']
        self.min_fee = stats['minfee']
        self.min_fee_rate = stats['minfeerate']
        self.min_tx_size = stats['mintxsize']
        self.min_tx_size = stats['mintxsize']

        self.total_fee = stats['totalfee']

    def get_resources(self):

        b = BlockStats(self.rpc_connection)

        # for resource in BLOCK_RESOURCE:
        #     if isinstance(resource.value, str):
        #         self.state[resource.name] = self.get_resource(resource.value)
        # self.state[BLOCK_RESOURCE.DAY_OF_WEEK.name] = dt.datetime.today().weekday()
        # self.state[BLOCK_RESOURCE.HOUR_OF_DAY.name] = dt.datetime.now().hour
        # self.state[BLOCK_RESOURCE.MONTH_OF_YEAR.name] = dt.datetime.now().month

    async def handle(self):
        self.logging.info('[Mempool State]: Starting gather mempool status')
        self.get_resources()
        self.logging.info(
            '[Mempool State]: Current mempool state ' + json.dumps(self.state))
        await asyncio.sleep(10)
        asyncio.ensure_future(self.handle())

    def start(self):
        print('Starting event loop')
        self.loop.create_task(self.handle())

    def stop(self):
        self.loop.stop()
