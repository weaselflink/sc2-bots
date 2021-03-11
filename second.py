
import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class SecondBot(sc2.BotAI):
    def worker_count(self) -> int:
        return self.workers.amount

    def main_base(self) -> Unit:
        return self.start_location.closest(self.townhalls)

    def has_enemy_within(self, unit, dist):
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
        depots: Units = self.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})
        depot_placement_positions: Set[Point2] = self.main_base_ramp.corner_depots
        if self.supply_left < 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
            if depots.amount < 1:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions.pop())
            elif depots.amount < 2:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions.pop())
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

    async def upgrade_marines(self):
        ebay = self.structures(UnitTypeId.ENGINEERINGBAY)
        if ebay:
            if self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            if self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            if self.can_cast(ebay.first, AbilityId.RESEARCH_COMBATSHIELD):
                ebay.first(AbilityId.RESEARCH_COMBATSHIELD)
            if self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            if self.can_cast(ebay.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                ebay.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)

    async def build_first_engineering_bay(self):
        all_racks = self.structures(UnitTypeId.ENGINEERINGBAY)
        if not all_racks and self.can_afford(UnitTypeId.ENGINEERINGBAY) and not self.already_pending(UnitTypeId.ENGINEERINGBAY):
            await self.build(UnitTypeId.ENGINEERINGBAY, self.main_base().position.towards(self.game_info.map_center, 8))
            return True
        return False

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

    async def on_step(self, iteration):
        await self.update_depots()
        await self.build_depots()
        await self.distribute_workers()
        await self.build_first_barracks()
        await self.build_first_engineering_bay()
        await self.build_refineries()
        await self.upgrade_marines()

        enemies = (self.enemy_units + self.enemy_structures).visible
        if enemies and self.units(UnitTypeId.MARINE):
            for m in self.units(UnitTypeId.MARINE):
                close_units = self.enemy_units.visible.closer_than(10, m)
                if close_units:
                    m.attack(close_units.closest_to(m))
                else:
                    m.attack(enemies.closest_to(m))

        if not enemies and self.units(UnitTypeId.MARINE).amount >= 10:
            for m in self.units(UnitTypeId.MARINE):
                m.attack(self.enemy_start_locations[0])

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
    Computer(Race.Protoss, Difficulty.Medium)
], realtime=False)
