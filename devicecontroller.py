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
import datetime
from functools import partial
import cv2
import numpy as np

LOG = getLogger('')


class TransferObject:

    def __init__(self):
        self.locked_forts = []
        self.forts_no_raid = []
        self.forts_no_raid_priority = []
        self.forts_no_boss = []
        self.forts = []
        self.teleport_locked = []

    def is_teleport_locked(self, index):
        return index in self.teleport_locked

    def add_teleport_lock(self, index):
        if index not in self.teleport_locked:
            self.teleport_locked.append(index)

    def remove_teleport_lock(self, index):
        if index in self.teleport_locked:
            self.teleport_locked.remove(index)

    def set_forts(self, forts):
        self.forts = forts

    def set_locked_forts(self, locked_forts):
        self.locked_forts = locked_forts

    def set_forts_no_raid(self, forts_no_raid):
        self.forts_no_raid = forts_no_raid

    def set_forts_no_raid_priority(self, forts_no_raid_priority):
        self.forts_no_raid_priority = forts_no_raid_priority

    def set_forts_no_boss(self, forts_no_boss):
        self.forts_no_boss = forts_no_boss

    def get_forts(self):
        return self.forts

    def get_locked_forts(self):
        return self.locked_forts

    def get_forts_no_boss(self):
        return self.forts_no_boss

    def get_forts_no_raid_priority(self):
        return self.forts_no_raid_priority

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

    def __init__(self, fort_id, time):
        self.fort_id = fort_id
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


def update_raids_and_forts(t_obj, lock, forts_static):

    time.sleep(1)
    while True:
        is_locked = False
        try:
            LOG.debug('Updating Raids and checking Gyms')
            session = database.Session()
            raids = database.get_raids_for_forts(session, forts_static)
            db_raids = []
            for raid in raids:
                db_raids.append(DBRaid(raid.id,raid.fort_id,raid.level,raid.pokemon_id,raid.time_spawn,raid.time_battle,raid.time_end))
            session.commit()
            session.close()

            lock.acquire()
            is_locked = True
            locked_forts = t_obj.get_locked_forts()
            for fort_time in locked_forts:
                if fort_time.time <= time.time():
                    locked_forts.remove(fort_time)

            t_obj.set_locked_forts(locked_forts)
            forts = t_obj.get_forts()

            forts_no_raid = []
            forts_no_raid_priority = []
            forts_no_boss = []

            for fort in forts:
                if fort.id in [fort_time.fort_id for fort_time in locked_forts]:
                    continue

                hasRaid = False
                for raid in db_raids:
                    if raid.time_end <= time.time():
                        continue

                    if fort.id == raid.fort_id:
                        hasRaid = True
                        if (raid.pokemon_id is None or raid.pokemon_id == 0) and raid.time_battle <= time.time():
                            if raid.time_battle + 1200 >= time.time():
                                forts_no_boss.append(fort)
                            else:
                                hasRaid = False
                        break
                if not hasRaid:
                    if time.time() - fort.updated >= 300:
                        forts_no_raid_priority.append(fort)
                    else:
                        forts_no_raid.append(fort)

            random.shuffle(forts_no_boss)
            random.shuffle(forts_no_raid_priority)
            random.shuffle(forts_no_raid)

            t_obj.set_forts_no_raid(forts_no_raid)
            t_obj.set_forts_no_raid_priority(forts_no_raid_priority)
            t_obj.set_forts_no_boss(forts_no_boss)
            lock.release()

            time.sleep(5)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            LOG.error('Failed to update Raids and Gyms: {}'.format(e))
            if is_locked:
                lock.release()
            time.sleep(1)


def is_raid_nearby(device_id, unix_time):
    web_img_path = os.getcwd() + '/web_img/'
    file_path = web_img_path + 'Device_' + device_id + '.png'
    file_update_time = int(os.stat(str(file_path)).st_mtime)
    if unix_time > file_update_time:
        # No new image after teleport
        return False

    img = cv2.imread(file_path,3)

    if img is None:
        return False

    if img.dtype == 'uint16':
        # print('16 bit image')
        img = (img / 256).astype('uint8')

    height, width, ch = img.shape
    scale = width/640

    height_ratio = 938/640
    height_nearby = width*height_ratio

    x1_p = 370/640
    x2_p = 550/640
    y1_p = (1136-367)/938
    y2_p = (1136-390)/938

    x1 = round(width*x1_p)
    x2 = round(width*x2_p)
    y1 = round(height - height_nearby*y1_p)
    y2 = round(height - height_nearby*y2_p)

    raid_bar = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(raid_bar, cv2.COLOR_BGR2HSV)

    # define range of blue color in HSV
    lower_blue = np.array([82, 63, 87])
    upper_blue = np.array([102, 110, 127])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    first = int(5*scale)
    last = int(5*scale)
    sum_255_count = int(1*scale)
    sum_0 = 0
    sum_255 = 0

    for i in range(mask.shape[0]):
        sum_horizontal = int(sum(mask[i, :])/(x2-x1))
        if i < first:
            sum_0 = sum_0 + sum_horizontal
        elif i >= mask.shape[0] - last:
            sum_0 = sum_0 + sum_horizontal
        else:
            if sum_horizontal == 255:
                sum_255 += 1

    if sum_0 == 0 and sum_255 >= sum_255_count:
        return True
    else:
        return False


def update_device_location(t_obj, lock, device, sleep, process_id):

    last_teleport = 0
    last_lat = 0
    last_lon = 0
    locked = False

    while True:

        try:

            is_boss = False

            LOG.debug('Running device controller task for {}'.format(device))

            fort = None

            lock.acquire()
            locked = True
            if t_obj.is_teleport_locked(process_id):
                lock.release()
                locked = False
                time.sleep(5)
                continue

            forts_no_boss = t_obj.get_forts_no_boss()
            forts_no_raid = t_obj.get_forts_no_raid()
            forts_no_raid_priority = t_obj.get_forts_no_raid_priority()
            forts_no_raid_all = forts_no_raid + forts_no_raid_priority
            forts = t_obj.get_forts()

            if len(forts_no_boss) > 0:
                fort = forts_no_boss[0]
            elif len(forts_no_raid_priority) > 0:
                fort = forts_no_raid_priority[0]
            elif len(forts_no_raid) > 0:
                fort = forts_no_raid[0]

            if fort is not None:

                session = database.Session()
                close_fort_ids = database.get_fort_ids_within_range(session, forts, 600, fort.lat, fort.lon)
                session.close()

                locked_forts = t_obj.get_locked_forts()
                index = 0
                for close_fort_id in close_fort_ids:
                    if index == 6:
                        break
                    index += 1

                    if close_fort_id in [fort.id for fort in forts_no_boss]:
                        lock_time = 60
                        close_forts = [fort for fort in forts_no_boss if fort.id == close_fort_id]
                        close_fort = close_forts[0]
                        forts_no_boss.remove(close_fort)
                    elif close_fort_id in [fort.id for fort in forts_no_raid_all]:
                        lock_time = 180
                        close_forts = [fort for fort in forts_no_raid_all if fort.id == close_fort_id]
                        close_fort = close_forts[0]
                        try: forts_no_raid.remove(close_fort)
                        except: pass
                        try: forts_no_raid_priority.remove(close_fort)
                        except: pass
                    else:
                        continue

                    locked_forts.append(FortTime(close_fort.id, time.time() + lock_time))
                    forts_fort = [fort for fort in forts if fort.id == close_fort_id]
                    forts_fort[0].updated = time.time()

                t_obj.set_forts_no_raid(forts_no_raid)
                t_obj.set_forts_no_raid_priority(forts_no_raid_priority)
                t_obj.set_forts_no_boss(forts_no_boss)
                t_obj.set_locked_forts(locked_forts)
                t_obj.set_forts(forts)
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

                raid_nearby_opened = False
                raid_nearby_wait_count = 0
                time.sleep(sleep-0.5)
                now = datetime.datetime.now()
                unix_time = int(now.timestamp())
                # Wait until new screenshot captured and raid nearby opened
                while raid_nearby_opened is False:
                    time.sleep(0.5)
                    raid_nearby_opened = is_raid_nearby(device, unix_time)
                    if t_obj.is_teleport_locked(process_id):
                        raid_nearby_opened = True
                    raid_nearby_wait_count += 1
                    if raid_nearby_wait_count%2==0:
                        LOG.info('Waiting device {} to open raid nearby at location {}, {}'.format(device, fort.lat, fort.lon))

                session = database.Session()
                database.add_device_location_history(session, device, time_end, fort.lat, fort.lon)
                session.close()

            else:
                lock.release()
                locked = False
                time_start = time.time()

            if is_boss:
                sleep_r = sleep + sleep
            else:
                sleep_r = sleep

            sleep_time = sleep_r - time.time() + time_start
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


def start_ui_test(device_uuid, log_path, derived_data_path, screenshot_delay, restart_delay, t_obj, index, lock, ):

    if len(argv) >= 2:
        config = importlib.import_module(str(argv[1]))
    else:
        config = importlib.import_module('config')

    if config.RAID_START_TIME is not None and config.RAID_END_TIME is not None:
        raid_start_time_hour = int(str(config.RAID_START_TIME).split(':')[0])
        raid_start_time_minute = int(str(config.RAID_START_TIME).split(':')[1])
        raid_end_time_hour = int(str(config.RAID_END_TIME).split(':')[0])
        raid_end_time_minute = int(str(config.RAID_END_TIME).split(':')[1])
        limit_time = True
    else:
        limit_time = False

    did_stop = False
    is_locked = False
    process = None

    while True:
        try:
            timestamp_start = time.time()
            path = os.path.dirname(os.path.realpath(__file__)) + '/../Control'
            log_file = log_path + '/{}_{}_xcodebuild.log'.format(strftime("%Y-%m-%d_%H-%M-%S", localtime()), device_uuid)
            stdout = open(log_file, 'w')
            if limit_time:
                now = datetime.datetime.now().astimezone()
                raid_start_date = now.replace(hour=raid_start_time_hour, minute=raid_start_time_minute)
                raid_end_date = now.replace(hour=raid_end_time_hour, minute=raid_end_time_minute)

                if not (raid_start_date < now and raid_end_date > now):
                    if not did_stop:
                        LOG.info('Stopping UITest for Device {} (Outside RAID_TIME)'.format(device_uuid))
                        lock.acquire()
                        is_locked = True
                        t_obj.add_teleport_lock(index)
                        lock.release()
                        is_locked = False
                        process = subprocess.Popen(
                            'xcodebuild test -scheme \"RDRaidMapCtrl\" -allowProvisioningUpdates -destination \"id={}\" -derivedDataPath \"{}\" \"TERMINATE=true\" \"CONFIGURATION_BUILD_DIR={}/Build/{}\"'.format(
                                device_uuid, str(derived_data_path), str(derived_data_path),  str(device_uuid)),
                            cwd=str(path), shell=True, stdout=stdout, stderr=stdout)
                        process.wait()
                        process = None
                        did_stop = True

                    time.sleep(60)
                    continue
                else:
                    if did_stop:
                        lock.acquire()
                        is_locked = True
                        t_obj.remove_teleport_lock(index)
                        lock.release()
                        is_locked = False
                        did_stop = False

            LOG.info('Starting UITest for Device {}'.format(device_uuid))
            process = subprocess.Popen('xcodebuild test -scheme \"RDRaidMapCtrl\" -allowProvisioningUpdates -destination \"id={}\" '
                                       '-derivedDataPath \"{}\" \"POKEMON={}\" \"UUID={}\" '
                                       '\"SCREENSHOT_DELAY={}\" \"RESTART_DELAY={}\" '
                                       '\"CONFIGURATION_BUILD_DIR={}/Build/{}\"'
                                       .format(device_uuid, str(derived_data_path), 'false', device_uuid,
                                               str(screenshot_delay), str(restart_delay), str(derived_data_path), str(device_uuid)), cwd=str(path), shell=True, stdout=stdout, stderr=stdout)
            if limit_time:
                process.wait(int(raid_end_date.timestamp() - now.timestamp()) + 1)
            else:
                process.wait()
            process = None
            timestamp_end = time.time()
            if timestamp_start + 60 > timestamp_end:
                LOG.error('UITest for Device {} ended after under 60 seconds (Check your latest xcodebuild.log)'.format(device_uuid))
            else:
                LOG.info('UITest for Device {} ended after {} seconds'.format(device_uuid, str(int(timestamp_end - timestamp_start))))
            
        
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
            if is_locked:
                lock.release()

            if process is not None:
                try:
                    process.terminate()
                except KeyboardInterrupt:
                    os.killpg(0, signal.SIGINT)
                    sys.exit(1)
                except: pass
            LOG.error('UITest Task for Device {} crashed with: {}'.format(device_uuid, e))
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
        t_obj.set_forts(self.forts)
        lock = manager.Lock()

        try:
            self.clean_process = Process(target=clean_task)
            self.clean_process.start()

            self.update_raids_process = Process(target=update_raids_and_forts, args=(t_obj, lock, self.forts, ))
            self.update_raids_process.start()

            index = 0
            for device in self.devices:
                uitest_process = Process(target=start_ui_test, args=(device, self.log_path, self.config.DERIVED_DATA_PATH, self.config.SCREENSHOT_DELAYS[index], self.config.RESTART_DELAYS[index], t_obj, index, lock, ))
                uitest_process.start()
                self.uitest_processes.append(uitest_process)

                tp_process = Process(target=update_device_location, args=(t_obj, lock, device, self.config.TELEPORT_DELAYS[index], index, ))
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
