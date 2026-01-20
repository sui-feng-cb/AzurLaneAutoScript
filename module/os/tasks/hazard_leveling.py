from module.logger import logger
from module.os.map import OSMap


class OpsiHazard1Leveling(OSMap):
    def os_hazard1_leveling(self):
        logger.hr('OS hazard 1 leveling', level=1)
        # Without these enabled, CL1 gains 0 profits
        self.config.override(
            OpsiGeneral_DoRandomMapEvent=True,
            OpsiGeneral_AkashiShopFilter='ActionPoint',
        )
        if not self.config.is_task_enabled('OpsiMeowfficerFarming'):
            self.config.cross_set(keys='OpsiMeowfficerFarming.Scheduler.Enable', value=True)
        while True:
            # Limited action point preserve of hazard 1 to 200
            self.config.OS_ACTION_POINT_PRESERVE = 200
            if self.config.is_task_enabled('OpsiAshBeacon') \
                    and not self._ash_fully_collected \
                    and self.config.OpsiAshBeacon_EnsureFullyCollected:
                logger.info('Ash beacon not fully collected, ignore action point limit temporarily')
                self.config.OS_ACTION_POINT_PRESERVE = 0
            logger.attr('OS_ACTION_POINT_PRESERVE', self.config.OS_ACTION_POINT_PRESERVE)

            if self.get_yellow_coins() < self.config.OpsiHazard1Leveling_OperationCoinsPreserve:
                logger.info(f'Reach the limit of yellow coins, preserve={self.config.OpsiHazard1Leveling_OperationCoinsPreserve}')
                with self.config.multi_set():
                    self.config.task_delay(minute=27, server_update=True)
                    if not self.is_in_opsi_explore():
                        if self.nearest_task_cooling_down is None:
                            for task in ['OpsiAbyssal', 'OpsiObscure']:
                                self.config.task_call(task, force_call=False)
                            if self.config.is_task_enabled('OpsiStronghold'):
                                if self.config.cross_get(keys='OpsiStronghold.OpsiStronghold.HasStronghold'):
                                    self.config.task_call('OpsiStronghold')
                                else:
                                    logger.info('No stronghold left, skip task call')
                        self.config.task_call('OpsiMeowfficerFarming', force_call=False)
                self.config.task_stop()

            self.get_current_zone()

            # Preset action point to 70
            # When running CL1 oil is for running CL1, not meowfficer farming
            keep_current_ap = True
            if self.config.OpsiGeneral_BuyActionPointLimit > 0:
                keep_current_ap = False
            self.action_point_set(cost=70, keep_current_ap=keep_current_ap, check_rest_ap=True)

            if self.config.OpsiHazard1Leveling_TargetZone != 0:
                zone = self.config.OpsiHazard1Leveling_TargetZone
            else:
                zone = 22
            logger.hr(f'OS hazard 1 leveling, zone_id={zone}', level=1)
            if self.zone.zone_id != zone or not self.is_zone_name_hidden:
                self.globe_goto(self.name_to_zone(zone), types='SAFE', refresh=True)
            self.fleet_set(self.config.OpsiFleet_Fleet)
            self.run_strategic_search()
            self.get_current_zone()
            if self.is_zone_name_hidden and not len(self._solved_map_event):
                self.fleets_clear_question()
            self.handle_after_auto_search()
            self.config.check_task_switch()
