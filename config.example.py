### Start Options ###

ENABLE_CONTROL = True
ENABLE_NEARBY = True
NEARBY_PROCESSES = 1
ENABLE_CROP = True
CROP_PROCESSES = 1
ENABLE_FINDFORT = True
FINDFORT_PROCESSES = 1

POOL_SIZE = 10

### General Settings ###

DB_ENGINE = 'postgres://user:pass@192.168.1.5:5432/monocle_raid'
#DB_ENGINE = 'mysql://user:pass@192.168.1.5:3306/monocle_raid?charset=utf8'

# ScreenShot size config
RAID_NEARBY_SIZE =  [   {'width':1536, 'height':2048 , 'crop_w':320, 'crop_h':525, 'crop_x1':170, 'crop_x2':618, 'crop_x3':1066, 'crop_y1':379, 'crop_y2':1041, 'comp_x': 175, 'comp_y': 535},  # iPad, iPad mini
                        {'width':750,  'height':1334 , 'crop_w':157, 'crop_h':260, 'crop_x1':83,  'crop_x2':302, 'crop_x3':520,  'crop_y1':519, 'crop_y2':842,  'comp_x': 85,  'comp_y': 595},  # iPhone
                        {'width':640,  'height':1136 , 'crop_w':133, 'crop_h':221, 'crop_x1':71,  'crop_x2':258, 'crop_x3':444,  'crop_y1':442, 'crop_y2':717,  'comp_x': 73,  'comp_y': 507},  # iPhone SE
                        {'width':1080, 'height':1920 , 'crop_w':270, 'crop_h':444, 'crop_x1':135, 'crop_x2':486, 'crop_x3':858,  'crop_y1':861, 'crop_y2':1386, 'comp_x': 150, 'comp_y': 1000}  # iPhone Plus
                    ]

SCAN_AREA = None
#from shapely.geometry import Polygon
#SCAN_AREA = Polygon([
#    [0.0, 0.0],
#    [1.0, 1.0],
#    [2.0, 0.0]
#])

DEVICE_LIST = None
#DEVICE_LIST = ['168069373365c2dbf9155169cfa3dc2d25068761']

SCREENSHOT_DELAY = 0.1
TELEPORT_DELEAY = 5

from os import path
DERIVED_DATA_PATH = path.dirname(path.realpath(__file__))+'/DerivedData'
SCREENSHOT_SAVE_PATH = path.dirname(path.realpath(__file__))+'/DerivedData/Logs/Test/Attachments'


### RSSBOT ###

RAID_IMAGE_CHANNELS = ('channel_id_1', 'channel_id_2')      #limit users to using the bot in this channel, right click and copy ID.
TOKEN= ''                                                   #discord bot token (NOT bot ID)