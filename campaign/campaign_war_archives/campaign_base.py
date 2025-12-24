from module.campaign.campaign_base import CampaignBase as CampaignBase_
from module.exception import RequestHumanTakeover
from module.logger import logger
from module.ui.assets import WAR_ARCHIVES_CHECK
from module.ui.page import page_archives
from module.ui.scroll import Scroll
from module.ui.switch import Switch
from module.war_archives.assets import (WAR_ARCHIVES_CAMPAIGN_CHECK,
                                        WAR_ARCHIVES_EX_ON,
                                        WAR_ARCHIVES_SCROLL,
                                        WAR_ARCHIVES_SP_ON)
from module.war_archives.dictionary import dic_archives_template

WAR_ARCHIVES_SWITCH = Switch('War_Archives_switch', is_selector=True)
WAR_ARCHIVES_SWITCH.add_state('ex', WAR_ARCHIVES_EX_ON)
WAR_ARCHIVES_SWITCH.add_state('sp', WAR_ARCHIVES_SP_ON)
WAR_ARCHIVES_SCROLL = Scroll(WAR_ARCHIVES_SCROLL, color=(247, 211, 66), name='WAR_ARCHIVES_SCROLL')


class CampaignBase(CampaignBase_):
    # Helper variable to keep track of whether is the first runthrough
    first_run = True
    ENEMY_FILTER = '1T > 1L > 1E > 1M > 2T > 2L > 2E > 2M > 3T > 3L > 3E > 3M'

    def _get_archives_entrance(self, name):
        """
        Create entrance button to target archive campaign
        using a template acquired by event folder name

        Args:
            name(str): event folder name
        """
        template = dic_archives_template[name]

        sim, button = template.match_result(self.device.image)
        if sim < 0.85:
            return None

        entrance = button.crop((-12, -12, 44, 32), image=self.device.image, name=name)
        return entrance

    def _archives_loading_complete(self):
        """
        Check if war archive has finished loading
        """
        for war_archive_folder in dic_archives_template:
            template = dic_archives_template[war_archive_folder]
            loading_result = template.match(self.device.image)
            if loading_result:
                return True

        return False

    def _search_archives_entrance(self, name, skip_first_screenshot=True):
        """
        Search for entrance using mini-touch scroll down
        at center
        Fixed number of scrolls until give up, may need to
        increase as more war archives campaigns are added
        """
        for _ in range(20):
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            while self.device.click_record and self.device.click_record[-1] == 'WAR_ARCHIVES_SCROLL':
                self.device.click_record.pop()

            # Drag may result in accidental exit, recover
            # before starting next search attempt
            while not self.appear(WAR_ARCHIVES_CHECK):
                self.ui_ensure(destination=page_archives)

            while not self._archives_loading_complete():
                self.device.screenshot()

            entrance = self._get_archives_entrance(name)
            if entrance is not None:
                return entrance

            if WAR_ARCHIVES_SCROLL.appear(main=self):
                if WAR_ARCHIVES_SCROLL.at_bottom(main=self):
                    WAR_ARCHIVES_SCROLL.set_top(main=self)
                else:
                    WAR_ARCHIVES_SCROLL.next_page(main=self, page=0.66)
                continue
            else:
                break

        logger.warning('Failed to find archives entrance')
        return None

    def ui_goto_archives_campaign(self, mode='ex'):
        """
        Performs the operations needed to transition
        to target archive's campaign stage map
        """
        # On first run regardless of current location
        # even in target stage map, start from page_archives
        # For subsequent runs when neither reward or
        # stop_triggers occur, no need perform operations
        result = True
        if self.first_run or not self.appear(WAR_ARCHIVES_CAMPAIGN_CHECK, offset=(20, 20)):
            result = self.ui_ensure(destination=page_archives)

            WAR_ARCHIVES_SWITCH.set(mode, main=self)

            entrance = self._search_archives_entrance(self.config.Campaign_Event)
            if entrance is not None:
                self.ui_click(entrance, appear_button=WAR_ARCHIVES_CHECK, check_button=WAR_ARCHIVES_CAMPAIGN_CHECK,
                              skip_first_screenshot=True)
            else:
                logger.critical('Respective server may not yet support the chosen War Archives campaign, '
                                'check back in the next app update')
                raise RequestHumanTakeover

        # Subsequent runs all set False
        if self.first_run:
            self.first_run = False

        return result

    def ui_goto_event(self):
        """
        Overridden to handle specifically transitions
        to target ex event in page_archives
        """
        return self.ui_goto_archives_campaign(mode='ex')

    def ui_goto_sp(self):
        """
        Overridden to handle specifically transitions
        to target sp event in page_archives
        """
        return self.ui_goto_archives_campaign(mode='sp')

    def check_oil_threshold(self, oil):
        oil_threshold = self.config.InterceptiveCheck_OilThreshold
        if not oil_threshold:
            return False
        logger.attr('Oil Threshold', oil_threshold)
        if oil_threshold <= 3:
            logger.info('Oil Threshold should be at least 4, set to default')
            self.config.InterceptiveCheck_OilThreshold = 0
            return False

        checked = False
        self._prev_oil = self._prev_oil or oil
        diff = abs(self._prev_oil - oil) if self._prev_oil else 0
        if diff > 0:
            logger.attr('Oil Consumption', diff)
            if diff >= 500:
                logger.warning(f"Wrong oil consumption {diff}, assuming it is an ocr error")
                self._prev_oil = 0
                return False
            if diff >= oil_threshold:
                logger.warning("Abnormal oil consumption detected, Withdrawing")
                checked = True
        self._prev_oil = oil
        return checked

    def auto_search_watch_oil(self, checked=False):
        """
        Watch oil.
        This will set auto_search_oil_limit_triggered.
        """
        if not checked:
            oil = self.get_oil()
            if oil == 0:
                logger.warning('Oil not found')
            else:
                if self.check_oil_threshold(oil):
                    self._interrupt = True
                if oil < max(500, self.config.StopCondition_OilLimit):
                    logger.info('Reach oil limit')
                    self.auto_search_oil_limit_triggered = True
                else:
                    if self.auto_search_oil_limit_triggered:
                        logger.warning('auto_search_oil_limit_triggered but oil recovered, '
                                       'probably because of wrong OCR result before')
                    self.auto_search_oil_limit_triggered = False
                checked = True

        return checked

    def auto_search_combat(self, emotion_reduce=None, fleet_index=1, battle=None):
        """
        Execute a combat.

        Note that fleet index == 1 is mob fleet, 2 is boss fleet.
        It's not the fleet index in fleet preparation or auto search setting.
        """
        emotion_reduce = emotion_reduce if emotion_reduce is not None else self.emotion.is_calculate
        if self._interrupt:
            self.interrupt_auto_search(emotion_reduce, fleet_index)
        super().auto_search_combat(emotion_reduce, fleet_index, battle)
