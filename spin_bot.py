import random
from math import floor

from sc2.constants import *
from sc2.position import Point2
from sc2.unit import Unit

from spin_bot_base import SpinBotBase


class SpinBot(SpinBotBase):
    inf_weapons: int = 0
    inf_armor: int = 0
    main_target: Point2 = Point2()
    hard_counter_types: Set[UnitTypeId] = {UnitTypeId.COLOSSUS, UnitTypeId.BATTLECRUISER, UnitTypeId.MEDIVAC}
    units_took_damage: set[int] = set()

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
        if self.supply_left < 2 and self.can_build_once(UnitTypeId.SUPPLYDEPOT):
            if depot_placement_positions:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions)
                return True
            else:
                await self.build(UnitTypeId.SUPPLYDEPOT,
                                 self.townhalls.first.position.towards(self.game_info.map_center, 8))
                return True
        return False

    async def build_barracks(self):
        racks = self.structures(UnitTypeId.BARRACKS)
        if racks.amount > 2:
            if not self.structures(UnitTypeId.BARRACKSTECHLAB) and not self.already_pending(UnitTypeId.BARRACKSTECHLAB):
                racks.random(AbilityId.BUILD_TECHLAB)
        if self.can_build_once(UnitTypeId.BARRACKS) and racks.amount < self.townhalls.amount * 2 and racks.amount < 16:
            if not racks:
                await self.build(UnitTypeId.BARRACKS, self.main_base_ramp.barracks_in_middle)
                return True
            elif self.units(UnitTypeId.MARINE).amount < 40 and self.minerals > 400 and self.structures(
                    UnitTypeId.ENGINEERINGBAY):
                await self.build(UnitTypeId.BARRACKS, self.structures(UnitTypeId.ENGINEERINGBAY).first)
                return True
        return False

    async def build_starports(self):
        ebays = self.structures(UnitTypeId.ENGINEERINGBAY)
        starports = self.structures(UnitTypeId.STARPORT)
        if starports and starports.amount < 4 and starports.amount < self.townhalls.amount:
            wanted_starports = floor(self.game_minutes / 5)
            await self.fulfill_building_need(UnitTypeId.STARPORT, ebays.first, wanted_starports)

    async def build_upgrades(self):
        ebays = self.structures(UnitTypeId.ENGINEERINGBAY)
        factories = self.structures(UnitTypeId.FACTORY)
        tech_labs = self.structures(UnitTypeId.BARRACKSTECHLAB)
        if tech_labs:
            tech_lab = tech_labs.random
            if await self.can_cast(tech_lab, AbilityId.RESEARCH_COMBATSHIELD):
                tech_lab(AbilityId.RESEARCH_COMBATSHIELD)
        if ebays:
            await self.fulfill_building_need(UnitTypeId.ENGINEERINGBAY, ebays.first, 2)
            await self.fulfill_building_need(UnitTypeId.FACTORY, ebays.first)
            if factories:
                await self.fulfill_building_need(UnitTypeId.ARMORY, ebays.first)
                await self.fulfill_building_need(UnitTypeId.STARPORT, ebays.first)
        if ebays.idle:
            if self.inf_weapons < 1 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            elif self.inf_armor < 1 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            elif self.inf_weapons < 2 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            elif self.inf_armor < 2 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
            elif self.inf_weapons < 3 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            elif self.inf_armor < 3 and await self.can_cast(
                    ebays.first, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3):
                ebays.idle.first(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3)
            elif self.inf_weapons == 3 and await self.can_cast(ebays.first, AbilityId.RESEARCH_HISECAUTOTRACKING):
                ebays.idle.first(AbilityId.RESEARCH_HISECAUTOTRACKING)
            elif self.inf_weapons == 3 and await self.can_cast(
                    ebays.first, AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE):
                ebays.idle.first(AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE)

    async def build_first_engineering_bay(self):
        if self.townhalls and self.gas_buildings:
            near = self.main_base().position.towards(self.game_info.map_center, 8)
            await self.fulfill_building_need(UnitTypeId.ENGINEERINGBAY, near)

    async def build_expansions(self):
        if self.can_build_once(UnitTypeId.COMMANDCENTER):
            await self.expand_now()
            return True
        return False

    async def build_refineries(self):
        if self.townhalls.amount < 2:
            return False
        if self.can_afford(UnitTypeId.REFINERY):
            if self.townhalls.ready.amount * 2 > self.structures(UnitTypeId.REFINERY).amount:
                need_refinery = self.townhalls.ready.filter(lambda t: self.free_geysers(t).amount > 0)
                if need_refinery:
                    await self.build(UnitTypeId.REFINERY, self.free_geysers(need_refinery.random).random)
                    return True
        return False

    async def build_turrets(self):
        if self.townhalls.amount < 3:
            return False
        if self.can_afford(UnitTypeId.MISSILETURRET):
            turrets = self.structures(UnitTypeId.MISSILETURRET)
            if self.townhalls.ready.amount * 2 > turrets.amount:
                need_turrets = self.townhalls.ready.filter(lambda t: turrets.closer_than(12, t).amount < 2)
                if need_turrets and not self.already_pending(UnitTypeId.MISSILETURRET):
                    await self.build(UnitTypeId.MISSILETURRET, need_turrets.random)
                    return True
        return False

    async def build_planetary_fortress(self):
        if self.townhalls and self.structures(UnitTypeId.ENGINEERINGBAY):
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
            threats = enemy_units - enemy_units({
                UnitTypeId.OVERLORD, UnitTypeId.OVERSEER, UnitTypeId.LARVA, UnitTypeId.EGG
            })
            for t in threats:
                if self.structures.closest_distance_to(t) < 30:
                    for m in marines:
                        m.attack(threats.closest_to(m))
                    return

            enemies = (enemy_units - enemy_units({UnitTypeId.LARVA, UnitTypeId.EGG})) + self.enemy_structures.visible
            if marines.amount >= 40 and enemies:
                for m in marines:
                    m.attack(enemies.closest_to(m))
                    return

            marines_at_enemy_base = marines.closer_than(10, self.main_target)
            if not enemies and marines_at_enemy_base.amount > 20:
                empty_expansions = list(
                    filter(lambda x: self.townhalls.closest_distance_to(x) > 5, self.expansion_locations_list)
                )
                self.main_target = random.choice(empty_expansions)

            if marines.amount >= self.game_minutes * 2.5 or marines.amount >= 40:
                for m in marines:
                    if m.distance_to(self.main_target) > 5:
                        m.attack(self.main_target)
                return

            rally_point = self.center(marines).position
            for m in marines:
                if m.distance_to(rally_point) > 5:
                    m.move(rally_point)

    async def control_vikings(self):
        vikings = self.units(UnitTypeId.VIKINGFIGHTER)
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
            marines = self.units(UnitTypeId.MARINE)
            for v in vikings:
                if v.tag in self.units_took_damage:
                    v.move(v.position.towards(self.start_location, 5))
                elif marines:
                    target = marines.closest_to(v)
                    if (target.distance_to(v)) > 3:
                        v.move(v.position.towards(target, 2))

    async def control_medivacs(self):
        medivacs = self.units(UnitTypeId.MEDIVAC)
        if medivacs:
            marines = self.units(UnitTypeId.MARINE)
            injured_marines = marines.filter(lambda i: i.health < i.health_max)
            if injured_marines:
                for m in medivacs:
                    target = injured_marines.closest_to(m)
                    if (target.distance_to(m)) > 3:
                        m.move(m.position.towards(target, 2))
            elif marines:
                for m in medivacs:
                    target = marines.closest_to(m)
                    if (target.distance_to(m)) > 3:
                        m.move(m.position.towards(target, 2))
            else:
                for m in medivacs:
                    if m.tag in self.units_took_damage:
                        m.move(m.position.towards(self.start_location, 5))

    async def production(self):
        if self.supply_left > 0:
            idle_ccs = self.townhalls.idle
            if idle_ccs and self.workers.amount < 90:
                idle_ccs.random.train(UnitTypeId.SCV, can_afford_check=True)

            marines = self.units(UnitTypeId.MARINE)
            idle_starports = self.structures(UnitTypeId.STARPORT).idle
            if idle_starports:
                if self.units(UnitTypeId.MEDIVAC).amount < marines.amount / 8:
                    idle_starports.random.train(UnitTypeId.MEDIVAC, can_afford_check=True)
                elif self.units(UnitTypeId.VIKINGFIGHTER).amount < 10:
                    idle_starports.random.train(UnitTypeId.VIKINGFIGHTER, can_afford_check=True)

            idle_barracks = self.structures(UnitTypeId.BARRACKS).idle
            if idle_barracks and self.units(UnitTypeId.MARINE).amount < 90:
                idle_barracks.random.train(UnitTypeId.MARINE, can_afford_check=True)

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float):
        self.units_took_damage.add(unit.tag)

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL1:
            self.inf_weapons = 1
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL1:
            self.inf_armor = 1
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL2:
            self.inf_weapons = 2
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL2:
            self.inf_armor = 2
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL3:
            self.inf_weapons = 3
        if upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL3:
            self.inf_armor = 3

    async def on_start(self):
        self.main_target = self.enemy_start_locations[0]

    async def on_step(self, iteration: int):
        await super().on_step(iteration)

        if self.state.game_loop % 5 == 0:
            await self.update_depots()
            await self.build_depots()
            await self.distribute_workers()
            await self.build_barracks()
            await self.build_starports()
            await self.build_first_engineering_bay()
            await self.build_refineries()
            await self.build_turrets()
            await self.build_upgrades()
            await self.build_expansions()
            await self.build_planetary_fortress()
        await self.control_marines()
        await self.control_vikings()
        await self.control_medivacs()

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

        await self.production()

        self.units_took_damage.clear()
