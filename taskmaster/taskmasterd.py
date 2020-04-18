#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-c/--configuration <file> -- configuration file path (searches if not given)
"""

from time import sleep
from taskmaster.config import Config

class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf

    def run(self):
        while 1:
            print('running daemon')
            for k, v in self.conf['programs'].items():
                print(k, v)
            sleep(1)

def main():
    print("daemon - do not touch")
    config = Config()
    d = Taskmasterd(config.conf)
    while (1):
        d.run()
    
if __name__ == '__main__':
    main()