import time

import database
import sys
import os
import subprocess
import random
from multiprocessing import Process
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import importlib
from sys import argv
from geopy.distance import vincenty

LOG = getLogger('')

class DBFort():

    def __init__(self,id,lat,lon):
        self.id = id
        self.lat = lat
        self.lon = lon

class FortTime:

    def __init__(self, fort, time):
        self.fort = fort
        self.time = time


class DeviceController:

    def __init__(self, forts, devices):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.forts = forts
        self.locked_forts = []
        self.devices = devices
        self.session = database.Session()
        self.ui_test_tasts = []
        self.last_lat = 0
        self.last_lon = 0

    def start_ui_test(self, device_uuid):
        while True:
            try:
                process = None
                LOG.info('Starting UITest for Device {}'.format(device_uuid))
                path = os.path.dirname(os.path.realpath(__file__)) + '/../Control'
                FNULL = open(os.devnull, 'w')
                process = subprocess.Popen('xcodebuild test -scheme \"RDRaidMapCtrl\" -destination \"id={}\" -derivedDataPath \"{}\" \"POKEMON={}\" \"UUID={}\" \"DELAY={}\"'.format(device_uuid, str(self.config.DERIVED_DATA_PATH), 'false', device_uuid, str(self.config.SCREENSHOT_DELAY)), cwd=str(path), shell=True, stdout=FNULL, stderr=FNULL)
                process.wait()
                LOG.info('UITest for Device {} ended'.format(device_uuid))
            except KeyboardInterrupt:
                if process is not None:
                    try:
                        process.terminate()
                    except:
                        pass
                sys.exit(0)
            except Exception as e:
                if process is not None:
                    try:
                        process.terminate()
                    except:
                        pass
                LOG.info('UITest for Device {} crashed with: {}'.format(device_uuid, e))
            time.sleep(1)

    def clean_task(self):
        while True:
            try:
                LOG.info('Deleting old device location history')
                database.delete_old_device_location_history(self.session)
            except KeyboardInterrupt:
                sys.exit(0)
            except:
                LOG.info('Failed to delete old device location history')
            time.sleep(600)


    def teleport(self, device, lat, lon):
        FNULL = open(os.devnull, 'w')
        if lat < 0:
            lat_str = '-- {}'.format(lat)
        else:
            lat_str = str(lat)

        if lon < 0:
            lon_str = '-- {}'.format(lon)
        else:
            lon_str = str(lon)

        process = subprocess.Popen('idevicelocation -u {} {} {}'.format(device, lat_str, lon_str), shell=True, stdout=FNULL, stderr=FNULL)
        time_start = time.time()
        process.wait(5)
        time_end = time.time()

        distance = vincenty((self.last_lat, self.last_lon ), (lat, lon)).meters
        LOG.info('Teleporting device with ID {} to {},{} over {:0.0f}m (delay: {:0.2f}s)'.format(device, lat, lon, distance, time_end - time_start))

        self.last_lon = lon
        self.last_lat = lat
        database.add_device_location_history(self.session, device, time.time(), lat, lon)

    def update_device_locations(self):
        LOG.debug('Running device controller task')
        raids = database.get_raids_for_forts(self.session, self.forts)

        for fort_time in self.locked_forts:
            if fort_time.time <= time.time():
                self.locked_forts.remove(fort_time)

        forts_no_raid = []
        forts_no_boss = []


        for fort in self.forts:

            if fort in [fort_time.fort for fort_time in self.locked_forts]:
                continue

            hasRaid = False
            for raid in raids:
                if fort.id == raid.fort_id:
                    hasRaid = True
                    if (raid.pokemon_id is None or raid.pokemon_id == 0) and raid.time_battle <= time.time():
                        forts_no_boss.append(fort)
                    break
            if not hasRaid:
                forts_no_raid.append(fort)

        for device in self.devices:
            fort = None
            if len(forts_no_boss) > 0:
                random.shuffle(forts_no_boss)
                fort = forts_no_boss.pop()
            elif len(forts_no_raid) > 0:
                random.shuffle(forts_no_raid)
                fort = forts_no_raid.pop()

            if fort is not None:
                self.locked_forts.append(FortTime(fort, time.time() + 120))
                self.teleport(device, fort.lat, fort.lon)

    def devicecontroller_main(self, raidscan):

        try:
            clean_process = Process(target=self.clean_task)
            clean_process.start()
            for device in self.devices:
                uitest_process = Process(target=self.start_ui_test, args=(device,))
                uitest_process.start()
                self.ui_test_tasts.append(uitest_process)
            while True:
                self.update_device_locations()
                time.sleep(self.config.TELEPORT_DELEAY)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            LOG.error('Unexpected Exception in devicecontroller Process: {}'.format(e))
            for uitest_process in self.ui_test_tasts:
                uitest_process.terminate()
            if raidscan is not None:
                raidscan.restart_devicecontroller()
            else:
                sys.exit(1)