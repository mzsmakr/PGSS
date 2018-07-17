from logging import getLogger
import importlib
import os
import signal
import sys
import time
import glob
from pathlib import Path
from sys import argv

LOG = getLogger('')

class HealthCheck:

    def __init__(self):
        if len(argv) >= 2:
            self.config = importlib.import_module(str(argv[1]))
        else:
            self.config = importlib.import_module('config')

        if self.config.ENABLE_CROP and self.config.CROP_PROCESSES > 0:
            self.check_crop = True
            self.crop_path = Path(self.config.SCREENSHOT_SAVE_PATH)
            self.crop_last = None
        else:
            self.check_crop = False

        if self.config.ENABLE_NEARBY and self.config.NEARBY_PROCESSES > 0:
            self.check_nearby = True
            self.nearby_path = os.path.dirname(os.getcwd() + '/process_img/')
            self.nearby_last = None
        else:
            self.check_nearby = False

        if self.config.ENABLE_FINDFORT and self.config.FINDFORT_PROCESSES > 0:
            self.check_findfort = True
            self.findfort_path = os.path.dirname(os.getcwd() + '/unknown_img/')
            self.not_find_path = os.path.dirname(os.getcwd() + '/not_find_img/')
            self.findfort_last = None
        else:
            self.check_findfort = False

    def healthcheck_main(self, raidscan):

        try:
            while True:
                if self.check_crop:
                    jpg_counter = len(glob.glob1(self.crop_path, "*.jpg"))
                    png_counter = len(glob.glob1(self.crop_path, "*.png"))
                    total_count = jpg_counter + png_counter
                    if self.crop_last is not None:
                        if total_count >= 100 and total_count > self.crop_last:
                            LOG.warning('Crop can not keep up. Increase "CROP_PROCESSES" '
                                        '(or increase "SCREENSHOT_DELAYS")!')
                    self.crop_last = total_count

                if self.check_nearby:
                    total_count = len(glob.glob1(self.nearby_path, "*.png"))
                    if self.nearby_last is not None:
                        if total_count >= 100 and total_count > self.nearby_last:
                            LOG.warning('Nearby can not keep up. Increase "NEARBY_PROCESSES"!')
                    self.nearby_last = total_count

                if self.check_findfort:
                    total_count = len(glob.glob1(self.findfort_path, "*.png"))
                    if self.findfort_last is not None:
                        if total_count >= 100 and total_count > self.findfort_last:
                            LOG.warning('FindFort can not keep up. Increase "FINDFORT_PROCESSES"!')
                    self.findfort_last = total_count

                    not_find_gym_count = len(glob.glob1(self.not_find_path, "GymImage_*.png"))
                    not_find_pokemon_count = len(glob.glob1(self.not_find_path, "PokemonImage_*.png"))
                    if not_find_gym_count > 10:
                        LOG.warning(
                            'Not Find Path contains {} Gym images to solve. '
                            'Solve them to potentially increase effizienzy!'
                            .format(not_find_gym_count))
                    if not_find_pokemon_count > 5:
                        LOG.warning(
                            'Not Find Path contains {} Pokemon images to solve. Solve them in order to detect Bosses!'
                            .format(not_find_pokemon_count))

                time.sleep(60)

        except KeyboardInterrupt:
            os.killpg(0, signal.SIGINT)
            sys.exit(1)
        except Exception as e:
            LOG.error('Unexpected Exception in devicecontroller Process: {}'.format(e))

            if raidscan is not None:
                raidscan.restart_healthcheck()
            else:
                os.killpg(0, signal.SIGINT)
                sys.exit(1)
