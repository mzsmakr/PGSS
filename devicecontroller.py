import time
import database
import sys
import os
import subprocess
import random
from multiprocessing import Process, Manager, Lock, Pool
from multiprocessing.managers import BaseManager
from logging import getLogger
import importlib
from sys import argv
from geopy.distance import vincenty
from time import localtime, strftime
import signal
from functools import partial

LOG = getLogger('')


class TransferObject:

    def __init__(self):
        self.locked_forts = []
        self.forts_no_raid = []
        self.forts_no_boss = []

    def set_locked_forts(self, locked_forts):
        self.locked_forts = locked_forts

    def set_forts_no_raid(self, forts_no_raid):
        self.forts_no_raid = forts_no_raid

    def set_forts_no_boss(self, forts_no_boss):
        self.forts_no_boss = forts_no_boss

    def get_locked_forts(self):
        return self.locked_forts

    def get_forts_no_boss(self):
        return self.forts_no_boss

    def get_forts_no_raid(self):
        return self.forts_no_raid

class DBRaid:

    def __init__(self,id,fort_id,level,pokemon_id,time_spawn,time_battle,time_end):
        self.id = id
        self.fort_id = fort_id
        self.level = level
        self.pokemon_id = pokemon_id
        self.time_spawn = time_spawn
        self.time_battle = time_battle
        self.time_end = time_end

class DBFort:

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
            LOG.error('Failed to delete old device location history: {}'.format(e))
        time.sleep(600)


def update_raids_and_forts(t_obj, lock, forts):

    time.sleep(1)
    while True:
        try:
            LOG.debug('Updating Raids and checking Gyms')
            session = database.Session()
            raids = database.get_raids_for_forts(session, forts)
            db_raids = []
            for raid in raids:
                db_raids.append(DBRaid(raid.id,raid.fort_id,raid.level,raid.pokemon_id,raid.time_spawn,raid.time_battle,raid.time_end))
            session.commit()
            session.close()

            lock.acquire()
            locked_forts = t_obj.get_locked_forts()
            for fort_time in locked_forts:
                if fort_time.time <= time.time():
                    locked_forts.remove(fort_time)

            t_obj.set_locked_forts(locked_forts)

            forts_no_raid = []
            forts_no_boss = []

            for fort in forts:
                if fort in [fort_time.fort for fort_time in locked_forts]:
                    continue

                hasRaid = False
                for raid in db_raids:
                    if fort.id == raid.fort_id:
                        hasRaid = True
                        if (raid.pokemon_id is None or raid.pokemon_id == 0) and raid.time_battle <= time.time():
                            forts_no_boss.append(fort)
                        break
                if not hasRaid:
                    forts_no_raid.append(fort)

            random.shuffle(forts_no_boss)
            random.shuffle(forts_no_raid)

            t_obj.set_forts_no_raid(forts_no_raid)
            t_obj.set_forts_no_boss(forts_no_boss)
            lock.release()

            time.sleep(5)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            LOG.error('Failed to update Raids and Gyms: {}'.format(e))
            time.sleep(1)


def update_device_location(t_obj, lock, device, sleep):

    last_teleport = 0
    last_lat = 0
    last_lon = 0
    locked = False

    while True:

        try:
            LOG.debug('Running device controller task for {}'.format(device))

            fort = None

            lock.acquire()
            locked = True
            forts_no_boss = t_obj.get_forts_no_boss()
            forts_no_raid = t_obj.get_forts_no_raid()
            if len(forts_no_boss) > 0:
                fort = forts_no_boss.pop()
                t_obj.set_forts_no_boss(forts_no_boss)
            elif len(forts_no_raid) > 0:
                fort = forts_no_raid.pop()
                t_obj.set_forts_no_raid(forts_no_raid)

            if fort is not None:
                locked_forts = t_obj.get_locked_forts()
                locked_forts.append(FortTime(fort, time.time() + 120))
                t_obj.set_locked_forts(locked_forts)
                lock.release()
                locked = False

                FNULL = open(os.devnull, 'w')
                if fort.lat < 0:
                    lat_str = '-- {}'.format(fort.lat)
                else:
                    lat_str = str(fort.lat)

                if fort.lon < 0:
                    lon_str = '-- {}'.format(fort.lon)
                else:
                    lon_str = str(fort.lon)

                process = subprocess.Popen('idevicelocation -u {} {} {}'.format(device, lat_str, lon_str), shell=True,
                                           stdout=FNULL, stderr=FNULL)
                time_start = time.time()
                process.wait(5)
                time_end = time.time()

                last_tp_time = time_end - last_teleport
                delay = time_end - time_start
                last_teleport = time.time()

                distance = vincenty((last_lat, last_lon), (fort.lat, fort.lon)).meters
                last_lat = fort.lat
                last_lon = fort.lon

                LOG.info(
                    'Teleporting device with ID {} to {},{} over {:0.0f}m (delay: {:0.2f}s, last ago: {:0.2f}s)'.format(
                        device, fort.lat, fort.lon, distance, delay, last_tp_time))

                session = database.Session()
                database.add_device_location_history(session, device, time_end, fort.lat, fort.lon)
                session.close()

            else:
                lock.release()
                locked = False
                time_start = time.time()

            sleep_time = sleep - time.time() + time_start
            if sleep_time > 0:
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            if locked:
                lock.release()
            LOG.error('Failed to update device location for device {}: {}'.format(device, e))
            time.sleep(1)


def start_ui_test(device_uuid, log_path, derived_data_path, screenshot_delay):
    while True:
        try:
            process = None
            LOG.info('Starting UITest for Device {}'.format(device_uuid))
            path = os.path.dirname(os.path.realpath(__file__)) + '/../Control'
            log_file = log_path + '/{}_{}_xcodebuild.log'.format(strftime("%Y-%m-%d_%H-%M-%S", localtime()), device_uuid)
            stdout = open(log_file, 'w')
            process = subprocess.Popen('xcodebuild test -scheme \"RDRaidMapCtrl\" -destination \"id={}\" -derivedDataPath \"{}\" \"POKEMON={}\" \"UUID={}\" \"DELAY={}\"'.format(device_uuid, str(derived_data_path), 'false', device_uuid, str(screenshot_delay)), cwd=str(path), shell=True, stdout=stdout, stderr=stdout)
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


class DeviceController:

    def __init__(self, forts, devices):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.forts = forts
        self.devices = devices
        self.raid_updater_task = None
        logpath = os.getcwd() + '/logs/'
        self.log_path = os.path.dirname(logpath)
        if not os.path.exists(self.log_path):
            print('log directory created')
            os.makedirs(self.log_path)
        self.update_raids_process = None
        self.clean_process = None
        self.uitest_processes = []
        self.teleport_processes = []

    def devicecontroller_main(self, raidscan):

        BaseManager.register('TransferObject', TransferObject)
        BaseManager.register('Lock', Lock)
        manager = BaseManager()
        manager.start()

        t_obj = manager.TransferObject()
        lock = manager.Lock()

        try:
            self.clean_process = Process(target=clean_task)
            self.clean_process.start()

            self.update_raids_process = Process(target=update_raids_and_forts, args=(t_obj, lock,  self.forts, ))
            self.update_raids_process.start()

            index = 0
            for device in self.devices:
                uitest_process = Process(target=start_ui_test, args=(device, self.log_path, self.config.DERIVED_DATA_PATH, self.config.SCREENSHOT_DELAYS[index], ))
                uitest_process.start()
                self.uitest_processes.append(uitest_process)

                tp_process = Process(target=update_device_location, args=(t_obj, lock, device, self.config.TELEPORT_DELEAYS[index], ))
                tp_process.start()
                self.teleport_processes.append(tp_process)

                index += 1
                time.sleep(0.1)

            while True:
                time.sleep(60)

        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            LOG.error('Unexpected Exception in devicecontroller Process: {}'.format(e))

            if self.update_raids_process is not None:
                self.update_raids_process.terminate()
            for uitest_process in self.uitest_processes:
                uitest_process.terminate()
            for tp_process in self.teleport_processes:
                tp_process.terminate()

            if raidscan is not None:
                raidscan.restart_devicecontroller()
            else:
                os.killpg(0, signal.SIGINT)
                sys.exit(1)