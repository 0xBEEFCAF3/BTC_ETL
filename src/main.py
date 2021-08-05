#!/usr/bin/env python3 
import sys
# import zeroMQ 
import threading
from mempool import MemPoolEntries
from rocksclient import RocksDBClient
import logging

if __name__ == "__main__":   
    if (sys.version_info.major, sys.version_info.minor) < (3, 5):
        print("Only works with Python 3.5 and greater")
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')

    lock = threading.Lock()
    rocks = RocksDBClient(lock)
    mempool = MemPoolEntries(lock, rocks)
    mempool.start()
    rocks.print_all_keys()

   

    