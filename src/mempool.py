from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os
import asyncio
import signal

class MemPoolEntries():
    def __init__(self):
        if os.environ['RPC_USER'] == None
            or os.environ['RPC_PASS'] == None
            or os.environ['RPC_HOST'] == None
            or os.environ['RPC_PORT'] == None 
            raise Exception('Need to specify RPC_USER and RPC_PASS environs')
        self.rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" % 
            (os.environ['RPC_USER'], os.environ['RPC_PASS'],  os.environ['RPC_HOST'], os.environ['RPC_PORT']))
        self.loop = asyncio.get_event_loop()
        self.txcache = set()
        self.MAX_CACHE_SIZE = 50000 # 256 * 50000 = = 12800000B
    
    async def handle(self):
        # Grab mempool entries, verbosity false
        ## https://chainquery.com/bitcoin-cli/getrawmempool
        mempool = self.rpc_connection.getrawmempool(False)
        for txid in mempool:
            if txid in self.txcache
                continue
            if len(self.txcache) >= self.MAX_CACHE_SIZE:
                # Remove LRU entry
                pass
            self.txcache.add(txid)
            # Decode tx id and save in rocks
            tx = self.rpc_connection.gettransaction(txid)
            ## Save in rocks with current ts    
        await asyncio.sleep(0.1)
        syncio.ensure_future(self.handle())

    def start(self):
        self.loop.add_signal_handler(signal.SIGINT, self.stop)
        self.loop.create_task()

    def stop(self):
        ## TODO relsae locks and save to db
        self.loop.stop()

    