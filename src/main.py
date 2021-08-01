#!/usr/bin/env python3 
import sys
# import zeroMQ 
import threading
import logger
from rocksclient import RocksDBClient

if __name__ == "__main__":   
    if (sys.version_info.major, sys.version_info.minor) < (3, 5):
        print("Only works with Python 3.5 and greater")
        sys.exit(1)
    lock = threading.Lock()

    rocks = RocksDBClient(lock)
    rocks.batch_write_mempool_txs([{'txid': '1234'}])
    