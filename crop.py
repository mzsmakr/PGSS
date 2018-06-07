import cv2
import numpy as np
from pathlib import Path
import os
import time
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
from config import SCREENSHOT_SAVE_PATH, RAID_NEARBY_SIZE
import asyncio
import shutil

LOG = getLogger('')

async def crop_task():
    screenshot_path = Path(SCREENSHOT_SAVE_PATH)
    crop_save_path = os.getcwd() + '/process_img/'
    not_find_path = os.getcwd() + '/not_find_img/'
    LOG.info('Crop screenshot task started')
    LOG.info('Screenshot path:{}'.format(screenshot_path))
    while True:
        for fullpath_filename in screenshot_path.glob('*.png'):
            filename = os.path.basename(fullpath_filename)
            filename, ext = os.path.splitext(filename)
            img = cv2.imread(str(fullpath_filename),3)
            
            if img is not None:
                height, width, channels = img.shape

                find_size_config = False

                for size in RAID_NEARBY_SIZE:
                    if width == size['width'] and height == size['height']:
                        LOG.info('screenshot with {}x{} found'.format(width, height))
                        crop1 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x1']:size['crop_x1']+size['crop_w']]
                        crop2 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x2']:size['crop_x2']+size['crop_w']]
                        crop3 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x3']:size['crop_x3']+size['crop_w']]
                        crop4 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x1']:size['crop_x1']+size['crop_w']]
                        crop5 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x2']:size['crop_x2']+size['crop_w']]
                        crop6 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x3']:size['crop_x3']+size['crop_w']]
                        cv2.imwrite(crop_save_path+filename+'_01.png', crop1)
                        cv2.imwrite(crop_save_path+filename+'_02.png', crop2)
                        cv2.imwrite(crop_save_path+filename+'_03.png', crop3)
                        cv2.imwrite(crop_save_path+filename+'_04.png', crop4)
                        cv2.imwrite(crop_save_path+filename+'_05.png', crop5)
                        cv2.imwrite(crop_save_path+filename+'_06.png', crop6)
                        os.remove(fullpath_filename)
                        find_size_config = True
                if find_size_config == False:
                    shutil.move(fullpath_filename, not_find_path+'Screen_' + str(width) + 'x' + str(height) + '.png')
                    LOG.info('No size matching config found in RAID_NEARBY_SIZE')
                    LOG.info('Check not_find_img directory and add RAID_NEARBY_SIZE in config for the screenshot iamge')
        await asyncio.sleep(3) # task runs every 3 seconds



