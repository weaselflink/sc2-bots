
import sc2
from sc2 import UnitTypeId, Union, AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class SpinBotBase(sc2.BotAI):

    inf_weapons: int = 0
    inf_armor: int = 0
    ship_weapons: int = 0
    ship_armor: int = 0

    def __init__(self):
        super().__init__()
        self.game_minutes: float = 0

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
        elif upgrade == UpgradeId.TERRANSHIPWEAPONSLEVEL1:
            self.ship_weapons = 1
        elif upgrade == UpgradeId.TERRANSHIPWEAPONSLEVEL2:
            self.ship_weapons = 2
        elif upgrade == UpgradeId.TERRANSHIPWEAPONSLEVEL3:
            self.ship_weapons = 3
        elif upgrade == UpgradeId.TERRANSHIPARMORSLEVEL1:
            self.ship_armor = 1
        elif upgrade == UpgradeId.TERRANSHIPARMORSLEVEL2:
            self.ship_armor = 2
        elif upgrade == UpgradeId.TERRANSHIPARMORSLEVEL3:
            self.ship_armor = 3

    def has_building(self, where: sc2.Union[Unit, Point2]) -> bool:
        return self.structures.closest_distance_to(where) < 0.5

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


class OrbitalCommander:
    bot: SpinBotBase
    call_down = AbilityId.CALLDOWNMULE_CALLDOWNMULE

    def __init__(self, bot: SpinBotBase):
        super().__init__()
        self.bot = bot

    async def command(self):
        if self.bot.state.game_loop % 10 != 0:
            return
        await self.mule()

    async def mule(self):
        orbitals = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready
        if orbitals:
            can_mule = await self.can_mule(orbitals)
            if can_mule:
                muleable = self.muleable_minerals()
                if muleable:
                    can_mule.random(self.call_down, muleable.random)

    async def can_mule(self, orbitals: Units) -> Units:
        can_cast = [o for o in orbitals if await self.can_cast_mule(o)]
        return Units(can_cast, self.bot)

    async def can_cast_mule(self, unit: Unit):
        return await self.bot.can_cast(unit, self.call_down, only_check_energy_and_cooldown=True)

    def muleable_minerals(self) -> Units:
        ready_bases = self.bot.townhalls.ready
        if not ready_bases:
            return Units([], self.bot)
        else:
            return self.bot.mineral_field.in_distance_of_group(ready_bases, 9)
