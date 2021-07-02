from typing import Set

import sc2
from sc2 import UnitTypeId, Union
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class SpinBotBase(sc2.BotAI):

    inf_weapons: int = 0
    inf_armor: int = 0
    vehicle_weapons: int = 0
    vehicle_armor: int = 0
    units_took_damage: Set[int] = set()

    def __init__(self):
        super().__init__()
        self.game_minutes: float = 0

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float):
        self.units_took_damage.add(unit.tag)

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL1:
            self.inf_weapons = 1
        elif upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL2:
            self.inf_weapons = 2
        elif upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL3:
            self.inf_weapons = 3
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL1:
            self.inf_armor = 1
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL2:
            self.inf_armor = 2
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL3:
            self.inf_armor = 3
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL1:
            self.vehicle_weapons = 1
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL2:
            self.vehicle_weapons = 2
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL3:
            self.vehicle_weapons = 3
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1:
            self.vehicle_armor = 1
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2:
            self.vehicle_armor = 2
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3:
            self.vehicle_armor = 3

    def has_building(self, where: sc2.Union[Unit, Point2]) -> bool:
        return self.structures.closest_distance_to(where) < 0.5

    @property
    def main_base(self) -> Unit:
        if self.townhalls:
            return self.start_location.closest(self.townhalls)
        else:
            pass

    def free_geysers(self, base):
        base_geysers = self.vespene_geyser.closer_than(20, base)
        base_refineries = self.gas_buildings.closer_than(20, base)
        if base_refineries:
            return base_geysers.filter(lambda g: base_refineries.closest_distance_to(g) > 1)
        else:
            return base_geysers

    async def fulfill_building_need(self, building_type: UnitTypeId, near: Union[Unit, Point2], count: int = 1):
        buildings = self.structures(building_type)
        if buildings.amount < count and self.can_build_once(building_type):
            await self.build(building_type, near)
            return True
        return False

    def can_build_once(self, building_type: UnitTypeId):
        return self.can_afford(building_type) and not self.already_pending(building_type)

    @staticmethod
    def center(units: Units) -> Unit:
        avg = Point2([0, 0])
        for u in units:
            avg += u.position
        avg /= units.amount
        return units.closest_to(avg)

    async def on_step(self, iteration: int):
        self.game_minutes = (self.state.game_loop / 22.4) / 60


