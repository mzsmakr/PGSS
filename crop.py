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
import raidnearby
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

init_crop_py = False
last_crop_all = np.zeros((10, 10, 3), np.uint8)

async def crop_img(fullpath_filename):
    global last_crop_all
    global init_crop_py
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
                refB = 156
                refG = 194
                refR = 252
                dif1 = pow(img[size['comp_y']][size['comp_x']][0] - refB,2)
                dif2 = pow(img[size['comp_y']][size['comp_x']][1] - refG,2)
                dif3 = pow(img[size['comp_y']][size['comp_x']][2] - refR,2)
                error = math.sqrt(dif1+dif2+dif3)
                LOG.debug('comp error:{} B:{}({}) G:{}({}) R:{}({})'.format(error, img[size['comp_y']][size['comp_x']][0], refB, img[size['comp_y']][size['comp_x']][1], refG, img[size['comp_y']][size['comp_x']][2],refR))               
#                        if (img[size['comp_y']][size['comp_x']] == [162, 193, 254]).all():
                if error <= 15:
                    LOG.info('screenshot with {}x{} found and raid'.format(width, height))
                    crop_all = img[size['crop_y1']:size['crop_y2'] + size['crop_h'], size['crop_x1']:size['crop_x3'] + size['crop_w']]
                    if init_crop_py == False:
                        last_crop_all = crop_all
                    s = cv2.norm(crop_all, last_crop_all, cv2.NORM_L1)
                    scale = size['crop_w']/1536
                    if s > 20000*scale or init_crop_py==False:
                        init_crop_py = True
                        crop1 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x1']:size['crop_x1']+size['crop_w']]
                        crop2 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x2']:size['crop_x2']+size['crop_w']]
                        crop3 = img[size['crop_y1']:size['crop_y1']+size['crop_h'], size['crop_x3']:size['crop_x3']+size['crop_w']]
                        crop4 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x1']:size['crop_x1']+size['crop_w']]
                        crop5 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x2']:size['crop_x2']+size['crop_w']]
                        crop6 = img[size['crop_y2']:size['crop_y2']+size['crop_h'], size['crop_x3']:size['crop_x3']+size['crop_w']]
                        if int(crop1.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_01.png', crop1)
                        if int(crop2.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_02.png', crop2)
                        if int(crop3.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_03.png', crop3)
                        if int(crop4.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_04.png', crop4)
                        if int(crop5.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_05.png', crop5)
                        if int(crop6.mean()) < 240:
                            cv2.imwrite(crop_save_path+filename+'_06.png', crop6)
                        last_crop_all = crop_all
                        LOG.info('New image. Cropped. s={} scale={}'.format(s,scale))
                    else:
                        LOG.info('Duplicate image. Not cropped. s={} scale={}'.format(s,scale))
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
        cv2.imwrite(save_file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
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

def exception_handler(loop, context):
    loop.default_exception_handler(context)
    exception = context.get('exception')
    if isinstance(exception, Exception):
        LOG.error("Found unhandeled exception. Stoping...")
        loop.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)
    loop.create_task(crop_task())
    loop.run_forever()
    loop.close()





