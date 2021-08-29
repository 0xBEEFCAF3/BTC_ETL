import json
import rocksdb
import threading
import decimal

class MergeOp(rocksdb.interfaces.AssociativeMergeOperator):
    def merge(self, key, existing_tx, conf_ts):
        if existing_tx != None:
            tx = json.loads(existing_tx)
            # Don't over write a conf time
            if('conf' not in tx):
                tx['conf'] = conf_ts
            return (True, str(json.dumps(tx)).encode('ascii'))
        return (True, conf_ts)

    def name(self):
        return b'MergeOp'

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

class RocksDBClient():
    def __init__(self, lock, logging):
        opts = rocksdb.Options()
        opts.create_if_missing = True
        opts.max_open_files = 300000
        opts.write_buffer_size = 67108864
        opts.max_write_buffer_number = 3
        opts.target_file_size_base = 67108864
        opts.merge_operator = MergeOp()

        opts.table_factory = rocksdb.BlockBasedTableFactory(
            filter_policy=rocksdb.BloomFilterPolicy(10),
            block_cache=rocksdb.LRUCache(2 * (1024 ** 3)),
            block_cache_compressed=rocksdb.LRUCache(500 * (1024 ** 2)))

        self.db =  rocksdb.DB("test.db", opts)
        self.lock = lock
        self.logging = logging
        
    def get_tx(self, txid):
        tx = None
        self.lock.acquire() 
        try:
            tx = self.db.get(bytes(txid, encoding='utf-8'))
        except Exception as e:
            self.logging.info('[rocks]: Failed to get tx')
            self.logging.info(e)
        finally:
           self.lock.release() 
        return tx
    
    def write_mempool_tx(self, tx):
        self.lock.acquire() 
        try:
            self.db.put(
                bytes(tx['txid'], encoding='utf-8'),
                bytes(json.dumps(tx, cls=DecimalEncoder), encoding='utf-8'))
        except Exception as e:
            self.logging.info('[rocks]: Create mempool entry')
            self.logging.info(e)
        finally:
           self.lock.release() 

    def update_tx_conf_time(self, txid, conf_ts):
        self.lock.acquire() 
        try:
            tx = json.loads(self.db.get(bytes(txid, encoding='utf-8')))
            if tx == None or 'conf' in tx:
                return
            tx['conf'] = conf_ts
            self.db.put(
                bytes(txid, encoding='utf-8'),
                bytes(json.dumps(tx, cls=DecimalEncoder), encoding='utf-8')) 
        except Exception as e:
            self.logging.info('[rocks]: Could not perform merge')
            self.logging.info(e)
        finally:
            self.lock.release()

    def print_all_keys(self):
        it = self.db.iterkeys()
        it.seek_to_first()
        txs = list(it) 
        print(self.db.get(txs[0]))
        # print(  txs)
