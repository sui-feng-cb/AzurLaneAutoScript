from datetime import datetime, timedelta
import re


from module.base.timer import Timer
from module.base.utils import copy_image
from module.campaign.campaign_base import CampaignBase
from module.combat.assets import BATTLE_TIME, MOVE_DOWN, MOVE_LEFT
from module.combat_ui.assets import QUIT
from module.daemon.daemon_base import DaemonBase
from module.exception import CampaignEnd
from module.exercise.assets import QUIT_RECONFIRM
from module.handler.ambush import MAP_AMBUSH_EVADE
from module.logger import logger
from module.map.assets import MAP_OFFENSIVE
from module.ocr.ocr import Duration


class BattleTime(Duration):
    SHOW_LOG = False

    def __init__(self, buttons, lang='azur_lane', letter=(148, 255, 99), threshold=128, alphabet='0123456789:IDSB',
                 name=None):
        super().__init__(buttons, lang=lang, letter=letter, threshold=threshold, alphabet=alphabet, name=name)

    @staticmethod
    def parse_time(string):
        result = re.search(r'(\d{1,2}):?(\d{2})', string)
        if result:
            result = [int(s) for s in result.groups()]
            return timedelta(hours=0, minutes=result[0], seconds=result[1])
        else:
            logger.warning(f'Invalid duration: {string}')
            return timedelta(hours=0, minutes=0, seconds=0)
        

class AzurLaneDaemon(DaemonBase, CampaignBase):
    battle_time_ocr_model = BattleTime(BATTLE_TIME)

    @property
    def battle_time(self):
        return self.battle_time_ocr_model.ocr(self.device.image).total_seconds()

    @property
    def quit_time(self):
        string = self.config.Daemon_15_1_QuitTime
        string = string.strip().replace('：', ':')
        t = datetime.strptime(string, "%M:%S")
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second).total_seconds()

    def run(self):
        move = True
        is_limit = False
        end = False
        self.device.screenshot_interval_set()
        self.config.override(Emulator_ControlMethod='uiautomator2')
        while 1:
            self.device.screenshot()

            # End
            if is_limit and self.config.Daemon_15_1_RunCount <= 0:
                logger.hr('Triggered stop condition: Run count')
                self.config.Daemon_15_1_RunCount = 0
                end = True
            is_limit = self.config.Daemon_15_1_RunCount
            pause = self.is_combat_executing()
            # running a combat
            if pause:
                if not self.config.Daemon_15_1_AutoCombat and move:
                    move = False
                    self.device.long_click(MOVE_DOWN, duration=self.config.Daemon_15_1_MoveDownTime)
                    self.device.long_click(MOVE_LEFT, duration=(3, 4))
                    continue

                # End
                battle_time = self.battle_time
                if battle_time and battle_time <= self.quit_time:
                    with self.stat.new(genre='campaign_15_1', method='save') as record:
                        if self.config.Daemon_15_1_RunCount:
                            self.config.Daemon_15_1_RunCount -= 1
                        combat_image = copy_image(self.device.image)

                        self.device.screenshot_interval_set()
                        skip_first_screenshot = True
                        pause_interval = Timer(0.5, count=1)
                        while 1:
                            if skip_first_screenshot:
                                skip_first_screenshot = False
                            else:
                                self.device.screenshot()

                            if pause_interval.reached():
                                pause = self.is_combat_executing()
                                if pause:
                                    self.device.click(pause)
                                    pause_interval.reset()
                                    continue

                            if QUIT.match_luma(self.device.image, offset=(20, 20)):
                                record.add(combat_image)
                                if self.config.Daemon_15_1_QuitScreenshot:
                                    record.add(self.device.image)
                                break
                    continue

            # Quit
            if self.handle_combat_quit():
                continue
            if self.appear_then_click(QUIT_RECONFIRM, offset=(20, 20), interval=5):
                move = True
                if end:
                    break
                continue

            # Combat
            if self.combat_appear():
                self.combat_preparation(auto='combat_auto' if self.config.Daemon_15_1_AutoCombat else '')
            try:
                if self.handle_battle_status():
                    self.combat_status(expected_end='no_searching')
                    continue
            except CampaignEnd:
                continue

            # Map operation
            if self.appear_then_click(MAP_AMBUSH_EVADE, offset=(20, 20)):
                self.device.sleep(1)
                continue
            if self.handle_mystery_items():
                continue

            # Retire
            if self.handle_retirement():
                continue

            # Emotion
            pass

            # Urgent commission
            if self.handle_urgent_commission():
                continue

            # Popups
            if self.handle_guild_popup_cancel():
                return True
            if self.handle_vote_popup():
                continue

            # Story
            if self.story_skip():
                continue

            # Map Offensive
            if not end and self.appear_then_click(MAP_OFFENSIVE, interval=2):
                continue

        return True
