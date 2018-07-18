import sys
import cv2
import numpy as np
from pathlib import Path
import os
import shutil
import matching as mt
import database as db
import raidnearby as rs
import time
import math
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
from multiprocessing import Process
import asyncio
import math
from sys import argv
import importlib
import hashlib
import signal

LOG = getLogger('')

class FindFort:
    def __init__(self):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.unknown_image_path = os.getcwd() + '/unknown_img'
        self.url_image_path = os.getcwd() + '/url_img'

        self.success_img_path = os.getcwd() + '/success_img/'
        self.need_check_img_path = os.getcwd() + '/need_check_img/'
        self.not_find_img_pth = os.getcwd() + '/not_find_img/'
        self.raidnearby = rs.RaidNearby()

    def run_fortmatching(self, session, fort_fullpath_filename):
        p_url = Path(self.url_image_path)
        fort_filename = os.path.basename(fort_fullpath_filename)
        LOG.info('find fort for {}'.format(fort_filename))
        max_fort_id = 0
        max_value = 0.0
        max_url_fullpath_filename = ''

        parts = str(fort_filename.replace('.jpg', '').replace('.png', '')).split('_')

        if len(parts) >= 3:
            device = parts[len(parts) - 2]
            time = int(parts[len(parts) - 1])

            teleport_delay = 1
            index = 0
            for device_conf in self.config.DEVICE_LIST:
                if device_conf == device:
                    teleport_delay = self.config.TELEPORT_DELAYS[index]
                    break
                index += 1

            time_a = math.floor(time - (teleport_delay / 2))
            time_b = math.ceil(time + (teleport_delay / 2))

            device_location_a = db.get_device_location_history(session, time_a, device)
            device_location_b = db.get_device_location_history(session, time_b, device)
            device_location_c = db.get_device_location_history(session, time, device)

            limit_forts = []

            if device_location_a is not None:
                ids_a = db.get_fort_ids_within_range(session, None, 800, device_location_a.lat, device_location_a.lon)
                for fort_id in ids_a:
                    if fort_id not in limit_forts:
                        limit_forts.append(fort_id)

            if device_location_b is not None:
                ids_b = db.get_fort_ids_within_range(session, None, 800, device_location_b.lat, device_location_b.lon)
                for fort_id in ids_b:
                    if fort_id not in limit_forts:
                        limit_forts.append(fort_id)

            if device_location_c is not None:
                ids_c = db.get_fort_ids_within_range(session, None, 800, device_location_c.lat, device_location_c.lon)
                if ids_a is not ids_c and ids_b is not ids_c:
                    for fort_id in ids_c:
                        if fort_id not in limit_forts:
                            limit_forts.append(fort_id)

            LOG.debug('Matching with gyms: {}'.format(limit_forts))
        else:
            LOG.debug('Matching without location')
            limit_forts = None

        for url_fullpath_filename in p_url.glob('*'):

            url_filename = os.path.basename(url_fullpath_filename)
            url_filename, url_filename_ext = os.path.splitext(url_filename)

            if url_filename_ext != '.png' and url_filename_ext != '.jpg':
                continue

            if limit_forts is not None and len(limit_forts) != 0:
                if int(url_filename) not in limit_forts:
                    continue

            if url_filename_ext == '.jpg' or url_filename_ext == '.png':
                try:
                    result = mt.fort_image_matching(str(url_fullpath_filename), str(fort_fullpath_filename))
                except KeyboardInterrupt:
                    os.killpg(0, signal.SIGINT)
                    sys.exit(1)
                except:
                    LOG.error('Matching error with {}'.format(str(url_fullpath_filename)))
                else:
                    url_filename = os.path.basename(url_fullpath_filename)
                    fort_id, ext = os.path.splitext(url_filename)
        #            print('fort_id:',fort_id,'result:',result,'max_value:',max_value, 'max_fort_id:', max_fort_id)
                    if result >= max_value:
                        max_value = result
                        max_fort_id = fort_id
                        max_url_fullpath_filename = url_fullpath_filename
    #            await asyncio.sleep(0.01)

        LOG.info('fort_filename:{} max_fort_id: {} max_value: {}'.format(fort_filename,max_fort_id, max_value))
        img = cv2.imread(str(fort_fullpath_filename), 3)
        gym_image_id = self.raidnearby.get_gym_image_id(img)
        gym_image_fort_id = db.get_gym_image_fort_id(session, gym_image_id)
        if float(max_value) >= 0.7:
            LOG.info(str(fort_fullpath_filename))
            if int(max_fort_id) == int(gym_image_fort_id):
                LOG.info('This gym image is already trained')
                fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '_GymImages_' + str(gym_image_id) + '_' + '{:.3f}'.format(max_value) + '.png'
                url_result_file = os.getcwd() + '/success_img/Fort_'+str(max_fort_id) + '_url' + str(url_filename_ext)
                shutil.move(fort_fullpath_filename, fort_result_file)
                shutil.copy(max_url_fullpath_filename, url_result_file)
            else:
                unknown_fort_id = db.get_unknown_fort_id(session)
                LOG.info('gym_images id:{} fort_id:{} unknow_fort_id:{}'.format(gym_image_id,gym_image_fort_id,unknown_fort_id))
                if gym_image_fort_id == unknown_fort_id:
                    try:
                        db.update_gym_image(session,gym_image_id,max_fort_id)
                    except KeyboardInterrupt:
                        os.killpg(0, signal.SIGINT)
                        sys.exit(1)
                    except:
                        LOG.error('Error to update gym_images for gym_images.id:{} gym_images.fort_id:{}'.format(gym_image_id,max_fort_id))
                        fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '_GymImages_' + str(gym_image_id) + '_' + '{:.3f}'.format(max_value) + '.png'
                        url_result_file = os.getcwd() + '/not_find_img/Fort_'+str(max_fort_id) + '_url' + str(url_filename_ext)
                        shutil.move(fort_fullpath_filename, fort_result_file)
                        shutil.copy(max_url_fullpath_filename, url_result_file)
                        LOG.error('Successfully found fort fort_id:{}, but failed to updata gym_images database. Check not_find_img with the fort_id'.format(max_fort_id))
                    else:
                        fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '_GymImages_' + str(gym_image_id) + '_' + '{:.3f}'.format(max_value) + '.png'
                        url_result_file = os.getcwd() + '/success_img/Fort_'+str(max_fort_id) + '_url' + str(url_filename_ext)
                        process_img_path = os.getcwd() + '/process_img/Fort_' + str(max_fort_id) + '.png'
                        shutil.copy(fort_fullpath_filename, process_img_path)
                        shutil.move(fort_fullpath_filename, fort_result_file)
                        shutil.copy(max_url_fullpath_filename, url_result_file)
                        LOG.info('Successfully found fort id: {}'.format(max_fort_id))
                else:
                    LOG.info('The gym image is assigned as fort id:{}'.format(gym_image_fort_id))
                    LOG.info('Check not_find_img directory.')       
                    LOG.info('If the Fort_{}.png and Fort_{}_url.jpg in not_find_img are correct'.format(str(max_fort_id),str(max_fort_id)))
                    LOG.info('Run "python3.6 manualsubmit.py force"'.format(str(max_fort_id),str(max_fort_id)))
                    fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '_GymImages_' + str(gym_image_id) + '_' + '{:.3f}'.format(max_value) + '.png'
                    url_result_file = os.getcwd() + '/not_find_img/Fort_'+str(max_fort_id) + '_url' + str(url_filename_ext)
                    shutil.move(fort_fullpath_filename, fort_result_file)
                    shutil.copy(max_url_fullpath_filename, url_result_file)
        elif float(max_value) >= 0.60:
            fort_result_file = os.getcwd() + '/not_find_img/LowConfidence_Fort_' + str(max_fort_id) + '_GymImages_' + str(gym_image_id) + '_' + '{:.3f}'.format(max_value) + '.png'
            url_result_file = os.getcwd() + '/not_find_img/LowConfidence_Fort_'+str(max_fort_id) + '_url' + str(url_filename_ext)
            shutil.move(fort_fullpath_filename, fort_result_file)
            shutil.copy(max_url_fullpath_filename, url_result_file)
            LOG.info('Found fort id: {} but need to verify'.format(max_fort_id))
            LOG.info('If the Fort_{}.png and Fort_{}_url.jpg in not_find_img are correct'.format(str(max_fort_id),str(max_fort_id)))
            LOG.info('Run "python3.6 manualsubmit.py"'.format(str(max_fort_id),str(max_fort_id)))
        else:
            split = str(fort_filename).split('_')
            if len(split) == 4:
                fort_filename_real = split[0] + '_' + split[1] + '.png'
            else:
                fort_filename_real = fort_filename
            fort_result_file = os.getcwd() + '/not_find_img/' + str(fort_filename_real)
            url_result_file = os.getcwd() + '/not_find_img/'+str(max_fort_id) + str(url_filename_ext)
            shutil.move(fort_fullpath_filename, fort_result_file)
            shutil.copy(max_url_fullpath_filename, url_result_file)
            LOG.info('Can not find fort: {}, check the image in not_find_img'.format(max_fort_id))
    

    def findfort_main(self, raidscan, id):
        try:
            LOG.info('Find fort task started for process {}'.format(id + 1))

            # Check directories
            file_path = os.path.dirname(self.url_image_path+'/')
            if not os.path.exists(file_path):
                LOG.error('Cannot find url_img directory. Run downloadfortimg.py')
                LOG.error('to create the directory and download fort images')
                return

            # Create directories if not exists
            file_path = os.path.dirname(self.success_img_path)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            file_path = os.path.dirname(self.need_check_img_path)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            file_path = os.path.dirname(self.not_find_img_pth)
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            p = Path(self.unknown_image_path)

            process_count = self.config.FINDFORT_PROCESSES
            while True:
                LOG.debug('Run find fort task')
                new_img_count = 0
                for fort_fullpath_filename in p.glob('GymImage*.png'):
                    if process_count > 1 and not int(hashlib.md5(str(fort_fullpath_filename).encode('utf-8')).hexdigest(),
                                                     16) % process_count == id:
                        continue
                    new_img_count = new_img_count+1
                    session = db.Session()
                    self.run_fortmatching(session, fort_fullpath_filename)
                    session.close()
                if new_img_count != 0:
                    LOG.info('{} new fort image processed'.format(new_img_count))
                else:
                    LOG.debug('{} new fort image processed'.format(new_img_count))
                time.sleep(1)
        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            LOG.error('Unexpected Exception in findfort Process: {}'.format(e))
            if raidscan is not None:
                raidscan.restart_findfort(id)
            else:
                os.killpg(0, signal.SIGINT)
                sys.exit(1)