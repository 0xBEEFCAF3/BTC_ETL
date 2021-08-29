from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os
import asyncio
import signal
import time
import logging
from mempoolState import BLOCK_RESOURCE

SATS_PER_BTC = 100000000

class MemPoolEntries():
    def __init__(self, logging, lock, rocksdb, mempoolState):
        if ('RPC_USER' not in os.environ
        or 'RPC_PASSWORD' not in os.environ
        or 'RPC_HOST' not in os.environ
        or 'RPC_PORT' not in os.environ) :
            raise Exception('Need to specify RPC_USER and RPC_PASSWORD, RPC_HOST, RPC_PORT environs')
        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" %
            (os.environ['RPC_USER'], os.environ['RPC_PASSWORD'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.loop = asyncio.get_event_loop()
        self.txcache = set()
        self.MAX_CACHE_SIZE = 50000 # 256 * 50000 = = 12800000B
        self.lock = lock
        self.rocksDbClient = rocksdb
        self.mempoolState = mempoolState
        self.logging = logging

    def getInputValue(self, txid, vout):
        serialized_tx = self.rpc_connection.decoderawtransaction(self.rpc_connection.getrawtransaction(txid))
        output = next((d for (index, d) in enumerate(serialized_tx['vout']) if d["n"] == vout), None)
        return output['value']

    def getTransactionFees(self, tx):
        ## Add up output values
        output_value = 0
        [output_value:= output_value + vout['value'] for vout in tx['vout']]
        ## Add up input values
        input_value = 0
        [input_value:= input_value + self.getInputValue(vin['txid'], vin['vout']) for vin in tx['vin']]

        assert(input_value > output_value)
        return float((input_value - output_value) * SATS_PER_BTC)


    def add_tx(self, txid):
        try:
            if txid in self.txcache:
                return
            if len(self.txcache) >= self.MAX_CACHE_SIZE:
                # TODO Remove LRU entry
                pass
            self.txcache.add(txid)
            #Decode tx id and save in rocks
            serialized_tx = self.rpc_connection.decoderawtransaction(self.rpc_connection.getrawtransaction(txid))
            fees = self.getTransactionFees(serialized_tx)
            fee_rate = fees / serialized_tx['size']
            tx = (
                {**{
                'feerate': float(fee_rate),
                'fee': float(fees),
                'mempooldate': int(time.time()),
                'mempoolgrowthrate': self.mempoolState.state[BLOCK_RESOURCE.MEMPOOL_GROWTH_RATE.name],
                'networkdifficulty': self.mempoolState.state[BLOCK_RESOURCE.NETWORK_DIFFICULTY.name],
                'averageconfirmationtime': self.mempoolState.state[BLOCK_RESOURCE.AVERAGE_CONFIRMATION_TIME.name],
                'mempoolsize': self.mempoolState.state[BLOCK_RESOURCE.MEMPOOL_SIZE.name],
                'minerrevenue': self.mempoolState.state[BLOCK_RESOURCE.MINER_REVENUE.name],
                'totalhashrate': self.mempoolState.state[BLOCK_RESOURCE.TOTAL_HASH_RATE.name],
                'marketprice': self.mempoolState.state[BLOCK_RESOURCE.MARKET_PRICE.name],
                }, **serialized_tx})
            self.rocksDbClient.write_mempool_tx(tx)
        except:
            self.logging.error('[Mempool Entries]: Failed to decode and persist tx %s' % txid)
            
            return

    async def handle(self):
        # Grab mempool entries, verbosity false
        ## https://chainquery.com/bitcoin-cli/getrawmempool
        mempool = self.rpc_connection.getrawmempool(False)
        self.logging.info('[Mempool Entries]: iterating through %i txs' % len(mempool))
        for txid in mempool[:100]:
            self.add_tx(txid)
            
        # await asyncio.sleep(20)
        # asyncio.ensure_future(self.handle())

    def start(self):
        self.loop.create_task(self.handle())
        self.loop.run_forever()

    def stop(self):
        self.loop.stop()

    