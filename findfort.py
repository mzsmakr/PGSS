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
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
import asyncio
import math

LOG = getLogger('')

class FindFort:
    def __init__(self):
        self.unknown_image_path = os.getcwd() + '/unknown_img'
        self.url_image_path = os.getcwd() + '/url_img'

        self.success_img_path = os.getcwd() + '/success_img/'
        self.need_check_img_path = os.getcwd() + '/need_check_img/'
        self.not_find_img_pth = os.getcwd() + '/not_find_img/'
        self.raidnearby = rs.RaidNearby()

    async def run_fortmatching(self, session, fort_fullpath_filename):
        p_url = Path(self.url_image_path)
        fort_filename = os.path.basename(fort_fullpath_filename)
        LOG.info('find fort for {}'.format(fort_filename))
        max_fort_id = 0
        max_value = 0.0
        max_url_fullpath_filename = '' 
        for url_fullpath_filename in p_url.glob('*.jpg'):
            try:
                result = mt.fort_image_matching(str(url_fullpath_filename), str(fort_fullpath_filename))
            except KeyboardInterrupt:
                print('Ctrl-C interrupted')
                session.close()
                sys.exit(1)
            except:
                LOG.error('Matching error')
            else:
                url_filename = os.path.basename(url_fullpath_filename)
                fort_id, ext = os.path.splitext(url_filename)            
    #            print('fort_id:',fort_id,'result:',result,'max_value:',max_value, 'max_fort_id:', max_fort_id)
                if result >= max_value:
                    max_value = result
                    max_fort_id = fort_id
                    max_url_fullpath_filename = url_fullpath_filename
            
        LOG.info('fort_filename:{} max_fort_id: {} max_value: {}'.format(fort_filename,max_fort_id, max_value))
        if float(max_value) >= 0.85:
            LOG.info(str(fort_fullpath_filename))
            img = cv2.imread(str(fort_fullpath_filename),3)
            gym_image_id = self.raidnearby.get_gym_image_id(img)
            gym_image_fort_id = db.get_gym_image_fort_id(session, gym_image_id)
            if int(max_fort_id) == int(gym_image_fort_id):
                LOG.info('This gym image is already trained')
                fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '.png'
                url_result_file = os.getcwd() + '/success_img/Fort_'+str(max_fort_id) + '_url.jpg'
                shutil.move(fort_fullpath_filename, fort_result_file)
                shutil.copy(max_url_fullpath_filename, url_result_file)
            else:
                unknown_fort_id = db.get_unknown_fort_id(session)
                LOG.info('gym_images id:{} fort_id:{} unknow_fort_id:{}'.format(gym_image_id,gym_image_fort_id,unknown_fort_id))
                if gym_image_fort_id == unknown_fort_id:
                    try:
                        db.update_gym_image(session,gym_image_id,max_fort_id)
                    except:
                        LOG.error('Error to update gym_images for gym_images.id:{} gym_images.fort_id:{}'.format(gym_image_id,max_fort_id))
                        fort_result_file = os.getcwd() + '/not_find_img/Fort_' + str(max_fort_id) + '.png'
                        url_result_file = os.getcwd() + '/not_find_img/Fort_'+str(max_fort_id) + '_url.jpg'
                        shutil.move(fort_fullpath_filename, fort_result_file)
                        shutil.copy(max_url_fullpath_filename, url_result_file)
                        LOG.error('Successfully found fort fort_id:{}, but failed to updata gym_images database. Check not_find_img with the fort_id'.format(max_fort_id))
                    else:
                        fort_result_file = os.getcwd() + '/success_img/Fort_' + str(max_fort_id) + '.png'
                        url_result_file = os.getcwd() + '/success_img/Fort_'+str(max_fort_id) + '_url.jpg'
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
                    fort_result_file = os.getcwd() + '/not_find_img/Fort_' + str(max_fort_id) + '.png'
                    url_result_file = os.getcwd() + '/not_find_img/Fort_'+str(max_fort_id) + '_url.jpg'
                    shutil.move(fort_fullpath_filename, fort_result_file)
                    shutil.copy(max_url_fullpath_filename, url_result_file)
        elif float(max_value) >= 0.80:
            fort_result_file = os.getcwd() + '/not_find_img/Fort_' + str(max_fort_id) + '.png'
            url_result_file = os.getcwd() + '/not_find_img/Fort_'+str(max_fort_id) + '_url.jpg'
            shutil.move(fort_fullpath_filename, fort_result_file)
            shutil.copy(max_url_fullpath_filename, url_result_file)
            LOG.info('Found fort id: {} but need to verify'.format(max_fort_id))
            LOG.info('If the Fort_{}.png and Fort_{}_url.jpg in not_find_img are correct'.format(str(max_fort_id),str(max_fort_id)))
            LOG.info('Run "python3.6 manualsubmit.py"'.format(str(max_fort_id),str(max_fort_id)))
        else:
            fort_result_file = os.getcwd() + '/not_find_img/' + str(fort_filename)
            url_result_file = os.getcwd() + '/not_find_img/'+str(max_fort_id) + '.jpg'
            shutil.move(fort_fullpath_filename, fort_result_file)
            shutil.copy(max_url_fullpath_filename, url_result_file)
            LOG.info('Can not find fort: {}, check the image in not_find_img'.format(max_fort_id))
    

    async def findfort_main(self):
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

        while True:
            LOG.debug('Run find fort task')
            session = db.Session()
            new_img_count = 0
            for fort_fullpath_filename in p.glob('GymImage*.png'):
                new_img_count = new_img_count+1
                await run_fortmatching(session, fort_fullpath_filename)
            if new_img_count != 0:
                LOG.info('{} new fort image processed'.format(new_img_count))
            else:
                LOG.debug('{} new fort image processed'.format(new_img_count))
            session.close()
            await asyncio.sleep(10)
            
        LOG.info('Done')
        return
    
if __name__ == '__main__':
    findfort = FindFort()
    findfort.findfort_main()

                    
                    
                    
            
                
