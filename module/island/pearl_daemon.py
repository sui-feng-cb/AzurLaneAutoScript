from rich.table import Table
from rich.text import Text

from module.base.timer import Timer
from module.island.assets import *
from module.island.ui import IslandUI
from module.logger import logger
from module.map.map_grids import SelectedGrids
from module.ocr.ocr import Digit, Ocr
from module.ui.page import page_island, page_island_phone
from module.ui.scroll import Scroll


ISLAND_FRIEND_SCROLL = Scroll(ISLAND_FRIEND_SCROLL, color=(255, 255, 255))
ISLAND_FRIEND_SCROLL.drag_threshold = 0.05
ISLAND_FRIEND_SCROLL.edge_threshold = 0.05

PEARL_PRICE_OCR = Digit(PEARL_PRICE_OCR, letter=(255, 255, 255), threshold=128)


class FriendNameOcr(Ocr):
    def after_process(self, result):
        result = super().after_process(result)
        result = result.replace('/', '').replace('\\', '').replace('`', '').replace('_', '')
        return result


class IslandFriend:
    # If success to parse project
    valid: bool
    # button to visit
    visit_button: Button
    # OCR result
    name: str
    # if visited
    visited: bool
    # pearl price on this island
    pearl_price: int

    def __init__(self, image, visit_button, crop_area):
        """
        Args:
            image:
            visit_button:
            crop_area:
        """
        self.image = image
        self.visit_button = visit_button.move((crop_area[0], crop_area[1]))
        self.crop_area = crop_area
        self.x1, self.y1, self.x2, self.y2 = self.visit_button.area
        self.valid = True
        self.visited = False
        self.pearl_price = 0
        self.friend_parse()

    def friend_parse(self):
        area = (self.x1 - 504, self.y1 - 25, self.x1 - 504 + 168, self.y1 - 25 + 22)

        if area[0] < 360 or area[1] < 98 or area[2] > 593 or area[3] > 693:
            self.valid = False
            return

        button = Button(area=area, color=(), button=area, name='FRIEND_NAME')
        ocr = FriendNameOcr(button, lang='cnocr', letter=(63, 64, 66), threshold=128)
        self.name = ocr.ocr(self.image)
        if not self.name:
            self.valid = False
            return

    def __eq__(self, other):
        """
        Args:
            other (IslandFriend):

        Returns:
            bool:
        """
        if not isinstance(other, IslandFriend):
            return False
        if not self.valid or not other.valid:
            return False
        if self.name != other.name:
            return False

        return True

    def __str__(self):
        return self.name


class IslandPearl(IslandUI):
    def pearl_enter(self):
        """
        Pages:
            in: ISLAND_FRIEND_LEAVE
            out: PEARL_CHECK
        """
        logger.hr('Pearl Enter')
        self.move_up(2.8)
        self.move_right(1.6)
        self.move_down(1.8)

        for _ in self.loop():
            if self.appear_then_click(PEARL_ENTER, offset=(20, 20), interval=2):
                continue
            if self.appear(PEARL_CHECK, offset=(20, 20)):
                break

    def pearl_price_get(self):
        """
        Returns:
            int: pearl price ocr result
        """
        ocr = 0
        for _ in self.loop(timeout=1.5):
            ocr = PEARL_PRICE_OCR.ocr(self.device.image)
            if ocr >= 200:
                break

        return ocr

    def friend_detect(self):
        """
        Get all friends from an image.

        Args:
            image (np.ndarray):

        Returns:
            SelectedGrids:
        """
        self.handle_info_bar()
        area = (880, 98, 960, 693)
        friends = SelectedGrids(
            [IslandFriend(self.device.image, button, area) for button in
             TEMPLATE_FRIEND_VISIT.match_multi(self.image_crop(area, copy=False))]
        )
        return friends.select(valid=True)

    def _friend_visit(self, friend):
        """
        Args:
            friend (IslandFriend):

        Returns:
            bool: if visited
        """
        logger.info(f'Visiting {friend}')
        confirm_timer = Timer(1, count=2).start()
        for _ in self.loop():
            if self.island_in_friend(interval=5):
                self.device.click(friend.visit_button)
                continue

            if self.info_bar_count():
                return False

            if self.appear(ISLAND_FRIEND_LEAVE, offset=(20, 20)):
                if confirm_timer.reached():
                    break
                continue
            else:
                confirm_timer.reset()
        return True

    def friend_leave(self):
        logger.hr('Friend Leave')
        self.island_ui_back()
        for _ in self.loop():
            if self.appear_then_click(ISLAND_FRIEND_LEAVE, offset=(20, 20), interval=2):
                continue

            if self.ui_page_appear(page_island):
                break
            if self.ui_page_appear(page_island_phone):
                break
        self.device.sleep(1.5)
        self.device.click_record_clear()
        self.ui_ensure_friend_page()
        # ISLAND_FRIEND_SCROLL.set_top(main=self)

    def friend_visit(self, current_friends, friends):
        """
        Visit a friend's island, get the pearl price then leave

        Args:
            current_friends (SelectedGrids):
            friends (SelectedGrids):

        Returns:
            SelectedGrids:
        """
        logger.hr('Friend Visit')
        friend: IslandFriend = friends.intersect_by_eq(current_friends).select(visited=False).first_or_none()
        if friend is None or friend.name not in current_friends.get('name'):
            return friends

        if self._friend_visit(friend):
            self.device.sleep(2)
            self.pearl_enter()
            friend.pearl_price = self.pearl_price_get()
            print(friend.name)
            self.friend_leave()
        friend.visited = True
        return friends

    def pearl_run(self):
        """
        Visit each friend's island, get the pearl price, and show in the logger

        Returns:
            SelectedGrids:
        """
        logger.hr('Island Pearl', level=1)
        bottom = False
        friends = SelectedGrids([])
        if ISLAND_FRIEND_SCROLL.appear(main=self):
            ISLAND_FRIEND_SCROLL.set_top(main=self)
        count = 0
        for _ in self.loop():
            if count > 2:
                break
            current_friends = self.friend_detect()
            friends = friends.add_by_eq(current_friends)
            friends = self.friend_visit(current_friends, friends)
            current_friends = friends.intersect_by_eq(current_friends)

            if ISLAND_FRIEND_SCROLL.appear(main=self):
                if ISLAND_FRIEND_SCROLL.at_bottom(main=self):
                    if not bottom:
                        ISLAND_FRIEND_SCROLL.drag_threshold = 0.01
                        ISLAND_FRIEND_SCROLL.edge_threshold = 0.01
                        bottom = True
                        continue
                    logger.info('Island friend reach bottom, stop')
                    break
                elif not current_friends.select(visited=False):
                    ISLAND_FRIEND_SCROLL.next_page(main=self)
                    count += 1

        return friends

    @staticmethod
    def show(data):
        """
        +----------+---------------+
        |  Player  |  Pearl Price  |
        +----------+---------------+
        |    a     |    200        |
        |    b     |    300        |
        |    c     |    400        |
        +----------+---------------+
        """
        table = Table(show_lines=True)
        table.add_column(
            'Player', header_style="bright_cyan", style="cyan", no_wrap=True
        )
        table.add_column("Pearl Price", style="magenta")
        for row in zip(data.get('name'), data.get('pearl_price')):
            table.add_row(
                row[0],
                str(row[1]),
            )
        logger.print(table, justify='center')

    def run(self):
        self.device.screenshot()
        self.ui_ensure_friend_page()
        friends = self.pearl_run()
        friends = friends.select(visited=True)
        self.show(friends)


if __name__ == '__main__':
    self = IslandPearl('alas')
    self.device.screenshot()
    self.run()
