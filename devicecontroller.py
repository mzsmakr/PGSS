import time

import database
import sys
import os
import subprocess
import random
from multiprocessing import Process, Queue
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import importlib
from sys import argv
from geopy.distance import vincenty
from time import localtime, strftime
import signal

LOG = getLogger('')

class DBRaid():

    def __init__(self,id,fort_id,level,pokemon_id,time_spawn,time_battle,time_end):
        self.id = id
        self.fort_id = fort_id
        self.level = level
        self.pokemon_id = pokemon_id
        self.time_spawn = time_spawn
        self.time_battle = time_battle
        self.time_end = time_end

class DBFort():

    def __init__(self,id,lat,lon,updated):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.updated = updated

class FortTime:

    def __init__(self, fort, time):
        self.fort = fort
        self.time = time


def clean_task():
    while True:
        try:
            LOG.info('Deleting old device location history')
            session = database.Session()
            database.delete_old_device_location_history(session)
            session.close()
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            LOG.info('Failed to delete old device location history: {}'.format(e))
        time.sleep(600)


def update_raids(queue, forts):
    while True:
        try:
            LOG.info('Updating Raids')
            session = database.Session()
            raids = database.get_raids_for_forts(session, forts)
            db_raids = []
            for raid in raids:
                db_raids.append(DBRaid(raid.id,raid.fort_id,raid.level,raid.pokemon_id,raid.time_spawn,raid.time_battle,raid.time_end))
            session.commit()
            session.close()
            queue.put(db_raids)
            time.sleep(30)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            LOG.info('Failed to update Raids: {}'.format(e))
            time.sleep(5)

class DeviceController:

    def __init__(self, forts, devices):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.forts = forts
        self.locked_forts = []
        self.devices = devices
        self.raid_updater_task = None
        self.last_lat = 0
        self.last_lon = 0
        logpath = os.getcwd() + '/logs/'
        self.log_path = os.path.dirname(logpath)
        if not os.path.exists(self.log_path):
            print('log directory created')
            os.makedirs(self.log_path)
        self.raids = []
        self.last_teleport_delays = []
        self.last_teleport = 0
        self.update_raids_queue = None
        self.update_raids_process = None
        self.uitest_processes = []
        self.time_start = time.time()

    def start_ui_test(self, device_uuid):
        while True:
            try:
                process = None
                LOG.info('Starting UITest for Device {}'.format(device_uuid))
                path = os.path.dirname(os.path.realpath(__file__)) + '/../Control'
                log_file = self.log_path + '/{}_{}_xcodebuild.log'.format(strftime("%Y-%m-%d_%H-%M-%S", localtime()), device_uuid)
                stdout = open(log_file, 'w')
                process = subprocess.Popen('xcodebuild test -scheme \"RDRaidMapCtrl\" -destination \"id={}\" -derivedDataPath \"{}\" \"POKEMON={}\" \"UUID={}\" \"DELAY={}\"'.format(device_uuid, str(self.config.DERIVED_DATA_PATH), 'false', device_uuid, str(self.config.SCREENSHOT_DELAY)), cwd=str(path), shell=True, stdout=stdout, stderr=stdout)
                process.wait()
                LOG.info('UITest for Device {} ended'.format(device_uuid))
            except KeyboardInterrupt:
                if process is not None:
                    try:
                        process.terminate()
                    except KeyboardInterrupt:
                        os.killpg(0, signal.SIGINT)
                        sys.exit(1)
                    except: pass
                os.killpg(0, signal.SIGINT)
                sys.exit(1)
            except Exception as e:
                if process is not None:
                    try:
                        process.terminate()
                    except KeyboardInterrupt:
                        os.killpg(0, signal.SIGINT)
                        sys.exit(1)
                    except: pass
                LOG.info('UITest for Device {} crashed with: {}'.format(device_uuid, e))
            time.sleep(1)

    def teleport(self, device, lat, lon, session):

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

        last_tp_time = time.time() - self.last_teleport
        self.last_teleport = time.time()

        LOG.info('Teleporting device with ID {} to {},{} over {:0.0f}m (delay: {:0.2f}s, last ago: {:0.2f}s)'.format(device, lat, lon, distance, time_end - time_start, last_tp_time))

        self.last_lon = lon
        self.last_lat = lat
        database.add_device_location_history(session, device, time.time(), lat, lon)

    def update_device_locations(self):

        LOG.debug('Running device controller task')

        while not self.update_raids_queue.empty():
            self.raids = self.update_raids_queue.get()

        for fort_time in self.locked_forts:
            if fort_time.time <= time.time():
                self.locked_forts.remove(fort_time)

        forts_no_raid = []
        forts_no_boss = []

        for fort in self.forts:
            if fort in [fort_time.fort for fort_time in self.locked_forts]:
                continue

            hasRaid = False
            for raid in self.raids:
                if fort.id == raid.fort_id:
                    hasRaid = True
                    if (raid.pokemon_id is None or raid.pokemon_id == 0) and raid.time_battle <= time.time():
                        forts_no_boss.append(fort)
                    break
            if not hasRaid:
                forts_no_raid.append(fort)

        time_to_wait = (self.config.TELEPORT_DELEAY + self.time_start - time.time())
        if time_to_wait > 0:
            time.sleep(time_to_wait)

        self.time_start = time.time()

        for device in self.devices:
            fort = None
            if len(forts_no_boss) > 0:
                random.shuffle(forts_no_boss)
                fort = forts_no_boss.pop()
            elif len(forts_no_raid) > 0:
                random.shuffle(forts_no_raid)
                fort = forts_no_raid.pop()

            session = database.Session()
            if fort is not None:
                self.locked_forts.append(FortTime(fort, time.time() + 120))
                self.teleport(device, fort.lat, fort.lon, session)
            session.close()


    def devicecontroller_main(self, raidscan):
        try:
            clean_process = Process(target=clean_task)
            clean_process.start()

            self.update_raids_queue = Queue()
            self.update_raids_process = Process(target=update_raids, args=(self.update_raids_queue, self.forts, ))
            self.update_raids_process.start()

            for device in self.devices:
                uitest_process = Process(target=self.start_ui_test, args=(device,))
                uitest_process.start()
                self.uitest_processes.append(uitest_process)
                time.sleep(1)

            while True:
                self.update_device_locations()

        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            LOG.error('Unexpected Exception in devicecontroller Process: {}'.format(e))
            if self.update_raids_process is not None:
                self.update_raids_process.terminate()
            for uitest_process in self.uitest_processes:
                uitest_process.terminate()

            if raidscan is not None:
                raidscan.restart_devicecontroller()
            else:
                os.killpg(0, signal.SIGINT)
                sys.exit(1)