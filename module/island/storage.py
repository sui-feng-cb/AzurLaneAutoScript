import cv2
import numpy as np

import module.config.server as server

from module.base.button import ButtonGrid
from module.base.decorator import cached_property, del_cached_property
from module.base.timer import Timer
from module.base.utils import color_similar, color_similarity_2d, crop, rgb2gray, xywh2xyxy
from module.island.assets import *
from module.island.data import DIC_ISLAND_ITEM
from module.island.ui import IslandUI, ISLAND_STORAGE_SCROLL
from module.logger import logger
from module.map_detection.utils import Points
from module.ocr.ocr import Digit
from module.statistics.item import Item, ItemGrid
from module.ui.page import page_island_storage


class AmountOcr(Digit):
    def pre_process(self, image):
        mask = color_similarity_2d(image, color=(75, 76, 78))
        bg = np.mean(mask > 230, axis=0)
        match = np.where(bg > 0.8)[0]
        if len(match):
            left = match[0]
            total = mask.shape[1]
            if left < total:
                image = image[:, left:]
        image = super().pre_process(image)
        return image


if server.server == 'jp':
    AMOUNT_OCR = AmountOcr([], letter=(255, 255, 255), name='Amount_ocr')
else:
    AMOUNT_OCR = AmountOcr([], lang='cnocr', letter=(218, 218, 218), name='Amount_ocr')


class StorageItem(Item):
    def predict_valid(self):
        return np.mean(rgb2gray(self.image) > 230) < 0.9


class StorageItemGrid(ItemGrid):
    item_class = StorageItem

    def match_template(self, image, similarity=None):
        """
        Match templates, try most frequent hit templates first.

        Args:
            image (np.ndarray):
            similarity (float):

        Returns:
            str: Template name.
        """
        if similarity is None:
            similarity = self.similarity
        color = cv2.mean(crop(image, self.template_area))[:3]
        # Match frequently hit templates first
        names = np.array(list(self.templates.keys()))[np.argsort(list(self.templates_hit.values()))][::-1]
        # Match known templates first
        names = [name for name in names if not name.isdigit()] + [name for name in names if name.isdigit()]
        for name in names:
            # threshold=5 to match items in same shape but with different colors
            if color_similar(color1=color, color2=self.colors[name], threshold=5):
                res = cv2.matchTemplate(image, self.templates[name], cv2.TM_CCOEFF_NORMED)
                _, sim, _, _ = cv2.minMaxLoc(res)
                if sim > similarity:
                    self.templates_hit[name] += 1
                    return name

        self.next_template_index += 1
        name = str(self.next_template_index)
        logger.info(f'New template: {name}')
        image = crop(image, self.template_area)
        self.colors[name] = cv2.mean(image)[:3]
        self.templates[name] = image
        self.templates_hit[name] = self.templates_hit.get(name, 0) + 1
        return name

    @staticmethod
    def item_id_parse(string):
        for key, value in DIC_ISLAND_ITEM.items():
            if string == value['name']['en']:
                return key
        logger.warning(f'Unknown item name: {string}')
        return None

    def predict(self, image, name=True, amount=True, cost=False, price=False, tag=False):
        super().predict(image, name, amount, cost, price, tag)
        items = []
        for item in self.items:
            item.item_id = self.item_id_parse(item.name)
            if item.item_id is not None:
                items.append(item)
        self.items = items
        return self.items


class IslandStorage(IslandUI):
    def _get_bars(self):
        """
        Returns:
            np.array: [[x1, y1], [x2, y2]], location of the item name icon upper left corner.
        """
        area = (299, 135, 1116, 574)
        image = self.image_crop(area, copy=True)
        gray = color_similarity_2d(image, color=(116, 116, 118))
        cv2.inRange(gray, 250, 255, dst=gray)
        bars = []
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cont in contours:
            rect = cv2.boundingRect(cv2.convexHull(cont).astype(np.float32))
            rect = xywh2xyxy(rect)
            # Check max_height
            if rect[3] - rect[1] < 10:
                continue
            # Check item grid should be in the area
            if rect[1] < 105:
                continue
            bars.append(rect)
        bars = Points([(0., b[1]) for b in bars]).group(threshold=5)
        logger.attr('Items_icon', len(bars))
        return bars

    def wait_until_bar_appear(self, skip_first_screenshot=True):
        """
        After entering island storage page,
        items are not loaded that fast,
        wait until any bar icon appears
        """
        timeout = Timer(1, count=3).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            bars = self._get_bars()

            if timeout.reached():
                break
            if len(bars):
                break

    @cached_property
    def storage_grid(self):
        return self.storage_bar_grid()

    def storage_bar_grid(self):
        """
        Returns:
            ButtonGrid:
        """
        bars = self._get_bars()
        count = len(bars)
        if count == 0:
            logger.warning('Unable to find bar icon, assume task list is at top')
            origin_y = 157
            delta_y = 167
            row = 2
        elif count == 1:
            y_list = bars[:, 1]
            # -105 to adjust the bar position to grid position
            origin_y = y_list[0] - 105 + 135
            delta_y = 167
            row = 1
        elif count == 2:
            y_list = bars[:, 1]
            origin_y = min(y_list) - 105 + 135
            delta_y = abs(y_list[1] - y_list[0])
            row = 2
        else:
            logger.warning(f'Too many bars found ({count}), assume max rows')
            y_list = bars[:, 1]
            origin_y = min(y_list) - 105 + 135
            delta_y = abs(y_list[1] - y_list[0])
            row = 2
        storage_grid = ButtonGrid(
            origin=(303, origin_y), delta=(142, delta_y),
            button_shape=(102, 102), grid_shape=(6, row),
            name='STORAGE_ITEM_GRID'
        )
        return storage_grid

    storage_template_folder = './assets/shop/island'

    @cached_property
    def storage_items(self):
        """
        Returns:
            ItemGrid:
        """
        storage_grid = self.storage_grid
        storage_items = StorageItemGrid(
            storage_grid,
            templates={},
            template_area=(0, 15, 96, 80),
            amount_area=(36, 85, 95, 102),
        )
        storage_items.load_template_folder(self.storage_template_folder)
        storage_items.amount_ocr = AMOUNT_OCR
        return storage_items

    def storage_has_loaded(self, items):
        """
        Returns:
            bool
        """
        return any(bool(item.amount) for item in items)

    def storage_get_items(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot (bool):

        Returns:
            list[Item]:
        """
        storage_items = self.storage_items
        if storage_items is None:
            logger.warning('Expected type \'StorageItemGrid\' but was None')
            return []

        # Loop on predict to ensure items
        # have loaded and can accurately
        # be read
        record = 0
        timeout = Timer(3, count=9).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.config.SHOP_EXTRACT_TEMPLATE:
                if self.storage_template_folder:
                    logger.info(f'Extract item templates to {self.storage_template_folder}')
                    storage_items.extract_template(self.device.image, self.storage_template_folder)
                else:
                    logger.warning('SHOP_EXTRACT_TEMPLATE enabled but shop_template_folder is not set, skip extracting')

            storage_items.predict(self.device.image)

            if timeout.reached():
                logger.warning('Items loading timeout; continue and assumed has loaded')
                break

            # Check unloaded items, because AL loads items too slow.
            items = storage_items.items
            known = len([item for item in items if item.is_known_item])
            logger.attr('Item detected', known)
            if known == 0 or known != record:
                record = known
                continue
            else:
                record = known

            # End
            if self.storage_has_loaded(items):
                break

        # Log final result on predicted items
        items = storage_items.items
        grids = storage_items.grids
        if len(items):
            min_row = grids[0, 0].area[1]
            row = [str(item) for item in items if item.button[1] == min_row]
            logger.info(f'Storage row 1: {row}')
            row = [str(item) for item in items if item.button[1] != min_row]
            logger.info(f'Storage row 2: {row}')
            return items
        else:
            logger.info('No storage items found')
            return []

    def scan_all(self):
        """
        Scans all items on the island storage page.

        Returns:
            dict: {item_id: amount}
        """
        logger.hr('Scanning storage items', level=2)
        ISLAND_STORAGE_SCROLL.set_top(main=self)
        self.wait_until_bar_appear()
        items_dict = {}
        while 1:
            items = self.storage_get_items()
            for item in items:
                if not items_dict.get(item.item_id):
                    items_dict[item.item_id] = item.amount

            if ISLAND_STORAGE_SCROLL.at_bottom(main=self):
                logger.info('Scroll bar reached end, stop')
                break
            else:
                ISLAND_STORAGE_SCROLL.next_page(main=self, page=0.66)
                self.device.click_record.pop()
                del_cached_property(self, 'storage_grid')
                del_cached_property(self, 'storage_items')
                continue
        return items_dict

    def run(self):
        """
        Pages:
            in: Any page
            out: page_island

        Returns:
            dict: {item_id: amount}
        """
        self.ui_ensure(page_island_storage)
        self.island_storage_side_navbar_ensure(upper=1)
        result = self.scan_all()
        return result
