from module.logger import logger
from module.campaign.campaign_base import CampaignBase
from module.map.map_grids import SelectedGrids, RoadGrids

from .campaign_16_base import CampaignBase, CampaignMap
from .campaign_16_base import Config as ConfigBase

MAP = CampaignMap('16-4')
MAP.shape = 'K8'
MAP.camera_data = ['C2', 'C6', 'F2', 'F6', 'H2', 'H6']
MAP.camera_data_spawn_point = ['C6']
MAP.camera_sight = (-2, -1, 3, 2)
MAP.map_data = """
    -- -- ++ -- -- -- ++ ME -- -- MB
    ME ++ ++ ++ -- -- ME ++ -- -- --
    -- -- ME -- -- ++ ++ ME -- -- --
    -- -- -- ME ++ -- ME -- ++ ++ --
    -- -- ME -- -- ME ++ -- ME ++ --
    -- __ -- ++ ++ -- ++ ME ME -- --
    SP -- -- ME -- -- ME ++ -- ++ ++
    SP -- -- -- ++ -- ++ ++ -- -- ++
"""
MAP.weight_data = """
    50 50 50 50 50 50 50 50 50 50 50
    50 50 50 50 50 50 50 50 50 50 50
    50 50 50 50 50 50 50 40 50 50 50
    50 50 50 40 50 40 40 40 50 50 50
    50 50 50 40 40 40 50 50 50 50 50
    50 50 50 50 50 50 50 50 50 50 50
    50 50 50 50 50 50 50 50 50 50 50
    50 50 50 50 50 50 50 50 50 50 50
"""
MAP.spawn_data = [
    {'battle': 0, 'enemy': 5},
    {'battle': 1, 'enemy': 4},
    {'battle': 2, 'enemy': 5},
    {'battle': 3},
    {'battle': 4, 'boss': 1},
]
A1, B1, C1, D1, E1, F1, G1, H1, I1, J1, K1, \
A2, B2, C2, D2, E2, F2, G2, H2, I2, J2, K2, \
A3, B3, C3, D3, E3, F3, G3, H3, I3, J3, K3, \
A4, B4, C4, D4, E4, F4, G4, H4, I4, J4, K4, \
A5, B5, C5, D5, E5, F5, G5, H5, I5, J5, K5, \
A6, B6, C6, D6, E6, F6, G6, H6, I6, J6, K6, \
A7, B7, C7, D7, E7, F7, G7, H7, I7, J7, K7, \
A8, B8, C8, D8, E8, F8, G8, H8, I8, J8, K8, \
    = MAP.flatten()

roads = [RoadGrids([D4, F5, G4, H3])]


class Config(ConfigBase):
    # ===== Start of generated config =====
    MAP_HAS_MAP_STORY = False
    MAP_HAS_FLEET_STEP = False
    MAP_HAS_AMBUSH = True
    # ===== End of generated config =====

    INTERNAL_LINES_FIND_PEAKS_PARAMETERS = {
        'height': (120, 255 - 17),
        'width': (0.9, 10),
        'prominence': 10,
        'distance': 35,
    }
    EDGE_LINES_FIND_PEAKS_PARAMETERS = {
        'height': (255 - 50, 255),
        'prominence': 10,
        'distance': 50,
        'wlen': 1000
    }
    INTERNAL_LINES_HOUGHLINES_THRESHOLD = 25
    EDGE_LINES_HOUGHLINES_THRESHOLD = 25
    MAP_WALK_USE_CURRENT_FLEET = True


class Campaign(CampaignBase):
    MAP = MAP

    def battle_default(self):
        if self.clear_roadblocks(roads):
            return True
        if self.clear_potential_roadblocks(roads):
            return True
        if self.clear_filter_enemy(self.ENEMY_FILTER, preserve=1):
            return True

        return super().battle_default()

    def battle_0(self):
        if self.clear_chosen_enemy(D4):
            return True

        return self.battle_default()

    def battle_1(self):
        if not self.map_is_clear_mode:
            self.destroy_land_base(C1, D1, D1)

        if self.clear_chosen_enemy(F5):
            return True

        return self.battle_default()

    def battle_2(self):
        if self.clear_chosen_enemy(G4):
            return True

        return self.battle_default()

    def battle_3(self):
        if self.clear_chosen_enemy(H3):
            return True

        return self.battle_default()

    def battle_4(self):
        if not self.map_is_clear_mode:
            # destroy K8 and G8 land base in one air attack
            self.destroy_land_base(K8, J6, I8)

        boss = self.map.select(is_boss=True)
        if boss:
            return self.fleet_boss.brute_clear_boss()

        if self.clear_roadblocks(roads):
            return True
        if self.clear_potential_roadblocks(roads):
            return True
        if self.clear_filter_enemy(self.ENEMY_FILTER, preserve=0):
            return True

        return self.battle_default()
