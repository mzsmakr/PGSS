# PGSS ( Pokemon Go Screenshot Scanner) 
PGSS scans raid near by images and identifies Gym,Raid Egg/Boss and time and then updates monocle hydro database. PGSS also works as backend for RealDeviceRaidMap (<https://github.com/123FLO321/RealDeviceRaidMap/>). Most of gym images are identified automatically.

## Features
1. Read raid near by sighting images and identify
	* gym 
	* raid boss
	* start time
2. Parameters to identify gym and raid boss are stored in `gym_images` and `pokemon_images` table automatically.
3. Update raids and fort_sightings tables in monocle (Hydro) database
4. Download gym(fort) url images and find matching gym automatically. Up to 99% of gyms are detected successfully.
5. Discord bot to download user submitted screenshot in your discord server 
6. MySQL and Postgresql supported.

## Requirements
* Python 3.6
* Tesseract
* Linux/macOS. Never tested on Windows.
* macOS and iOS are required for RealDeviceRaidMap(<https://github.com/123FLO321/RealDeviceRaidMap/>) to fully automate raids scan. 

## How it works
### raidnearby.py
Read all raid near by screen shot image cropped by `crop.py` in `process_img` directory and extract gym/raid boss/hatch time information and update `raids` and `fort_sightings` table for monocle Hydro database. If raidnearby.py can't identify the gym then the gym image is stored in `unknown_img` as `FortImage_xxx.png`. Once gym is identified, check level and time. If time is Ongoing(Raid), then try to identify raid boss by checking with `pokemon_images` table. If the raid boss is unknown, then store the raid boss image into `non_find_img` as PokemonImage_xxx.png.

### findfort.py
Read all gym images in `unknown_img` and identify the gym(fort) image by comparing fort URL images in `url_img`. If findfort.py finds matching gym(fort) in `url_img`, then update `gym_images` table to set identified `fort_id`. findfort.py checks images every 30 seconds. Fort URL images need to be downloaded by `downloadfortimg.py` before running `findfort.py`. If findfort.py can't find matching jpg image in `url_img`, the gym image stored in `not_find_img` and you need to submit manually by renaming the image to `Fort_fortid.png` and run `python3.6 manualsubmit.py`. 

### downloadfortimg.py
Download all fort URL images in `Forts` table. Set `MAP_START` and `MAP_END` in `config.py` to limit fort URL images to download if you want.

### manualsubmit.py
`manualsubmit.py` update `fort_id` in `gym_images` and `pokemon_id` in `pokemon_images` by reading `Fort_xxx.png` and `Pokemon_yyy.png` in `not_find_img`. User need to set xxx for `fort_id` and yyy for `pokedex id` manually. This part need to be integrated with `Frontend` of RealDeviceRaidMap in the future.

### rssbot.py
Discord bot to download user submitted raid nearby in your discord server. It saves to `SCREENSHOT_SAVE_PATH` in config.py. To create discord bot, check here <https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token>

### Running order
1. Copy config.example.py and rename to config.py. Configure config.py based on your setup.
2. Run `python3.6 downloadfortimg.py` once to download all gym(fort) URL images
3. Run `python3.6 raidscan.py` start raid image scanning. With this command, `crop.py`, `raidnearby.py` and `findfort.py` run all together. If you run with `python3.6 raidscan.py NO_FINDFORT`, `findfort.py` dosen't run and need to run `findfort.py` separately. This option is recommanded when you start raid scan in new area and most of gym images are unknown.
4. If you run `raidscan.py` with **NO_FINDFORT** option, run open another terminal and activate `venv`, then run `python3.6 findfort.py`.
5. _Optional_. Run `python3.6 rssbot.py` to start downloading user posted screenshot image on your discord server 
6. If PGSS can't find gym then the gym image is saved in `not_find_img`. Check the images in the directory and identify the gym. Then rename the image to `Fort_xxx.png` or `Pokemon_yyy.png`. Then Run `python3.6 manualsubmit.py`. `manualsubmit.py` updates `fort_id` to xxx in `raid_images` and `pokemon_id (Pokedex#)` to yyy in `pokemon_images` table.

## Setting up
1. Install Python 3.6
 * macOS : I downloaded from here <https://www.python.org/downloads/release/python-365/> and installed
 * Linux (Ubuntu example)
    ```
    apt-get install build-essential
    sudo add-apt-repository ppa:jonathonf/python-3.6
    apt-get update
    sudo apt-get install python3.6 python3.6-dev
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3.6 get-pip.py
    ```
    There are many other way to install python3.6. Google it.
3. Install tesseract 
 * macOS : `brew install tesseract` (Install Homebrew if you don't already have it)
 * Linux
    ```
    apt-get update
    sudo apt-get install tesseract-ocr
    ```
4. Create venv
    `python3.6 -m venv path/to/create/venv`
	example: `python3.6 -m venv ~/venv_pgss`
5. Activate venv
    `source ~/venv_pgss/bin/activate`
6. Install requirements
    `pip3.6 install -r requirements.txt -U`
    * If you don't have MySQL on your machine, comment out mysqlclient
    * If you don't have Postgresql on your machine, commment out psycopg2 and psycopg2-binary
7. Configure config.py to set your monocle database and set discord server setting if you use rssbot.py 
8. Run `python3.6 downloadfortimg.py`. If you don't want to download whole fort images in database, set `MAP_START` and `MAP_END` in `config.py`.
9. Run `python3.6 raidscan.py` from the command line. When first run, raid_images and pokemon_images tables are added automatically.
10. **Note. If you were running crop.bash for Frontend of ReadDevicePokeMap, stop crop.bash before running raidscan.py. raidscan.py itself gets screenshot image and crop with crop.py**. Don't worry, PGSS can identify gym images up to 99% of gyms automatically (without user input).
11. Run `python3.6 rssbot.py` to start downloading user posted screenshot image on your discord server
12. Wait until all gyms are identified. Check `success_img` directory to make sure all gym images are correctly identified. If pgss can't find matching gym in `url_img`, the raid sighting image is stored in `not_find_img` and you have to manually assign fort id to the gym image. Rename the gym image to Fort_fortid.png and run `python3.6 manualsubmit.py`. 
13. `PokemonImage_xxx.png` files are stored in `not_find_img` directory. Rename the file to `Pokemon_PokemonId.png`(e.g. `Pokemon_380.png` for Latias) and run `python3.6 manualsubmit.py`. This will train pokemon raid boss. Usually only one time training should be enough.
14. If screenshot image size is not in config.py save the iamge to `not_find_img` as `Image_aaaxbbb.png` and you have to configure `RAID_NEARBY_SIZE`.

## Database Tables
When you run `raidscan.py`, `gym_images` and `pokemon_images` tables are automatically created if these tables are not in your database. If for some reason(error), these tables are not created, then you can create manually these tables as follow.

### Postgresql
#### gym_images
```
CREATE TABLE gym_images (
    id SERIAL NOT NULL, 
    fort_id INTEGER, 
    param_1 INTEGER, 
    param_2 INTEGER, 
    param_3 INTEGER, 
    param_4 INTEGER, 
    param_5 INTEGER, 
    param_6 INTEGER, 
    created INTEGER, 
    PRIMARY KEY (id)
);
```
#### pokemon_images
```
CREATE TABLE pokemon_images (
    id SERIAL NOT NULL, 
    pokemon_id INTEGER, 
    param_1 INTEGER, 
    param_2 INTEGER, 
    param_3 INTEGER, 
    param_4 INTEGER, 
    param_5 INTEGER, 
    param_6 INTEGER, 
    param_7 INTEGER, 
    created INTEGER, 
    PRIMARY KEY (id)
);
```
### MySQL
#### gym_images
```
CREATE TABLE gym_images (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    fort_id INTEGER, 
    param_1 INTEGER, 
    param_2 INTEGER, 
    param_3 INTEGER, 
    param_4 INTEGER, 
    param_5 INTEGER, 
    param_6 INTEGER, 
    created INTEGER, 
    PRIMARY KEY (id)
);
```
#### pokemon_images
```
CREATE TABLE pokemon_images (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    pokemon_id INTEGER, 
    param_1 INTEGER, 
    param_2 INTEGER, 
    param_3 INTEGER, 
    param_4 INTEGER, 
    param_5 INTEGER, 
    param_6 INTEGER, 
    param_7 INTEGER, 
    created INTEGER, 
    PRIMARY KEY (id)
)
```
