import sys
import cv2
import numpy as np
from pathlib import Path
import os
import time
import math
import shutil
from PIL import Image
import pytesseract
import datetime
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, CRITICAL, Formatter, handlers
import time
import database
from multiprocessing import Process
import asyncio
import re
from sys import argv
import importlib
import hashlib

logpath = os.getcwd()+'/logs/'
log_path = os.path.dirname(logpath)
if not os.path.exists(log_path):
    print('log directory created')
    os.makedirs(log_path)

log_fmt='%(asctime)s [%(filename)-12.12s] [%(levelname)-5.5s]  %(message)s'
logFormatter = Formatter(log_fmt)
nowtime = datetime.datetime.now()
nowtimestr = '{0:%Y-%m-%d_%H-%M-%S}'.format(nowtime)
logfile = logpath+nowtimestr+'_raidscan.log'
basicConfig(filename=logfile, format=log_fmt, level=DEBUG)

LOG = getLogger('')
console=StreamHandler();
console.setLevel(INFO)
console.setFormatter(logFormatter)
LOG.addHandler(console)

rfh = handlers.RotatingFileHandler(
    filename=logfile,
    maxBytes=16384,
    backupCount=3
)
rfh.setLevel(CRITICAL)
rfh.setFormatter(logFormatter)
LOG.addHandler(rfh)


class RaidNearby:
    def __init__(self):

        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        LOG.info('Pokemon Screenshot Raid Scan Started')

        self.process_img_path = os.getcwd() + '/process_img/'
        self.copy_path = os.getcwd() + '/unknown_img/'
        self.not_find_path = os.getcwd() + '/not_find_img/'
        self.success_img_path = os.getcwd() + '/success_img/'

        # Create directories if not exists
        file_path = os.path.dirname(self.process_img_path)
        if not os.path.exists(file_path):
            LOG.info('process_img directory created')
            os.makedirs(file_path)

        file_path = os.path.dirname(self.copy_path)
        if not os.path.exists(file_path):
            LOG.info('unknown_img directory created')
            os.makedirs(file_path)

        file_path = os.path.dirname(self.success_img_path)
        if not os.path.exists(file_path):
            LOG.info('success_img_path directory created')
            os.makedirs(file_path)

        file_path = os.path.dirname(self.not_find_path)
        if not os.path.exists(file_path):
            LOG.info('not_find_img directory created')
            os.makedirs(file_path)

        self.p = Path(self.process_img_path)

        self.timefile = "time.png"
        self.level1_num = 328950.0

        self.session = database.Session()

        self.gym_db = database.get_gym_images(self.session)
        LOG.info('{} gym images loaded'.format(len(self.gym_db)))
        #for gym in self.gym_db:
        #    LOG.debug('%d %d %d %d %d %d %d %d', gym.id, gym.fort_id, gym.param_1, gym.param_2, gym.param_3, gym.param_4, gym.param_5, gym.param_6)

        self.mon_db = [mon for mon in database.get_pokemon_images(self.session)]
        LOG.info('{} pokemon images loaded'.format(len(self.mon_db)))

        self.unknown_fort_id = database.get_unknown_fort_id(self.session)
        self.not_a_fort_id = database.get_not_a_fort_id(self.session)
        self.not_a_pokemon_id = -2

    # Detect level of raid from level image
    def detectLevel(self, level_img):
        img_gray = cv2.cvtColor(level_img,cv2.COLOR_BGR2GRAY)
        ret,thresh1 = cv2.threshold(img_gray,220,255,cv2.THRESH_BINARY_INV)

        profile = []
        star_start = []
        star_end = []
        level = 0
        valley_threshold = 0
        # get letter separation pixels
        for i in range(thresh1.shape[1]):
            sum_vertical = sum(thresh1[:, i])
            profile.append(sum_vertical)
            if len(star_start) == len(star_end):
                if sum_vertical > valley_threshold:
                    star_start.append(i)
            else:
                if sum_vertical <= valley_threshold:
                    star_end.append(i)
                    level = level + 1
        if level < 1 or level > 5:
            level = -1

        return level

    # Detect hatch time from time image
    def detectTime(self, time_binary):
#        img_gray = cv2.cvtColor(time_img, cv2.COLOR_BGR2GRAY)
#        ret, thresh1 = cv2.threshold(img_gray, 230, 255, cv2.THRESH_BINARY_INV)
        final_img = np.zeros((time_binary.shape[0], int(time_binary.shape[1] * 0.25)), np.uint8)
        right_img = np.zeros((time_binary.shape[0], int(time_binary.shape[1] * 0.15)), np.uint8)
        separate_img = np.zeros((time_binary.shape[0], int(time_binary.shape[1] * 0.1)), np.uint8)
        profile = []
        letter_start = []
        letter_end = []
        count = 0
        # get letters separation pixels
        for i in range(time_binary.shape[1]):
            sum_vertical = sum(time_binary[:, i])
            profile.append(sum_vertical)
            if len(letter_start) == len(letter_end):
                if sum_vertical > 0:
                    letter_start.append(i)
            else:
                if sum_vertical == 0:
                    letter_end.append(i)
                    count = count + 1
        # Add blank(black) space between letters
        for i in range(count):
            final_img = cv2.hconcat([final_img, time_binary[0:time_binary.shape[0], letter_start[i]:letter_end[i]]])
            final_img = cv2.hconcat([final_img, separate_img])
        final_img = cv2.hconcat([final_img, right_img])
        kernel = np.ones((2, 2), np.uint8)
        final_img = cv2.dilate(final_img, kernel, iterations=1)
        cv2.imwrite(self.timefile, final_img)
        text = pytesseract.image_to_string(Image.open(self.timefile),
                                           config='-c tessedit_char_whitelist=1234567890:~AMP -psm 7')
        return text

    # Detect gym from raid sighting image
    def detectGym(self, raid_img):
        height, width, channels = raid_img.shape
        
        org_top_y = 40
        org_top_h = 30
        org_top_x = 135
        org_top_w = 50
        org_left_y = 125
        org_left_h = 70
        org_left_x = 45
        org_left_w = 25
        
        scale = width/320
        LOG.debug('raid image scale: {}'.format(scale))

        top_y = int(org_top_y*scale)
        top_h = int(org_top_h*scale)
        top_x = int(org_top_x*scale)
        top_w = int(org_top_w*scale)
        left_y = int(org_left_y*scale)
        left_h = int(org_left_h*scale)
        left_x = int(org_left_x*scale)
        left_w = int(org_left_w*scale)
        
        cropTop = raid_img[top_y:top_y+top_h, top_x:top_x+top_w]
        cropLeft = raid_img[left_y:left_y+left_h, left_x:left_x+left_w]
                
        top_mean0 = int(cropTop[:,:,0].mean())
        top_mean1 = int(cropTop[:,:,1].mean())
        top_mean2 = int(cropTop[:,:,2].mean())
        left_mean0 = int(cropLeft[:,:,0].mean())
        left_mean1 = int(cropLeft[:,:,1].mean())
        left_mean2 = int(cropLeft[:,:,2].mean())

        min_error = 10000000
        gym_id = 0
        gym_image_id = 0

        LOG.info('Gyms in gym_images: {}'.format(len(self.gym_db)))
        LOG.debug('top_mean0:{} top_mean1:{} top_mean2:{} left_mean0:{} left_mean1:{} left_mean2:{} '.format(top_mean0,top_mean1,top_mean2,left_mean0,left_mean1,left_mean2))

        for gym in self.gym_db:
            dif1 = pow(top_mean0 - gym.param_1,2)
            dif2 = pow(top_mean1 - gym.param_2,2)
            dif3 = pow(top_mean2 - gym.param_3,2)
            dif4 = pow(left_mean0 - gym.param_4,2)
            dif5 = pow(left_mean1 - gym.param_5,2)
            dif6 = pow(left_mean2 - gym.param_6,2)
            error = math.sqrt(dif1+dif2+dif3+dif4+dif5+dif6)
    #        print(gym.fort_id,error,gym.param_1,gym.param_2,gym.param_3,gym.param_4,gym.param_5,gym.param_6)
            # find minimum error
            if error < min_error:
                min_error = error
                gym_id = gym.fort_id
                gym_image_id = gym.id

        if min_error > 10:
            LOG.info('gym_id:{} min_error:{}'.format(gym_id, min_error))
            LOG.info('GymImage added to database')
            gym_id = -1
            database.add_gym_image(self.session,self.unknown_fort_id,top_mean0,top_mean1,top_mean2,left_mean0,left_mean1,left_mean2)
            gym_image_id = database.get_gym_image_id(self.session,top_mean0,top_mean1,top_mean2,left_mean0,left_mean1,left_mean2)
            # Reload gym_images
            self.gym_db = database.get_gym_images(self.session)
    #        for gym in self.gym_db:
    #            LOG.debug('{} {} {} {} {} {} {} {}'.format(gym.id, gym.fort_id, gym.param_1, gym.param_2, gym.param_3, gym.param_4, gym.param_5, gym.param_6))
            LOG.info('GymImage reloaded : {}'.format(len(self.gym_db)))

        return gym_image_id, gym_id, min_error

    def get_gym_image_id(self, raid_img):
        height, width, channels = raid_img.shape
        
        org_top_y = 40
        org_top_h = 30
        org_top_x = 135
        org_top_w = 50
        org_left_y = 125
        org_left_h = 70
        org_left_x = 45
        org_left_w = 25
        
        scale = width/320

        top_y = int(org_top_y*scale)
        top_h = int(org_top_h*scale)
        top_x = int(org_top_x*scale)
        top_w = int(org_top_w*scale)
        left_y = int(org_left_y*scale)
        left_h = int(org_left_h*scale)
        left_x = int(org_left_x*scale)
        left_w = int(org_left_w*scale)
        
        cropTop = raid_img[top_y:top_y+top_h, top_x:top_x+top_w]
        cropLeft = raid_img[left_y:left_y+left_h, left_x:left_x+left_w]
            
        top_mean0 = int(cropTop[:,:,0].mean())
        top_mean1 = int(cropTop[:,:,1].mean())
        top_mean2 = int(cropTop[:,:,2].mean())
        left_mean0 = int(cropLeft[:,:,0].mean())
        left_mean1 = int(cropLeft[:,:,1].mean())
        left_mean2 = int(cropLeft[:,:,2].mean())
        LOG.debug('gym image param: {} {} {} {} {} {}'.format(top_mean0,top_mean1,top_mean2,left_mean0,left_mean1,left_mean2))
        gym_image_id = database.get_gym_image_id(self.session,top_mean0,top_mean1,top_mean2,left_mean0,left_mean1,left_mean2)
        return gym_image_id

    def detectMon(self, img):
        ret,bin_img = cv2.threshold(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),240,255,cv2.THRESH_BINARY_INV)
        bin_color = cv2.cvtColor(bin_img,cv2.COLOR_GRAY2BGR)

        height, width, channels = img.shape
        
        org_x1 = [288, 300]
        org_y1 = [125, 195]
        org_x2 = [264, 280]
        org_y2 = [234, 250]    
        org_x3 = [244, 260]
        org_y3 = [254, 270]    
        org_x4 = [224, 240]
        org_y4 = [270, 286]    
        org_x5 = [310, 318]
        org_y5 = [220, 350]    
        org_x6 = [280, 308]
        org_y6 = [270, 350]    
        org_x7 = [244, 278]
        org_y7 = [300, 350]    

        scale = width/320
        LOG.debug('raid image scale :{}'.format(scale))

        x1 = [int(org_x1[0]*scale), int(org_x1[1]*scale)]
        y1 = [int(org_y1[0]*scale), int(org_y1[1]*scale)]
        x2 = [int(org_x2[0]*scale), int(org_x2[1]*scale)]
        y2 = [int(org_y2[0]*scale), int(org_y2[1]*scale)]    
        x3 = [int(org_x3[0]*scale), int(org_x3[1]*scale)]
        y3 = [int(org_y3[0]*scale), int(org_y3[1]*scale)]    
        x4 = [int(org_x4[0]*scale), int(org_x4[1]*scale)]
        y4 = [int(org_y4[0]*scale), int(org_y4[1]*scale)]    
        x5 = [int(org_x5[0]*scale), int(org_x5[1]*scale)]
        y5 = [int(org_y5[0]*scale), int(org_y5[1]*scale)]    
        x6 = [int(org_x6[0]*scale), int(org_x6[1]*scale)]
        y6 = [int(org_y6[0]*scale), int(org_y6[1]*scale)]    
        x7 = [int(org_x7[0]*scale), int(org_x7[1]*scale)]
        y7 = [int(org_y7[0]*scale), int(org_y7[1]*scale)]    
        
        crop1 = bin_img[y1[0]:y1[1], x1[0]:x1[1]]
        crop2 = bin_img[y2[0]:y2[1], x2[0]:x2[1]]
        crop3 = bin_img[y3[0]:y3[1], x3[0]:x3[1]]
        crop4 = bin_img[y4[0]:y4[1], x4[0]:x4[1]]
        crop5 = bin_img[y5[0]:y5[1], x5[0]:x5[1]]
        crop6 = bin_img[y6[0]:y6[1], x6[0]:x6[1]]
        crop7 = bin_img[y7[0]:y7[1], x7[0]:x7[1]]

        mean1 = int(crop1.mean())
        mean2 = int(crop2.mean())
        mean3 = int(crop3.mean())
        mean4 = int(crop4.mean())
        mean5 = int(crop5.mean())
        mean6 = int(crop6.mean())
        mean7 = int(crop7.mean())
        
        min_error = 10000000
        mon_id = 0
        mon_image_id = 0

        # get error from all gyms
        for mon in self.mon_db:
            dif1 = pow(mean1 - mon.param_1,2)
            dif2 = pow(mean2 - mon.param_2,2)
            dif3 = pow(mean3 - mon.param_3,2)
            dif4 = pow(mean4 - mon.param_4,2)
            dif5 = pow(mean5 - mon.param_5,2)
            dif6 = pow(mean6 - mon.param_6,2)
            dif7 = pow(mean7 - mon.param_7,2)
            error = math.sqrt(dif1+dif2+dif3+dif4+dif5+dif6+dif7)
            # find minimum error
            if error < min_error:
                min_error = error
                mon_id = mon.pokemon_id
                mon_image_id = mon.id

        if min_error > 5:
            mon_id = -1
            database.add_pokemon_image(self.session,0,mean1,mean2,mean3,mean4,mean5,mean6,mean7)
            mon_image_id = database.get_pokemon_image_id(self.session,mean1,mean2,mean3,mean4,mean5,mean6,mean7)
            # Reload pokemon_images
            self.mon_db = database.get_pokemon_images(self.session)

        return mon_image_id, mon_id, min_error

    def get_pokemon_image_id(self, img):
        ret,bin_img = cv2.threshold(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),240,255,cv2.THRESH_BINARY_INV)
        bin_color = cv2.cvtColor(bin_img,cv2.COLOR_GRAY2BGR)
        
        height, width, channels = img.shape
        
        org_x1 = [288, 300]
        org_y1 = [125, 195]
        org_x2 = [264, 280]
        org_y2 = [234, 250]    
        org_x3 = [244, 260]
        org_y3 = [254, 270]    
        org_x4 = [224, 240]
        org_y4 = [270, 286]    
        org_x5 = [310, 318]
        org_y5 = [220, 350]    
        org_x6 = [280, 308]
        org_y6 = [270, 350]    
        org_x7 = [244, 278]
        org_y7 = [300, 350]    

        scale = width/320

        x1 = [int(org_x1[0]*scale), int(org_x1[1]*scale)]
        y1 = [int(org_y1[0]*scale), int(org_y1[1]*scale)]
        x2 = [int(org_x2[0]*scale), int(org_x2[1]*scale)]
        y2 = [int(org_y2[0]*scale), int(org_y2[1]*scale)]    
        x3 = [int(org_x3[0]*scale), int(org_x3[1]*scale)]
        y3 = [int(org_y3[0]*scale), int(org_y3[1]*scale)]    
        x4 = [int(org_x4[0]*scale), int(org_x4[1]*scale)]
        y4 = [int(org_y4[0]*scale), int(org_y4[1]*scale)]    
        x5 = [int(org_x5[0]*scale), int(org_x5[1]*scale)]
        y5 = [int(org_y5[0]*scale), int(org_y5[1]*scale)]    
        x6 = [int(org_x6[0]*scale), int(org_x6[1]*scale)]
        y6 = [int(org_y6[0]*scale), int(org_y6[1]*scale)]    
        x7 = [int(org_x7[0]*scale), int(org_x7[1]*scale)]
        y7 = [int(org_y7[0]*scale), int(org_y7[1]*scale)]    
        
        crop1 = bin_img[y1[0]:y1[1], x1[0]:x1[1]]
        crop2 = bin_img[y2[0]:y2[1], x2[0]:x2[1]]
        crop3 = bin_img[y3[0]:y3[1], x3[0]:x3[1]]
        crop4 = bin_img[y4[0]:y4[1], x4[0]:x4[1]]
        crop5 = bin_img[y5[0]:y5[1], x5[0]:x5[1]]
        crop6 = bin_img[y6[0]:y6[1], x6[0]:x6[1]]
        crop7 = bin_img[y7[0]:y7[1], x7[0]:x7[1]]

        mean1 = int(crop1.mean())
        mean2 = int(crop2.mean())
        mean3 = int(crop3.mean())
        mean4 = int(crop4.mean())
        mean5 = int(crop5.mean())
        mean6 = int(crop6.mean())
        mean7 = int(crop7.mean())

        LOG.debug('pokemon image param: {} {} {} {} {} {} {}'.format(mean1,mean2,mean3,mean4,mean5,mean6,mean7))
        pokemon_image_id = database.get_pokemon_image_id(self.session,mean1,mean2,mean3,mean4,mean5,mean6,mean7)
        return pokemon_image_id

    def detectEgg(self, time_img):
        img_gray = cv2.cvtColor(time_img, cv2.COLOR_BGR2GRAY)
        ret, thresh1 = cv2.threshold(img_gray, 220, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((2, 2), np.uint8)
        thresh1 = cv2.erode(thresh1, kernel, iterations=1)
        time_mean = cv2.mean(time_img, thresh1)
        if time_mean[2] > (time_mean[0]+50): # Red is greater than Blue+50
            return False, thresh1
        else:
            return True, thresh1

    def checkHourMin(self, hour_min):
        hour_min[0] = hour_min[0].replace('O','0')
        hour_min[0] = hour_min[0].replace('o','0')
        hour_min[0] = hour_min[0].replace('A','4')
        hour_min[1] = hour_min[1].replace('O','0')
        hour_min[1] = hour_min[1].replace('o','0')
        hour_min[1] = hour_min[1].replace('A','4')
        if str(hour_min[0]).isdecimal()==True and str(hour_min[1]).isdecimal()==True:
            return True, hour_min
        else:
            return False, hour_min

    def getHatchTime(self,data):
        zero = datetime.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
        unix_zero = zero.timestamp()
        LOG.info('hatch_time ={}'.format(data))
        hour_min_divider = data.find(':')
        if hour_min_divider != -1:
            # US format
            AM = data.find('AM')
            PM = data.find('PM')
            if AM >= 4:
                data = data.replace('A','')
                data = data.replace('M','')
                data = data.replace('~','')
                data = data.replace('-','')
                data = data.replace(' ','')
                hour_min = data.split(':')
                ret, hour_min = self.checkHourMin(hour_min)
                if ret == True:
                    return int(unix_zero)+int(hour_min[0])*3600+int(hour_min[1])*60
                else:
                    return -1
            elif PM >= 4:
                data = data.replace('P','')
                data = data.replace('M','')
                data = data.replace('~','')
                data = data.replace('-','')
                data = data.replace(' ','')
                hour_min = data.split(':')
                ret, hour_min = self.checkHourMin(hour_min)
                if ret == True:
                    if hour_min[0] == '12':
                        return int(unix_zero)+int(hour_min[0])*3600+int(hour_min[1])*60
                    else:
                        return int(unix_zero)+(int(hour_min[0])+12)*3600+int(hour_min[1])*60
                else:
                    return -1
            # Europe format
            else:
                data = data.replace('~','')
                data = data.replace('-','')
                data = data.replace(' ','')
                hour_min = data.split(':')
                ret, hour_min = self.checkHourMin(hour_min)
                if ret == True:
                    return int(unix_zero)+int(hour_min[0])*3600+int(hour_min[1])*60
                else:
                    return -1
        else:
            return -1
        
    def isRaidSighting(self, img):
        ret = True
        LOG.debug('image mean :{}'.format(img.mean()))
        if int(img.mean()) > 240:
            LOG.debug('No raid sightings')
            ret = False
        return ret

    def reloadImagesDB(self):
        unknown_gym_num = 0
        for gym in self.gym_db:
            if int(gym.fort_id) == int(self.unknown_fort_id):
                unknown_gym_num = unknown_gym_num + 1
        if unknown_gym_num != 0:
            self.gym_db = database.get_gym_images(self.session)
            LOG.info('{} Unknown gym in DB'.format(unknown_gym_num))
            LOG.info('GymImage reloaded : {}'.format(len(self.gym_db)))        
                                 
        unknown_mon_num = 0 
        for mon in self.mon_db:
            if int(mon.pokemon_id) == 0:
                unknown_mon_num = unknown_mon_num + 1        

        if unknown_mon_num != 0:
            self.mon_db = database.get_pokemon_images(self.session)
            LOG.info('{} Unknown pokemon in DB'.format(unknown_mon_num))
            LOG.info('PokemonImages table reloaded : {}'.format(len(self.mon_db)))          

    def processRaidImage(self, raidfilename):
        filename = os.path.basename(raidfilename)
        img_full = cv2.imread(str(raidfilename),3)
        
        if img_full is None:
            return False
        
        filename_no_ext, ext = os.path.splitext(filename)

        now = datetime.datetime.now()
        unix_time = int(now.timestamp())
        file_update_time = int(os.stat(str(raidfilename)).st_mtime)
        LOG.debug('Image was created {} seconds ago'.format(str(unix_time-file_update_time)))

        if self.isRaidSighting(img_full) == False:
            os.remove(raidfilename)
            return False

        LOG.info('process {}'.format(filename))

        height, width, channel = img_full.shape
        
        scale = width/320

        x1 = [0, int(319*scale)]
        y1 = [int(406*scale), int(458*scale)]    
        time_img = img_full[y1[0]:y1[1], x1[0]:x1[1]]    
        #cv2.rectangle(img_egg,(x1[0],y1[0]),(x1[1],y1[1]),(0,255,0),1)

        
        x2 = [0, int(319*scale)]
        y2 = [int(476*scale), int(524*scale)]
        level_img = img_full[y2[0]:y2[1], x2[0]:x2[1]]    
        #cv2.rectangle(img_egg,(x2[0],y2[0]),(x2[1],y2[1]),(0,255,0),1)    

        egg, time_binary = self.detectEgg(time_img)
        if egg == True:
            time_text = self.detectTime(time_binary)
        else:
            time_text = 'Raid Boss'
        level = self.detectLevel(level_img)
        gym_image_id, gym, error_gym = self.detectGym(img_full)

        update_raid = True    
        # old file
        if unix_time - file_update_time > 1800:
            LOG.info('File is too old')
            update_raid = False
        if int(gym) > 0 and int(gym) != int(self.not_a_fort_id) and int(gym) != int(self.unknown_fort_id):
            if egg == True:
                hatch_time = self.getHatchTime(time_text)
                if hatch_time == -1:
                    LOG.error('time detection failed : {}'.format(time_text))
                    fullpath_dest = str(self.not_find_path) + 'Time_'+ time_text + '_Fort_' + str(gym) + '_GymImages_' + str(gym_image_id) + '.png' 
                    shutil.move(raidfilename,fullpath_dest)
                    return False
                if level == -1:
                    LOG.error('level detection failed.')
                    fullpath_dest = str(self.not_find_path) + 'Level_Failed_Fort_' + str(gym) + '_GymImages_' + str(gym_image_id) + '.png'
                    shutil.move(raidfilename,fullpath_dest)
                    return False
                spawn_time = hatch_time - 3600
                end_time = hatch_time + 2700
                time_battle = database.get_raid_battle_time(self.session, gym)
                LOG.info('Egg: level={} time_text={} gym={} error_gym={} hatch_time={} time_battle={}'.format(level, time_text, gym, error_gym, hatch_time, time_battle))
                if update_raid == True:
                    if int(time_battle) == int(hatch_time):
                        LOG.info('This Egg is already assigned.')
                    else:
                        try:
                            database.update_raid_egg(self.session, gym, level, hatch_time)
                            database.updata_fort_sighting(self.session, gym, unix_time)
                            LOG.info('***** New Egg is added. *****')
                        except:
                            LOG.error('Error to update raid egg for fort:{}'.format(gym))
                            self.session.rollback()
                else:
                    LOG.info('Skip update raid due to old file')
            else:
                mon_image_id, mon, error_mon = self.detectMon(img_full)
                pokemon_id = database.get_raid_pokemon_id(self.session, gym)
                if level == -1:
                    LOG.error('level detection failed.')
                    fullpath_dest = str(self.not_find_path) + 'Level_Failed_Fort_' + str(gym) + '_GymImages_' + str(gym_image_id) + '.png'
                    shutil.move(raidfilename,fullpath_dest)
                LOG.info('Pokemon: level={} time_text={} gym={} error_gym={} mon={} error_mon={}'.format(level, time_text, gym, error_gym, mon, error_mon))
                LOG.info('mon:{} pokemon_id:{}'.format(mon,pokemon_id))
                if int(mon) == int(pokemon_id) and int(mon) > 0:
                    LOG.info('This mon is already assigned.')
                else:            
                    if int(mon) > 0:
                        if update_raid == True:
                            try:
                                database.update_raid_mon(self.session, gym, mon)
                                database.updata_fort_sighting(self.session, gym, unix_time)
                                LOG.info('!!!!! New raid boss is added. !!!!!')
                            except:
                                LOG.error('Error to update raid boss for fort:{}'.format(gym))
                                self.session.rollback()
                        else:
                            LOG.info('Skip update raid due to old file')
                    elif int(mon) == 0:
                        LOG.info('Pokemon image params are in database but the Pokemon is not known')
                        unknown_mon_name = 'PokemonImage_'+str(mon_image_id)+'.png'
                        fullpath_dest = str(self.not_find_path) + str(unknown_mon_name)
                        LOG.info(fullpath_dest)
                        shutil.copy2(raidfilename,fullpath_dest)
                    elif int(mon) == self.not_a_pokemon_id: # -2
                        LOG.info('Pokemon image is not valid (most likly emply')
                    else: # int(mon) == -1
                        # Send mon image for training directory
                        LOG.info('Mon is not in database')
                        unknown_mon_name = 'PokemonImage_'+str(mon_image_id)+'.png'
                        fullpath_dest = str(self.not_find_path) + str(unknown_mon_name)
                        LOG.info(fullpath_dest)
                        shutil.copy2(raidfilename,fullpath_dest)
                processed_pokemon_name = 'Pokemon_' + str(mon) + '_PokemonImages_' + str(mon_image_id) + '.png'
                processed_file_dest = str(self.success_img_path) + str(processed_pokemon_name)
                shutil.copy2(raidfilename, processed_file_dest)
            processed_gym_name = 'Fort_'+str(gym)+'_GymImages_'+ str(gym_image_id)+'.png'
            processed_file_dest = str(self.success_img_path) + str(processed_gym_name)
            shutil.copy2(raidfilename, processed_file_dest)                
        elif int(gym) == self.not_a_fort_id:
            LOG.info('Raid image is not valid')
        elif int(gym) == self.unknown_fort_id and egg == True:
            # Send Image to Training Directory
            LOG.debug('unknown fort id:{}'.format(self.unknown_fort_id))
            LOG.debug('    gym fort id:{}'.format(gym))
            LOG.info('Gym image params are in database but the Gym is not known. Fort_id:{}'.format(gym))

            parts = str(filename_no_ext).split('_')
            if len(parts) >= 3:
                detect_help_string = '_{}_{}'.format(parts[0],parts[1])
            else:
                detect_help_string = ''

            unknown_gym_name = 'GymImage_'+str(gym_image_id)+str(detect_help_string)+'.png'
            fullpath_dest = str(self.copy_path) + str(unknown_gym_name)
            LOG.info(fullpath_dest)
            shutil.copy2(raidfilename,fullpath_dest)
        elif int(gym) == -1 and egg == True: # int(gym) < 0
            # Send gym image for training directory
            LOG.info('New unknown gym with egg. Send to unknown_img to find Gym.')

            parts = str(filename_no_ext).split('_')
            if len(parts) >= 3:
                detect_help_string = '_{}_{}'.format(parts[0],parts[1])
            else:
                detect_help_string = ''

            unknown_gym_name = 'GymImage_'+str(gym_image_id)+detect_help_string+'.png'
            fullpath_dest = str(self.copy_path) + str(unknown_gym_name)
            LOG.info(fullpath_dest)
            shutil.copy2(raidfilename,fullpath_dest)
        elif int(gym) == -1 and egg == False:
            LOG.info('Unknown gym with Raid Boss. Need egg with this Gym to identify')
#            unknown_gym_name = 'GymImage_'+str(gym_image_id)+'.png'
#            fullpath_dest = str(self.not_find_path) + str(unknown_gym_name)
#            LOG.info(fullpath_dest)
#            shutil.copy2(raidfilename,fullpath_dest) 

        os.remove(raidfilename)

        #cv2.imshow('raid_image', img_full)
        #cv2.waitKey(0)
        return True

    def main(self, raidscan, id):
        try:

            LOG.info('Raid nearby task started for process {}'.format(id + 1))
            LOG.debug('Unknown fort id: {}'.format(self.unknown_fort_id))
            LOG.debug('Not a fort id: {}'.format(self.not_a_fort_id))
            process_count = self.config.NEARBY_PROCESSES

            while True:
                LOG.debug('Run raid nearby task')
                self.reloadImagesDB()
                for fullpath_filename in self.p.glob('*.png'):
                    if process_count > 1 and not int(hashlib.md5(str(fullpath_filename).encode('utf-8')).hexdigest(),
                                                     16) % process_count == id:
                        continue
                    LOG.debug('process {}'.format(fullpath_filename))
                    self.processRaidImage(fullpath_filename)
                time.sleep(1)
        except KeyboardInterrupt:
            self.session.close()
            sys.exit(0)
        except Exception as e:
            LOG.error('Unexpected Exception in raidnerby Process: {}'.format(e))
            if raidscan is not None:
                raidscan.restart_nearby(id)
            else:
                sys.exit(1)