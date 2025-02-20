import csv
from tqdm import tqdm

from module.base.button import ButtonGrid
from module.base.decorator import cached_property, run_once
from module.base.utils import load_image
from module.combat.assets import BATTLE_TIME
from module.daemon.daemon_15_1 import BattleTime as BattleTime_
from module.logger import logger
from module.ocr.al_ocr import AlOcr
from module.ocr.ocr import Ocr, Digit
from module.statistics.utils import *


class BattleTime(BattleTime_):
    @staticmethod
    def parse_time(string):
        return string


class PlaneOcr(Digit):
    def __init__(self, buttons, lang='azur_lane', letter=(255, 251, 247), threshold=128, alphabet='0123456789IDSBX',
                 name=None):
        super().__init__(buttons, lang=lang, letter=letter, threshold=threshold, alphabet=alphabet, name=name)

    def after_process(self, result):
        result = result.replace('X', '') if 'X' in result else '0'
        result = super().after_process(result)
        return result


class PlaneStatistics:
    DROP_FOLDER = './screenshots'
    CNOCR_CONTEXT = 'cpu'
    CSV_FILE = 'drop_result.csv'
    CSV_OVERWRITE = True
    CSV_ENCODING = 'utf-8'
    PLANE_ROWS = 7
    PLANE_GRID = ButtonGrid(origin=(1230, 90), button_shape=(48, 30), grid_shape=(1, 7), delta=(0, 43))

    def __init__(self):
        AlOcr.CNOCR_CONTEXT = PlaneStatistics.CNOCR_CONTEXT
        Ocr.SHOW_LOG = False
        self.PLANE_GRID.grid_shape = (1, self.PLANE_ROWS)
        self.place_ocr_model = PlaneOcr(self.PLANE_GRID.buttons)
        self.time_ocr_model = BattleTime(BATTLE_TIME)

    @property
    def csv_file(self):
        return os.path.join(PlaneStatistics.DROP_FOLDER, PlaneStatistics.CSV_FILE)

    @staticmethod
    def drop_folder(campaign):
        return os.path.join(PlaneStatistics.DROP_FOLDER, campaign)

    @cached_property
    def csv_overwrite_check(self):
        """
        Remove existing csv file. This method only run once.
        """
        if PlaneStatistics.CSV_OVERWRITE:
            if os.path.exists(self.csv_file):
                logger.info(f'Remove existing csv file: {self.csv_file}')
                os.remove(self.csv_file)
        return True

    @staticmethod
    @run_once
    def csv_write_column_name(writer, columns):
        writer.writerows([columns])

    def parse_plane(self, file):
        ts = os.path.splitext(os.path.basename(file))[0]
        campaign = os.path.basename(os.path.abspath(os.path.join(file, '../')))
        campaign = campaign.replace('campaign_', '')
        images = unpack(load_image(file))
        image = images[0]
        plane = self.place_ocr_model.ocr(image)
        time = self.time_ocr_model.ocr(image)
        yield ['\'' + ts, campaign, str(plane), sum(plane), time]

    def extract_plane(self, campaign):
        """
        Extract images from a given folder.

        Args:
            campaign (str):
        """
        print('')
        logger.hr(f'extract plane statistics from {campaign}', level=1)
        _ = self.csv_overwrite_check

        with open(self.csv_file, 'a', newline='', encoding=PlaneStatistics.CSV_ENCODING) as csv_file:
            writer = csv.writer(csv_file)
            self.csv_write_column_name(writer, ['截图文件名称', '关卡名称', 'ocr识别结果', '飞机总数', '右上角时间'])
            for ts, file in tqdm(load_folder(self.drop_folder(campaign)).items()):
                try:
                    rows = self.parse_plane(file)
                    writer.writerows(rows)
                except ImageError as e:
                    logger.warning(e)
                    continue
                except Exception as e:
                    logger.exception(e)
                    logger.warning(f'Error on image {ts}')
                    continue


if __name__ == '__main__':
    # Drop screenshot folder. Default to './screenshots'
    # 截图文件夹名称
    PlaneStatistics.DROP_FOLDER = './screenshots'
    # 'cpu' or 'gpu', default to 'cpu'.
    # Use 'gpu' for faster prediction, but you must have the gpu version of mxnet installed.
    PlaneStatistics.CNOCR_CONTEXT = 'cpu'
    # Name of the output csv file.
    # This will write to {DROP_FOLDER}/{CSV_FILE}.
    # 结果文件名称
    PlaneStatistics.CSV_FILE = 'plane_result.csv'
    # If True, remove existing file before extraction.
    # 是否覆写csv
    PlaneStatistics.CSV_OVERWRITE = True
    # Usually to be 'utf-8'.
    # For better Chinese export to Excel, use 'gbk'.
    PlaneStatistics.CSV_ENCODING = 'gbk'
    # Default to be 7.
    # This will change the ocr of rows of plane.
    # 飞机识别行数（最多有几行飞机）
    PlaneStatistics.PLANE_ROWS = 9
    # campaign names to export under DROP_FOLDER.
    # This will load {DROP_FOLDER}/{CAMPAIGN}.
    # Just a demonstration here, you should modify it to your own.
    # 关卡名称（截图文件夹内的需要识别图片的文件夹的名称）
    CAMPAIGNS = ['campaign_15_1']

    stat = PlaneStatistics()

    """
    Step 1:
        Run this code.
    """
    for i in CAMPAIGNS:
        stat.extract_plane(i)
