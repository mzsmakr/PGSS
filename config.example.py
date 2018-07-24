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
RAID_NEARBY_SIZE = [
                    {'width': 1536, 'height': 2048, 'crop_w': 320, 'crop_h': 525, 'crop_y1': 369, 'crop_y2': 977,
                     'comp3_x': 164, 'comp3_y': 528, 'crop3_x1': 160, 'crop3_x2': 608, 'crop3_x3': 1056,
                     'comp2_x': 389, 'comp2_y': 528, 'crop2_x1': 384, 'crop2_x2': 832,
                     'comp1_x': 612, 'comp1_y': 528, 'crop1_x1': 608},  # iPad, iPad mini

                    {'width': 750, 'height': 1334, 'crop_w': 157, 'crop_h': 260, 'crop_y1': 514, 'crop_y2': 811,
                     'comp3_x': 80, 'comp3_y': 590, 'crop3_x1': 78,  'crop3_x2': 297, 'crop3_x3': 516,
                     'comp2_x': 190, 'comp2_y': 590, 'crop2_x1': 188, 'crop2_x2': 406,
                     'comp1_x': 300, 'comp1_y': 590, 'crop1_x1': 297},  # iPhone

                    {'width': 640, 'height': 1136, 'crop_w': 134, 'crop_h': 221, 'crop_y1': 436, 'crop_y2': 690,
                     'comp3_x': 69, 'comp3_y': 503, 'crop3_x1': 67, 'crop3_x2': 253, 'crop3_x3': 440,
                     'comp2_x': 162, 'comp2_y': 503, 'crop2_x1': 160, 'crop2_x2': 347,
                     'comp1_x': 255, 'comp1_y': 503, 'crop1_x1': 253},  # iPhone SE

                    {'width': 1080, 'height': 1920, 'crop_w': 270, 'crop_h': 444, 'crop_y1': 0, 'crop_y2': 0,
                     'comp3_x': 0, 'comp3_y': 0, 'crop3_x1': 0, 'crop3_x2': 0, 'crop3_x3': 0,
                     'comp2_x': 0, 'comp2_y': 0, 'crop2_x1': 0, 'crop2_x2': 0,
                     'comp1_x': 0, 'comp1_y': 0, 'crop1_x1': 0},  # iPhone Plus
                   ]

### Device Manager Options ###

SCAN_AREA = None
#from shapely.geometry import Polygon
#SCAN_AREA = Polygon([
#    [0.0, 0.0],
#    [1.0, 1.0],
#    [2.0, 0.0]
#])
#SCAN_AREA = 'All'

DEVICE_LIST = None
#DEVICE_LIST = ['168069373365c2dbf9155169cfa3dc2d25068761', 'xxx']
TELEPORT_DELAYS = [5, 5]
SCREENSHOT_DELAYS = [0.25, 0.25]
RESTART_DELAYS = [600, 600]

from os import path
DERIVED_DATA_PATH = path.dirname(path.realpath(__file__))+'/DerivedData'
SCREENSHOT_SAVE_PATH = path.dirname(path.realpath(__file__))+'/DerivedData/Logs/Test/Attachments'

RAID_START_TIME = "06:00"
RAID_END_TIME = "20:00"

### RSSBOT ###

RAID_IMAGE_CHANNELS = ('channel_id_1', 'channel_id_2')      #limit users to using the bot in this channel, right click and copy ID.
TOKEN= ''                                                   #discord bot token (NOT bot ID)