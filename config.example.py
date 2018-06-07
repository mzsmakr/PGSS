
DB_ENGINE = 'postgres://user:pass@192.168.1.5:5432/monocle_raid'
#DB_ENGINE = 'mysql://user:pass@192.168.1.5:3306/monocle_raid?charset=utf8'

# the corner points of a rectangle for download gym url image
# If either of them is (0, 0) then download all gym url image in database
MAP_START = (0,0)
MAP_END = (0,0)
#MAP_START = (41.89588847196377,-87.65613555908205)
#MAP_END = (41.84271080015277,-87.61476516723633)

# Config for rssbot
SCREENSHOT_SAVE_PATH = '/Users/user/Library/Developer/Xcode/DerivedData/Location-aforuhseaddpszablncqqxewzbkm/Logs/Test/Attachments/'
RAID_IMAGE_CHANNELS = ('channel_id_1', 'channel_id_2')      #limit users to using the bot in this channel, right click and copy ID.
TOKEN= ''    #discord bot token (NOT bot ID)

# ScreenShot size config
RAID_NEARBY_SIZE = [  {'width':1536, 'height':2048 , 'crop_w':320, 'crop_h':525, 'crop_x1':170, 'crop_x2':618, 'crop_x3':1066, 'crop_y1':379, 'crop_y2':1041},  # iPad, iPad mini
                      {'width':750,  'height':1334 , 'crop_w':157, 'crop_h':260, 'crop_x1':83,  'crop_x2':302, 'crop_x3':520,  'crop_y1':519, 'crop_y2':842}    # iPhone
                      ]  

