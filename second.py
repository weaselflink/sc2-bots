import random

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
        self.game_minutes: float = 0
        self.main_target: Point2 = Point2()
        self.hard_counter_seen: bool = False
        self.hard_counter_types: Set[UnitTypeId] = {UnitTypeId.COLOSSUS, UnitTypeId.BATTLECRUISER, UnitTypeId.MEDIVAC}

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

    async def build_barracks(self):
        racks = self.structures(UnitTypeId.BARRACKS)
        if racks.amount > 2:
            if not self.structures(UnitTypeId.BARRACKSTECHLAB) and not self.already_pending(UnitTypeId.BARRACKSTECHLAB):
                racks.random(AbilityId.BUILD_TECHLAB)
                return True
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
        tech_labs = self.structures(UnitTypeId.BARRACKSTECHLAB)
        if tech_labs:
            tech_lab = tech_labs.random
            if self.can_cast(tech_lab, AbilityId.RESEARCH_COMBATSHIELD):
                tech_lab(AbilityId.RESEARCH_COMBATSHIELD)
        if ebay:
            if self.inf_weapons == 1 and self.inf_armor == 1:
                await self.fulfill_building_need(UnitTypeId.FACTORY, ebay.first)
            if self.inf_weapons == 1 and self.inf_armor == 1 and factory:
                await self.fulfill_building_need(UnitTypeId.ARMORY, ebay.first)
            if self.inf_weapons < 1 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            if self.inf_armor < 1 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            if self.inf_weapons < 2 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            if self.inf_armor < 2 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
            if self.inf_weapons < 3 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            if self.inf_armor < 3 and await self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3):
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
            enemy_units = self.enemy_units.visible
            threats = enemy_units - enemy_units({UnitTypeId.OVERLORD, UnitTypeId.OVERSEER, UnitTypeId.LARVA})
            for t in threats:
                if self.structures.closest_distance_to(t) < 30:
                    for m in marines:
                        m.attack(threats.closest_to(m))
                    return

            enemies = enemy_units + self.enemy_structures.visible
            if marines.amount >= 40 and enemies:
                for m in marines:
                    m.attack(enemies.closest_to(m))
                    return

            marines_at_enemy_base = marines.closer_than(10, self.main_target)
            if not enemies and marines_at_enemy_base.amount > 20:
                empty_expansions = list(filter(lambda x: self.townhalls.closest_distance_to(x) > 5, self.expansion_locations_list))
                self.main_target = random.choice(empty_expansions)

            if marines.amount >= self.game_minutes * 2.5 or marines.amount >= 40:
                for m in marines:
                    if m.distance_to(self.main_target) > 5:
                        m.attack(self.main_target)

    async def control_vikings(self):
        vikings = self.units(UnitTypeId.VIKING)
        if vikings:
            main_targets = self.enemy_units(self.hard_counter_types).visible
            if main_targets:
                for v in vikings:
                    v.attack(main_targets.closest_to(v))
                return
            secondary_targets = self.enemy_units.visible.flying
            if secondary_targets:
                for v in vikings:
                    v.attack(secondary_targets.closest_to(v))
                return

    async def counter_counter(self):
        if self.enemy_units(self.hard_counter_types):
            self.hard_counter_seen = True
        if self.hard_counter_seen and self.structures(UnitTypeId.STARPORT).amount < 2 and not self.already_pending(UnitTypeId.STARPORT):
            await self.build(UnitTypeId.STARPORT, self.structures(UnitTypeId.ENGINEERINGBAY).first)


    async def on_upgrade_complete(self, upgrade: UpgradeId):
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL1:
            self.inf_weapons = 1
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL1:
            self.inf_armor = 1
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL2:
            self.inf_weapons = 2
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL2:
            self.inf_armor = 2

    async def on_start(self):
        self.main_target = self.enemy_start_locations[0]

    async def on_step(self, iteration: int):
        self.game_minutes = (self.state.game_loop / 22.4) / 60

        await self.update_depots()
        await self.build_depots()
        await self.distribute_workers()
        await self.build_barracks()
        await self.build_first_engineering_bay()
        await self.build_refineries()
        await self.upgrade_infantry()
        await self.control_marines()
        await self.build_expansions()
        await self.build_planetary_fortress()
        await self.counter_counter()

        for cc in self.townhalls:
            if cc.health < cc.health_max:
                repairing_workers = self.workers.filter(lambda w: w.is_repairing).closer_than(10, cc)
                if repairing_workers.amount < 4:
                    avail_workers = self.workers.filter(lambda w: not w.is_repairing)
                    near_workers = avail_workers.closer_than(10, cc)
                    if near_workers.amount > 3:
                        for nw in near_workers:
                            nw.repair(cc)
                    else:
                        for aw in avail_workers.closest_n_units(cc, 10):
                            aw.repair(cc)
                break

        if self.supply_left > 0:
            idle_ccs = self.townhalls.idle
            if idle_ccs and self.worker_count() < 100:
                idle_ccs.first.train(UnitTypeId.SCV, can_afford_check=True)

            idle_starports = self.structures(UnitTypeId.STARPORT).idle
            if idle_starports and self.units(UnitTypeId.VIKING).amount < 10:
                idle_starports.first.train(UnitTypeId.VIKING, can_afford_check=True)

            idle_barracks = self.structures(UnitTypeId.BARRACKS).idle
            if idle_barracks and self.units(UnitTypeId.MARINE).amount < 100:
                idle_barracks.first.train(UnitTypeId.MARINE, can_afford_check=True)

        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(self.townhalls.first))


run_game(maps.get("AcropolisLE"), [
    Bot(Race.Terran, SecondBot()),
    Computer(Race.Random, Difficulty.Hard)
], realtime=False)
