from datetime import datetime, timedelta
import re


from module.base.timer import Timer
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
    @property
    def battle_time(self):
        return BattleTime(BATTLE_TIME, letter=(148, 255, 99)).ocr(self.device.image)

    @property
    def quit_time(self):
        string: str = self.config.Daemon_15_1_QuitTime
        string = string.strip().replace('：', ':')
        t = datetime.strptime(string, "%M:%S")
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second).total_seconds()

    def run(self):
        move = True
        end = False
        pause_interval = Timer(0.5, count=1)
        self.device.screenshot_interval_set()
        self.device.stuck_record_clear()
        self.device.click_record_clear()
        while 1:
            self.device.screenshot()

            pause = self.is_combat_executing()
            # running a combat
            if pause:
                if not self.config.Daemon_15_1_AutoCombat and move:
                    move = False
                    self.device.long_click(MOVE_DOWN, duration=1.5)
                    self.device.long_click(MOVE_LEFT, duration=(3, 4))
                    continue

                # End
                if not end and self.battle_time.total_seconds() == self.quit_time + 1:
                    end = True
                    with self.stat.new(
                            genre='campaign_15_1', method='save'
                    ) as drop:
                        if drop:
                            drop.handle_add(self)
                    continue
            else:
                if self.appear_then_click(MAP_OFFENSIVE, interval=2):
                    continue

            if end:
                pause = self.is_combat_executing()
                if pause:
                    self.device.screenshot_interval_set()
                    self.device.stuck_record_clear()
                    self.device.click_record_clear()
                    end = False
                    self.device.click(pause)
                    pause_interval.reset()
                continue
            
            # Quit
            if self.handle_combat_quit():
                pause_interval.reset()
                continue
            if self.appear_then_click(QUIT_RECONFIRM, offset=(20, 20), interval=5):
                move = True
                self.interval_reset(QUIT)
                pause_interval.reset()
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

            # No end condition, stop it manually.

        return True


if __name__ == '__main__':
    b = AzurLaneDaemon('alas', task='Daemon')
    b.run()
