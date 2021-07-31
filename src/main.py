#!/usr/bin/env python3 
import sys
import zeroMQ 
import threading



if __name__ == "__main__":
   
    if (sys.version_info.major, sys.version_info.minor) < (3, 5):
        print("This example only works with Python 3.5 and greater")
        sys.exit(1)
    dameon = zeroMQ.ZMQHandler()