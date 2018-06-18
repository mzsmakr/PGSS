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

            if img.dtype == 'uint16':
                img = (img / 256).astype('uint8')

            if img is not None:
                height, width, channels = img.shape
                find_size_config = False
                for size in RAID_NEARBY_SIZE:
                    if width == size['width'] and height == size['height']:
                        find_size_config = True
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
                        os.remove(fullpath_filename)
                        break
                if find_size_config == False:
                    shutil.move(fullpath_filename, not_find_path+'Screen_' + str(width) + 'x' + str(height) + '.png')
                    LOG.info('No size matching config found in RAID_NEARBY_SIZE')
                    LOG.info('Check not_find_img directory and add RAID_NEARBY_SIZE in config for the screenshot iamge')
                await asyncio.sleep(0.1) 
        await asyncio.sleep(3) # task runs every 3 seconds

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




