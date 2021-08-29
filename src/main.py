#!/usr/bin/env python3 
import sys
from zeroMQ import ZMQHandler 
import threading
from rocksclient import RocksDBClient
from mempoolState import MempoolState
import logging

if __name__ == "__main__":   
    if (sys.version_info.major, sys.version_info.minor) < (3, 5):
        print("Only works with Python 3.5 and greater")
        sys.exit(1)
    thread_pool = []
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')
    lock = threading.Lock()
    rocks = RocksDBClient(lock, logging)
    mempoolState = MempoolState(logging)
    mempoolState.start()
    zeroMQ = ZMQHandler(logging, rocks, mempoolState)
    zeroMQ.start()
    
    ## Set up threads
    # mempoolState.get_resources();
    # thread_pool.append(threading.Thread(target=mempoolState.start))
    # thread_pool.append(threading.Thread(target=zeroMQ.start))
    # for t in thread_pool:
    #     t.start()

    # for index, t in enumerate(thread_pool):
    #     t.join()
    


   

    