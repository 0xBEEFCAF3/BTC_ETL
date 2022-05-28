import asyncio
import requests
import os
import json
import datetime as dt
from enum import Enum
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

SATS_PER_BTC = 100000000


class MarketPriceService():
    resource_url = 'https://casa-crypto-price-service-staging.s3.amazonaws.com/v1/crypto-price-service.json'

    def __init__(self):
        self.update()

    def update(self):
        self.market_price = requests.get(self.resource_url).json()[
            "median"]["BTC"]["USD"]

        return self.market_price


class TotalHashRateService():
    resource_url = 'https://api.blockchain.info/charts/hash-rate?daysAverageString=7D&timespan=1year&sampled=true&metadata=false&cors=true&format=json'

    def __init__(self):
        self.update()

    def update(self):
        self.total_hash_rate = requests.get(self.resource_url).json()[
            "values"][-1]["y"]

        return self.total_hash_rate


class MinerRevenueService():
    resource_url = 'https://api.blockchain.info/charts/miners-revenue?timespan=5days&sampled=true&metadata=false&cors=true&format=json'

    def __init__(self):
        self.update()

    def update(self):
        self.miner_revenue = requests.get(self.resource_url).json()[
            "values"][-1]["y"]

        return self.miner_revenue


class MempoolGrowthRateService():
    resource_url = 'https://api.blockchain.info/charts/mempool-growth?timespan=5days&sampled=true&metadata=false&cors=true&format=json'

    def __init__(self):
        self.update()

    def update(self):
        self.growth_rate = requests.get(self.resource_url).json()[
            "values"][-1]["y"]

        return self.growth_rate


class AverageConfirmationService():
    resource_url = 'https://api.blockchain.info/charts/avg-confirmation-time?timespan=5days&sampled=true&metadata=false&cors=true&format=json'

    def __init__(self):
        self.update()

    def update(self):
        self.average_confirmation_time = requests.get(self.resource_url).json()[
            "values"][-1]["y"]

        return self.average_confirmation_time


class MedianConfirmationService():
    resource_url = 'https://api.blockchain.info/charts/median-confirmation-time?timespan=5days&sampled=true&metadata=false&cors=true&format=json'

    def __init__(self):
        self.update()

    def update(self):
        self.median_confirmation_time = requests.get(self.resource_url).json()[
            "values"][-1]["y"]

        return self.median_confirmation_time


class NetworkDifficultyService():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection
        self.update()

    def update(self):
        difficulty = self.rpc_connection.getbestblockhash()
        self.network_difficulty = difficulty
        return difficulty


class BlockStatsService():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection

    def update(self, block_height=None):
        if (block_height == None):
            block_height = self.rpc_connection.getblockcount()
        stats = self.rpc_connection.getblockstats(block_height)
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
        self.min_fee_rate = stats['minfeerate']
        self.median_fee = stats['medianfee']
        self.median_time = stats['mediantime']
        self.median_tx_size = stats['mediantxsize']
        self.min_fee = stats['minfee']
        self.min_tx_size = stats['mintxsize']
        self.total_fee = stats['totalfee']


class MempoolSizeService():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection
        self.update()

    def update(self):
        mempool_info = self.rpc_connection.getmempoolinfo()
        # Current tx count
        self.mempool_size = mempool_info['size']
        # Sum of all virtual transaction sizes as defined in BIP 141. Differs from actual serialized size because witness data is discounted
        self.average_mempool_tx_size = mempool_info['bytes'] / \
            mempool_info['size']


class MempoolFeeInfoService():
    def __init__(self, rpc_connection):
        self.rpc_connection = rpc_connection
        self.update()

    def update(self):
        mempool = self.rpc_connection.getrawmempool(True)
        running_fee = 0
        running_fee_rate = 0

        for txId in mempool:
            fee = mempool[txId]['fee'] * SATS_PER_BTC
            running_fee += fee
            running_fee_rate += fee / mempool[txId]['vsize']

        self.average_fee = running_fee / len(mempool)
        self.average_fee_rate = running_fee_rate / len(mempool)





class FeeService():
    resource_url = 'https://bitcoiner.live/api/fees/estimates/latest'

    def __init__(self):
        self.update()

    def update(self):
        response = requests.get(self.resource_url).json()
        # Sats per vbyte
        self.rates = [response['estimates']['30']['sat_per_vbyte'], response['estimates']['60']['sat_per_vbyte'],
                      response['estimates']['120']['sat_per_vbyte'], response['estimates']['180']['sat_per_vbyte'],
                      response['estimates']['360']['sat_per_vbyte'], response['estimates']['720']['sat_per_vbyte'], response['estimates']['1440']['sat_per_vbyte']]


class DatesService():
    def __init__(self):
        self.update()

    def update(self):
        self.day_of_week = dt.datetime.today().weekday()
        self.hour_of_day = dt.datetime.now().hour
        self.month_of_year = dt.datetime.now().month


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

        self.block_stats_service = BlockStatsService(self.rpc_connection)
        self.network_difficulty = NetworkDifficultyService(self.rpc_connection)
        self.date_service = DatesService()
        self.fee_service = FeeService()
        self.median_confirmation_time_service = MedianConfirmationService()
        self.average_confirmation_time_service = AverageConfirmationService()
        self.mempool_growth_rate_service = MempoolGrowthRateService()
        self.miner_revenue_service = MinerRevenueService()
        self.total_hash_rate_service = TotalHashRateService()
        self.market_price_service = MarketPriceService()
        self.mempool_size_service = MempoolSizeService(self.rpc_connection)
        self.mempool_fee_service = MempoolFeeInfoService(self.rpc_connection)

        self.resources = [self.block_stats_service, self.network_difficulty, self.date_service, self.fee_service, self.median_confirmation_time_service,
                          self.average_confirmation_time_service, self.mempool_growth_rate_service, self.miner_revenue_service, self.total_hash_rate_service, self.market_price_service, self.mempool_size_service, self.mempool_fee_service]

        self.loop = asyncio.get_event_loop()

    def get_resources(self):
        self.logging.info('[Mempool State]: Updating resources')
        for resource in self.resources:
            resource.update()

        self.logging.info('[Mempool State]: Done update resources')

    async def handle(self):
        self.logging.info('[Mempool State]: Starting gather mempool status')
        self.get_resources()
        await asyncio.sleep(10)
        asyncio.ensure_future(self.handle())

    def start(self):
        self.logging.info('[Mempool State]: Starting event loop')
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()
