import cv2
import numpy as np
from pathlib import Path
import os
import time
from logging import getLogger
import shutil
import math
import sys
from sys import argv
import importlib
import hashlib
import signal

LOG = getLogger('')


class Crop:

    def __init__(self):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        self.screenshot_path = Path(self.config.SCREENSHOT_SAVE_PATH)
        self.crop_save_path = os.getcwd() + '/process_img/'
        self.not_find_path = os.getcwd() + '/not_find_img/'
        self.web_server_path = os.getcwd()+'/webserver/'

        # Create directories if not exists
        file_path = os.path.dirname(self.crop_save_path)
        if not os.path.exists(file_path):
            LOG.info('process_img directory created')
            os.makedirs(file_path)

        # Create directories if not exists
        file_path = os.path.dirname(self.not_find_path)
        if not os.path.exists(file_path):
            LOG.info('not_find_img directory created')
            os.makedirs(file_path)

        # Create directories if not exists
        file_path = os.path.dirname(self.web_server_path)
        if not os.path.exists(file_path):
            LOG.info('not_find_img directory created')
            os.makedirs(file_path)

        self.init_crop_py = False
        self.last_crop1 = np.zeros((10, 10, 3), np.uint8)
        self.last_crop2 = np.zeros((10, 10, 3), np.uint8)
        self.last_crop3 = np.zeros((10, 10, 3), np.uint8)
        self.last_crop4 = np.zeros((10, 10, 3), np.uint8)
        self.last_crop5 = np.zeros((10, 10, 3), np.uint8)
        self.last_crop6 = np.zeros((10, 10, 3), np.uint8)
        self.diff_threshold = 10000

    def crop_img(self, fullpath_filename):
        
        now = datetime.datetime.now()
        unix_time = int(now.timestamp())
        file_update_time = int(os.stat(str(fullpath_filename)).st_mtime)
        if unix_time - file_update_time > 1800:
            LOG.info('Attachment File is too old')
            os.remove(fullpath_filename)
            return
 
        filename = os.path.basename(fullpath_filename)
        filename, ext = os.path.splitext(filename)
        img = cv2.imread(str(fullpath_filename), 3)

        if img is not None:
            if img.dtype == 'uint16':
                # print('16 bit image')
                img = (img / 256).astype('uint8')

            height, width, channels = img.shape
            find_size_config = False
            for size in self.config.RAID_NEARBY_SIZE:
                if width == size['width'] and height == size['height']:
                    find_size_config = True
                    LOG.debug('ext = {}'.format(ext))
                    ref_b = 156
                    ref_g = 194
                    ref_r = 252

                    dif3_1 = pow(img[size['comp3_y']][size['comp3_x']][0] - ref_b, 2)
                    dif3_2 = pow(img[size['comp3_y']][size['comp3_x']][1] - ref_g, 2)
                    dif3_3 = pow(img[size['comp3_y']][size['comp3_x']][2] - ref_r, 2)
                    error3 = math.sqrt(dif3_1+dif3_2+dif3_3)

                    dif2_1 = pow(img[size['comp2_y']][size['comp2_x']][0] - ref_b, 2)
                    dif2_2 = pow(img[size['comp2_y']][size['comp2_x']][1] - ref_g, 2)
                    dif2_3 = pow(img[size['comp2_y']][size['comp2_x']][2] - ref_r, 2)
                    error2 = math.sqrt(dif2_1+dif2_2+dif2_3)

                    dif1_1 = pow(img[size['comp1_y']][size['comp1_x']][0] - ref_b, 2)
                    dif1_2 = pow(img[size['comp1_y']][size['comp1_x']][1] - ref_g, 2)
                    dif1_3 = pow(img[size['comp1_y']][size['comp1_x']][2] - ref_r, 2)
                    error1 = math.sqrt(dif1_1+dif1_2+dif1_3)

                    LOG.debug('comp dif 3+:{}, dif 2:{}, dif 1:{} ' .format(error3, error2, error1))
                    scale = size['width'] / 1536
                    match = False
                    if error3 <= 15:
                        match = True
                        LOG.info('screenshot with {}x{} found with 3+ raids'.format(width, height))

                        crop1 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop3_x1']:size['crop3_x1']+size['crop_w']]
                        crop2 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop3_x2']:size['crop3_x2']+size['crop_w']]
                        crop3 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop3_x3']:size['crop3_x3']+size['crop_w']]
                        crop4 = img[size['crop_y2']:size['crop_y2']+size['crop_h'],
                                    size['crop3_x1']:size['crop3_x1']+size['crop_w']]
                        crop5 = img[size['crop_y2']:size['crop_y2']+size['crop_h'],
                                    size['crop3_x2']:size['crop3_x2']+size['crop_w']]
                        crop6 = img[size['crop_y2']:size['crop_y2']+size['crop_h'],
                                    size['crop3_x3']:size['crop3_x3']+size['crop_w']]

                    elif error2 <= 15:
                        match = True
                        LOG.info('screenshot with {}x{} found with 2 raids'.format(width, height))

                        crop1 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop2_x1']:size['crop2_x1']+size['crop_w']]
                        crop2 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop2_x2']:size['crop2_x2']+size['crop_w']]
                        crop3 = None
                        crop4 = None
                        crop5 = None
                        crop6 = None

                    elif error1 <= 15:
                        match = True
                        LOG.info('screenshot with {}x{} found with 1 raid'.format(width, height))

                        crop1 = img[size['crop_y1']:size['crop_y1']+size['crop_h'],
                                    size['crop1_x1']:size['crop1_x1']+size['crop_w']]
                        crop2 = None
                        crop3 = None
                        crop4 = None
                        crop5 = None
                        crop6 = None

                    if match:

                        if not self.init_crop_py:
                            self.last_crop1 = crop1
                            self.last_crop2 = crop2
                            self.last_crop3 = crop3
                            self.last_crop4 = crop4
                            self.last_crop5 = crop5
                            self.last_crop6 = crop6

                        if crop1 is not None and int(crop1.mean()) < 240:
                            if self.last_crop1 is not None and self.last_crop1.shape == crop1.shape:
                                s = cv2.norm(crop1, self.last_crop1, cv2.NORM_L1)
                                LOG.debug('crop1 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_01.png', crop1)
                                    self.last_crop1 = crop1
                                    LOG.debug('New Image. crop1 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_01.png', crop1)
                                self.last_crop1 = crop1
                                LOG.debug('New Image. crop1 saved.')
                        if crop2 is not None and int(crop2.mean()) < 240:
                            if self.last_crop2 is not None and self.last_crop2.shape == crop2.shape:
                                s = cv2.norm(crop2, self.last_crop2, cv2.NORM_L1)
                                LOG.debug('crop2 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_02.png', crop2)
                                    self.last_crop2 = crop2
                                    LOG.debug('New Image. crop2 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_02.png', crop2)
                                self.last_crop2 = crop2
                                LOG.debug('New Image. crop2 saved.')
                        if crop3 is not None and int(crop3.mean()) < 240:
                            if self.last_crop3 is not None and self.last_crop3.shape == crop3.shape:
                                s = cv2.norm(crop3, self.last_crop3, cv2.NORM_L1)
                                LOG.debug('crop3 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_03.png', crop3)
                                    self.last_crop3 = crop3
                                    LOG.debug('New Image. crop3 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_03.png', crop3)
                                self.last_crop3 = crop3
                                LOG.debug('New Image. crop3 saved.')
                        if crop4 is not None and int(crop4.mean()) < 240:
                            if self.last_crop4 is not None and self.last_crop4.shape == crop4.shape:
                                s = cv2.norm(crop4, self.last_crop4, cv2.NORM_L1)
                                LOG.debug('crop4 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_04.png', crop4)
                                    self.last_crop4 = crop4
                                    LOG.debug('New Image. crop4 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_04.png', crop4)
                                self.last_crop4 = crop4
                                LOG.debug('New Image. crop4 saved.')
                        if crop5 is not None and int(crop5.mean()) < 240:
                            if self.last_crop5 is not None and self.last_crop5.shape == crop5.shape:
                                s = cv2.norm(crop5, self.last_crop5, cv2.NORM_L1)
                                LOG.debug('crop5 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_05.png', crop5)
                                    self.last_crop5 = crop5
                                    LOG.debug('New Image. crop5 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_05.png', crop5)
                                self.last_crop5 = crop5
                                LOG.debug('New Image. crop5 saved.')
                        if crop6 is not None and int(crop6.mean()) < 240:
                            if self.last_crop6 is not None and self.last_crop6.shape == crop6.shape:
                                s = cv2.norm(crop6, self.last_crop6, cv2.NORM_L1)
                                LOG.debug('crop6 s={} scale={}'.format(s, scale))
                                if s >= self.diff_threshold*scale*scale or not self.init_crop_py:
                                    cv2.imwrite(self.crop_save_path+filename+'_06.png', crop6)
                                    self.last_crop6 = crop6
                                    LOG.debug('New Image. crop6 saved. s={} scale={}'.format(s, scale))
                            else:
                                cv2.imwrite(self.crop_save_path + filename + '_06.png', crop6)
                                self.last_crop6 = crop6
                                LOG.debug('New Image. crop6 saved.')

                        self.init_crop_py = True
                        break
                    else:
                        LOG.info('screenshot with {}x{} found without raid'.format(width, height))
    #                        os.remove(fullpath_filename)
            if not find_size_config:
                shutil.copy2(fullpath_filename, self.not_find_path+'Screen_' + str(width) + 'x' + str(height) + ext)
                LOG.info('No size matching config found in RAID_NEARBY_SIZE')
                LOG.info('Check not_find_img directory and add RAID_NEARBY_SIZE in config for the screenshot iamge')
            img = cv2.resize(img, None, fx=0.35, fy=0.35)
            save_file_path = self.web_server_path+'screenshot.jpg'
            cv2.imwrite(save_file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            os.remove(fullpath_filename)
            time.sleep(0.1)

    def crop_task(self, raidscan, task_id):
        try:
            LOG.info('Crop screenshot task started for process {}'.format(task_id+1))
            LOG.debug('Screenshot path:{}'.format(self.screenshot_path))
            process_count = self.config.CROP_PROCESSES
            while True:
                for fullpath_filename in self.screenshot_path.glob('*.jpg'):
                    if process_count > 1 and not \
                            int(hashlib.md5(str(fullpath_filename).encode('utf-8')).hexdigest(), 16)\
                            % process_count == task_id:
                        continue
                    self.crop_img(fullpath_filename)
                for fullpath_filename in self.screenshot_path.glob('*.png'):
                    if process_count > 1 and not \
                            int(hashlib.md5(str(fullpath_filename).encode('utf-8')).hexdigest(), 16)\
                            % process_count == task_id:
                        continue
                    self.crop_img(fullpath_filename)
                time.sleep(0.1)  # task runs every 0.1 seconds
        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            LOG.error('Unexpected Exception in crop Process: {}'.format(e))
            if raidscan is not None:
                raidscan.restart_crop(task_id)
            else:
                os.killpg(0, signal.SIGINT)
                sys.exit(1)
