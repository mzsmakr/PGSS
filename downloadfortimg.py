import sys
from sys import argv
import requests
import shutil
import database
import os
import time
import importlib

url_image_path = os.getcwd() + '/url_img/'

session = database.Session()

if len(argv) >= 2:
    config = importlib.import_module(str(argv[1]))
else:
    config = importlib.import_module('config')

def download_img(url, file_name):
    file_path = os.path.dirname(url_image_path)
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    retry = 1
    while retry <= 5:
        try:
            r = requests.get(url, stream=True, timeout=5)
            if r.status_code == 200:
                with open(file_name, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                break
        except KeyboardInterrupt:
            print('Ctrl-C interrupted')
            session.close()
            sys.exit(1)
        except:
            retry=retry+1
            print('Download error', url)
            if retry <= 5:
                print('retry:', retry)
            else:
                print('Failed to download after 5 retry')

def main():
    check_boundary = True
    if (config.MAP_START[0] == 0 and config.MAP_START[1] == 0) or (config.MAP_END[0] == 0 and config.MAP_END[1] == 0):
        check_boundary = False
    else:
        north = max(MAP_START[0], MAP_END[0])
        south = min(MAP_START[0], MAP_END[0])
        east = max(MAP_START[1], MAP_END[1])
        west = min(MAP_START[1], MAP_END[1])

    all_forts = [fort for fort in database.get_forts(session)]
    print('{} forts find in database. Start downloading.'.format(len(all_forts)))
    for fort in all_forts:
        if fort.url is not None:
            in_boundary = True
            if check_boundary == True:
                lat_check = (fort.lat-north)*(fort.lat-south)
                lon_check = (fort.lon-east)*(fort.lon-west)
                if lat_check<=0.0 and lon_check<=0.0:
                    in_boundary = True
                else:
                    in_boundary = False
            if in_boundary == True:
                filename = url_image_path + str(fort.id) + '.jpg'
                print('Downloading', filename)
                download_img(str(fort.url), str(filename))
    session.close()

if __name__ == '__main__':
    main()

