import sys
from sys import argv
import datetime
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import time
import database
import asyncio
import raidnearby
import findfort
import devicecontroller
import crop
import os
import concurrent.futures
from multiprocessing import Process
from pathlib import Path
from shapely.geometry import Polygon, Point
from downloadfortimg import download_img
from devicecontroller import DBFort
import importlib

LOG = getLogger('')

class RaidScan:

    def __init__(self):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.all_forts_inside = []

        if self.config.SCAN_AREA is not None:

            LOG.info('Scan-Area is set! Getting Forts...')
            session = database.Session()
            all_forts = database.get_forts(session)

            all_forts_to_download = []

            session2 = database.Session()

            for fort in all_forts:
                if fort.lat is not None and fort.lon is not None and self.config.SCAN_AREA.contains(Point(fort.lat, fort.lon)):
                    self.all_forts_inside.append(DBFort(fort.id, fort.lat, fort.lon))

                    if fort.id not in all_forts_to_download:
                        all_forts_to_download.append(fort.id)

                    nearby_ids = database.get_fort_ids_within_range(session2, all_forts, 800, fort.lat, fort.lon)
                    for fort_id in nearby_ids:
                        if fort_id not in all_forts_to_download:
                            all_forts_to_download.append(fort_id)

            session2.close()

            LOG.info('Found {} Gyms Gyms in Scan-Area'.format(len(self.all_forts_inside)))

            for fort in all_forts:
                if fort.id in all_forts_to_download:
                    image_file = Path(os.getcwd() + '/url_img/' + str(fort.id) + '.jpg')
                    if not os.path.isfile(image_file) and fort.url is not None:
                        LOG.info(
                            'Found gym in Scan-Area without stored image! Downloading image for {}'.format(fort.id))
                        download_img(str(fort.url), str(image_file))

            if self.config.DEVICE_LIST is None:
                LOG.error('SCAN_AREA set but DEVICE_LIST is empty! Skipping')

            session.commit()
            session.close()
            time.sleep(1)

        if self.config.ENABLE_NEARBY:
            for i in range(self.config.NEARBY_PROCESSES):
                self.restart_nearby(i)
        if self.config.ENABLE_CROP:
            for i in range(self.config.CROP_PROCESSES):
                self.restart_crop(i)
        if self.config.ENABLE_FINDFORT:
            for i in range(self.config.FINDFORT_PROCESSES):
                self.restart_findfort(i)
        if self.config.ENABLE_CONTROL and self.config.SCAN_AREA is not None and self.config.DEVICE_LIST is not None:
            self.restart_devicecontroller()

    def restart_crop(self, id):
        time.sleep(1)
        try:
            crop_obj = crop.Crop()
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            LOG.error('Failed to init Crop: {}'.format(e))
            self.restart_crop(id)
            return
        crop_process = Process(target=crop_obj.crop_task, args=(self,id,))
        crop_process.start()

    def restart_nearby(self, id):
        time.sleep(1)
        try:
            raid_nearby = raidnearby.RaidNearby()
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            LOG.error('Failed to init RaidNearby: {}'.format(e))
            self.restart_nearby(id)
            return
        rn_process = Process(target=raid_nearby.main, args=(self,id,))
        rn_process.start()

    def restart_findfort(self, id):
        time.sleep(1)
        try:
            find_fort = findfort.FindFort()
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            LOG.error('Failed to init FindFort: {}'.format(e))
            self.restart_findfort(id)
            return
        ff_process = Process(target=find_fort.findfort_main, args=(self,id,))
        ff_process.start()

    def restart_devicecontroller(self):
        time.sleep(1)
        try:
            device_controller = devicecontroller.DeviceController(self.all_forts_inside, self.config.DEVICE_LIST)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            LOG.error('Failed to init DeviceController: {}'.format(e))
            self.restart_devicecontroller()
            return
        dc_process = Process(target=device_controller.devicecontroller_main, args=(self,))
        dc_process.start()

if __name__ == '__main__':
    main = RaidScan()
