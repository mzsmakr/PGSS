import cv2
import numpy as np
from pathlib import Path
import os
import time
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
from config import SCREENSHOT_SAVE_PATH, RAID_NEARBY_SIZE
import asyncio
import shutil
import math
#import pdb; pdb.set_trace()

LOG = getLogger('')
screenshot_path = Path(SCREENSHOT_SAVE_PATH)
crop_save_path = os.getcwd() + '/process_img/'
not_find_path = os.getcwd() + '/not_find_img/'
web_server_path = os.getcwd()+'/webserver/'

# Create directories if not exists
file_path = os.path.dirname(crop_save_path)
if not os.path.exists(file_path):
    LOG.info('process_img directory created')
    os.makedirs(file_path)

# Create directories if not exists
file_path = os.path.dirname(not_find_path)
if not os.path.exists(file_path):
    LOG.info('not_find_img directory created')
    os.makedirs(file_path)

# Create directories if not exists
file_path = os.path.dirname(web_server_path)
if not os.path.exists(file_path):
    LOG.info('not_find_img directory created')
    os.makedirs(web_server_path)  

async def crop_img(fullpath_filename):
    filename = os.path.basename(fullpath_filename)
    filename, ext = os.path.splitext(filename)
    img = cv2.imread(str(fullpath_filename),3)

    if img is not None:
        if img.dtype == 'uint16':
            print('16 bit image')
            img = (img / 256).astype('uint8')
            
        height, width, channels = img.shape
        find_size_config = False
        for size in RAID_NEARBY_SIZE:
            if width == size['width'] and height == size['height']:
                find_size_config = True
                LOG.debug('ext = {}'.format(ext))
                if ext == '.jpg':
                    refB = 150
                else:
                    refB = 162                
                refG = 194
                refR = 252
                dif1 = pow(img[size['comp_y']][size['comp_x']][0] - refB,2)
                dif2 = pow(img[size['comp_y']][size['comp_x']][1] - refG,2)
                dif3 = pow(img[size['comp_y']][size['comp_x']][2] - refR,2)
                error = math.sqrt(dif1+dif2+dif3)
                LOG.debug('comp error:{} B:{}({}) G:{}({}) R:{}({})'.format(error, img[size['comp_y']][size['comp_x']][0], refB, img[size['comp_y']][size['comp_x']][1], refG, img[size['comp_y']][size['comp_x']][2],refR))               
#                        if (img[size['comp_y']][size['comp_x']] == [162, 193, 254]).all():
                if error <= 10:
                    LOG.info('screenshot with {}x{} found and raid'.format(width, height))
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
                else:
                    LOG.info('screenshot with {}x{} found without raid'.format(width, height))
#                        os.remove(fullpath_filename)
                break
        if find_size_config == False:
            shutil.copy2(fullpath_filename, not_find_path+'Screen_' + str(width) + 'x' + str(height) + ext)
            LOG.info('No size matching config found in RAID_NEARBY_SIZE')
            LOG.info('Check not_find_img directory and add RAID_NEARBY_SIZE in config for the screenshot iamge')
        img = cv2.resize(img, None, fx = 0.35, fy = 0.35) 
        save_file_path = web_server_path+'screenshot.jpg'
        cv2.imwrite(save_file_path, img)
        os.remove(fullpath_filename)
        await asyncio.sleep(0.1) 
    

async def crop_task():
    LOG.info('Crop screenshot task started')
    LOG.info('Screenshot path:{}'.format(screenshot_path))
    while True:
        for fullpath_filename in screenshot_path.glob('*.jpg'):
            await crop_img(fullpath_filename)
        for fullpath_filename in screenshot_path.glob('*.png'):
            await crop_img(fullpath_filename)
        await asyncio.sleep(0.2) # task runs every 0.2 seconds


