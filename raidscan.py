import sys
import datetime
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import time
import asyncio
import raidnearby
import findfort
import crop
import os

LOG = getLogger('')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(raidnearby.main()),
             loop.create_task(findfort.findfort_main()),
             loop.create_task(crop.crop_task())
             ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()


