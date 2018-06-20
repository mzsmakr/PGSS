import sys
import datetime
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import time
import asyncio
import raidnearby
import findfort
import crop
import os
import concurrent.futures

LOG = getLogger('')

def exception_handler(loop, context):
    loop.default_exception_handler(context)
    exception = context.get('exception')
    if isinstance(exception, Exception):
        LOG.error("Found unhandeled exception. Stoping...")
        loop.stop()

if __name__ == '__main__':
    raid_nearby = raidnearby.RaidNearby()
    find_fort = findfort.FindFort()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)
    executor = concurrent.futures.ProcessPoolExecutor()
    loop.set_default_executor(executor)
    loop.create_task(raid_nearby.main())
    loop.create_task(find_fort.findfort_main())
    loop.create_task(crop.crop_task())
    loop.run_forever()
    loop.close()
