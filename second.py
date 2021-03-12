
import sc2
from sc2 import run_game, maps, Race, Difficulty, Union
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.position import Point2
from sc2.unit import Unit


class SecondBot(sc2.BotAI):
    def __init__(self):
        super().__init__()
        self.inf_weapons: int = 0
        self.inf_armor: int = 0

    def _initialize_variables(self):
        super()._initialize_variables()

    def has_building(self, where: Union[Unit, Point2]):
        return self.structures.closest_distance_to(where) < 0.5

    def worker_count(self) -> int:
        return self.workers.amount

    def main_base(self) -> Unit:
        return self.start_location.closest(self.townhalls)

    def has_enemy_within(self, unit: Unit, dist: int):
        for enemy in self.enemy_units.not_structure:
            if enemy.distance_to(unit) < dist:
                return True
        return False

    async def update_depots(self):
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if not self.has_enemy_within(depot, 15):
                depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        for depot in self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            if self.has_enemy_within(depot, 10):
                depot(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    async def build_depots(self):
        depot_placement_positions = list([p for p in self.main_base_ramp.corner_depots if not self.has_building(p)])
        if self.supply_left < 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
            if depot_placement_positions:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions[0])
            else:
                await self.build(UnitTypeId.SUPPLYDEPOT, self.townhalls.first.position.towards(self.game_info.map_center, 8))

    async def build_first_barracks(self):
        racks = self.structures(UnitTypeId.BARRACKS)
        if self.can_afford(UnitTypeId.BARRACKS) and not self.already_pending(UnitTypeId.BARRACKS):
            if not racks:
                await self.build(UnitTypeId.BARRACKS, self.main_base_ramp.barracks_in_middle)
                return True
            if racks and self.units(UnitTypeId.MARINE).amount < 40 and self.minerals > 400 and self.structures(UnitTypeId.ENGINEERINGBAY):
                await self.build(UnitTypeId.BARRACKS, self.structures(UnitTypeId.ENGINEERINGBAY).first)
                return True
        return False

    async def upgrade_infantry(self):
        ebay = self.structures(UnitTypeId.ENGINEERINGBAY)
        factory = self.structures(UnitTypeId.FACTORY)
        if ebay:
            if self.inf_weapons == 1 and self.inf_armor == 1:
                await self.fulfill_building_need(UnitTypeId.FACTORY, ebay.first)
            if self.inf_weapons == 1 and self.inf_armor == 1 and factory:
                await self.fulfill_building_need(UnitTypeId.ARMORY, ebay.first)
            if self.inf_weapons < 1 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            if self.inf_armor < 1 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            if self.inf_weapons < 2 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            if self.inf_armor < 2 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
            if self.inf_weapons < 3 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            if self.inf_armor < 3 and self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3)

    async def fulfill_building_need(self, building_type: UnitTypeId, near: Union[Unit, Point2]):
        buildings = self.structures(building_type)
        if not buildings and not self.already_pending(building_type):
            await self.build(building_type, near)
            return True
        return False

    async def build_first_engineering_bay(self):
        near = self.main_base().position.towards(self.game_info.map_center, 8)
        await self.fulfill_building_need(UnitTypeId.ENGINEERINGBAY, near)

    async def build_expansions(self):
        if self.can_afford(UnitTypeId.COMMANDCENTER) and not self.already_pending(UnitTypeId.COMMANDCENTER):
            await self.expand_now()
            return True
        return False

    async def build_refineries(self):
        if self.townhalls.ready.amount > 1 and self.can_afford(UnitTypeId.REFINERY):
            empty_main_base_geysers = self.empty_geysers(self.main_base())
            if empty_main_base_geysers:
                location = empty_main_base_geysers.first
                await self.build(UnitTypeId.REFINERY, location)
                return True
        return False

    def empty_geysers(self, base):
        base_geysers = self.vespene_geyser.closer_than(25, base)
        base_refineries = self.structures(UnitTypeId.REFINERY).closer_than(25, base)
        if base_refineries:
            return base_geysers.filter(lambda g: base_refineries.closest_distance_to(g) > 1)
        else:
            return base_geysers

    async def build_planetary_fortress(self):
        if self.structures(UnitTypeId.ENGINEERINGBAY):
            if self.can_afford(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS):
                need_upgrade = self.townhalls(UnitTypeId.COMMANDCENTER).idle
                if need_upgrade:
                    upgrading = need_upgrade.closest_to(self.main_base())
                    upgrading(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)
                    return True
        return False

    async def control_marines(self):
        marines = self.units(UnitTypeId.MARINE)
        if marines:
            threats = self.enemy_units.visible
            for t in threats:
                if self.structures.closest_distance_to(t) < 30:
                    for m in marines:
                        m.attack(threats.closest_to(m))
                    return

            enemies = (self.enemy_units + self.enemy_structures).visible
            if marines.amount >= 40 and enemies:
                for m in marines:
                    m.attack(enemies.closest_to(m))
                    return

            target = self.enemy_start_locations[0]
            marines_at_enemy_base = marines.closer_than(10, target)
            if not enemies and marines_at_enemy_base.amount > 40:
                candidates = list(filter(lambda e: not self.is_visible(e), self.expansion_locations_list))
                if candidates:
                    for m in marines:
                        m.attack(candidates[0])
                    return

            if marines.amount >= 12:
                for m in marines:
                    if m.distance_to(target) > 5:
                        m.attack(target)

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL1:
            self.inf_weapons = 1
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL1:
            self.inf_armor = 1
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL2:
            self.inf_weapons = 2
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL2:
            self.inf_armor = 2

    async def on_step(self, iteration: int):
        await self.update_depots()
        await self.build_depots()
        await self.distribute_workers()
        await self.build_first_barracks()
        await self.build_first_engineering_bay()
        await self.build_refineries()
        await self.upgrade_infantry()
        await self.control_marines()
        await self.build_expansions()
        await self.build_planetary_fortress()

        for cc in self.townhalls:
            if cc.health < cc.health_max:
                repairing_workers = self.workers.filter(lambda w: w.is_repairing).closer_than(10, cc)
                if repairing_workers.amount < 4:
                    avail_workers = self.workers.filter(lambda w: not w.is_repairing)
                    near_workers = avail_workers.closer_than(10, cc)
                    if near_workers.amount > 3:
                        for w in near_workers:
                            w.repair(cc)
                    else:
                        for w in avail_workers.closest_n_units(cc, 10):
                            w.repair(cc)
                break

        if self.supply_left > 0:
            idle_ccs = self.townhalls.idle
            if idle_ccs and self.worker_count() < 100:
                idle_ccs.first.train(UnitTypeId.SCV, can_afford_check=True)

            idle_barracks = self.structures(UnitTypeId.BARRACKS).idle
            if idle_barracks and self.units(UnitTypeId.MARINE).amount < 100:
                idle_barracks.first.train(UnitTypeId.MARINE, can_afford_check=True)

        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(self.townhalls.first))


run_game(maps.get("AcropolisLE"), [
    Bot(Race.Terran, SecondBot()),
    Computer(Race.Random, Difficulty.Medium)
], realtime=False)
