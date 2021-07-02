import random
from math import floor
from typing import Union, Optional, List

from sc2.constants import *
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from spin_bot_base import SpinBotBase, OrbitalCommander


class SpinBot(SpinBotBase):

    build_units: bool = True
    main_target: Point2 = Point2()
    hard_counter_types: Set[UnitTypeId] = {UnitTypeId.COLOSSUS, UnitTypeId.BATTLECRUISER, UnitTypeId.MEDIVAC}
    units_took_damage: set[int] = set()
    need_air: bool = False
    orbital_commander: OrbitalCommander

    def __init__(self):
        super().__init__()
        self.orbital_commander = OrbitalCommander(self)

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
        depot_placement_positions = self.empty_ramp_corners()
        if self.supply_left < 2 and self.can_build_once(UnitTypeId.SUPPLYDEPOT):
            if depot_placement_positions:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions[0])
                return True
            else:
                await self.build(
                    UnitTypeId.SUPPLYDEPOT,
                    self.townhalls.first.position.towards(self.game_info.map_center, 8)
                )
                return True
        return False

    def empty_ramp_corners(self) -> List[Point2]:
        corners: Set[Point2] = self.main_base_ramp.corner_depots  # type: ignore
        return [
            p for p in corners if not self.has_building(p)
        ]

    async def build_barracks(self):
        racks = self.structures(UnitTypeId.BARRACKS)
        tech_labs = self.structures(UnitTypeId.BARRACKSTECHLAB)
        reactors = self.structures(UnitTypeId.BARRACKSREACTOR)
        if racks.amount > 1:
            racks_with_space = await self.barracks_missing_addons()
            if racks_with_space:
                if not tech_labs:
                    racks_with_space.random(AbilityId.BUILD_TECHLAB)
                elif reactors.amount * 3 < racks.amount:
                    racks_with_space.random(AbilityId.BUILD_REACTOR)
                elif tech_labs.amount * 3 < racks.amount:
                    racks_with_space.random(AbilityId.BUILD_TECHLAB)
        if self.can_build_once(UnitTypeId.BARRACKS) and racks.amount < self.townhalls.amount * 2 and racks.amount < 16:
            if racks.amount < 1:
                placement: Optional[Point2] = self.main_base_ramp.barracks_correct_placement  # type: ignore
                await self.build_single_barracks(placement, addon_place=False)
                return True
            elif racks.amount == 1:
                near = self.main_base.position.towards(self.game_info.map_center, 8)
                await self.build_single_barracks(near)
                return True
            elif (self.units(UnitTypeId.MARINE).amount < 40 and
                  self.minerals > 500 and
                  self.structures(UnitTypeId.ENGINEERINGBAY)):
                await self.build_single_barracks(self.structures(UnitTypeId.ENGINEERINGBAY).first)
                return True
        return False

    async def barracks_missing_addons(self) -> Units:
        return Units(
            [b for b in self.structures(UnitTypeId.BARRACKS) if await self.room_for_addon(b)],
            self
        )

    async def room_for_addon(self, unit: Unit) -> bool:
        return await self.can_place_single(UnitTypeId.SUPPLYDEPOT, unit.position.offset((2.5, -0.5)))

    async def build_single_barracks(
            self,
            near: Union[Unit, Point2],
            # TODO does not work with this set to True
            addon_place: bool = False
    ):
        if isinstance(near, Unit):
            near = near.position
        if isinstance(near, Point2):
            near = near.to2
        spot = await self.find_placement(
            UnitTypeId.BARRACKS,
            near,
            max_distance=20,
            placement_step=2,
            random_alternative=False,
            addon_place=addon_place
        )
        if spot:
            builder = self.select_build_worker(near)
            if builder:
                self.do(builder.build(UnitTypeId.BARRACKS, spot), subtract_cost=True, ignore_warning=True)

    async def build_starports(self):
        ebays = self.structures(UnitTypeId.ENGINEERINGBAY)
        starports = self.structures(UnitTypeId.STARPORT)
        if starports and starports.amount < 4 and starports.amount < self.townhalls.amount:
            wanted_starports = floor(self.game_minutes / 5)
            await self.fulfill_building_need(UnitTypeId.STARPORT, ebays.first, wanted_starports)

    async def build_upgrades(self):
        ebays = self.structures(UnitTypeId.ENGINEERINGBAY)
        armories = self.structures(UnitTypeId.ARMORY)
        factories = self.structures(UnitTypeId.FACTORY)
        tech_labs = self.structures(UnitTypeId.BARRACKSTECHLAB)
        if tech_labs.idle:
            idle_tech_lab = tech_labs.idle.random
            if await self.can_cast(idle_tech_lab, AbilityId.RESEARCH_COMBATSHIELD):
                idle_tech_lab(AbilityId.RESEARCH_COMBATSHIELD)
        if ebays:
            await self.fulfill_building_need(UnitTypeId.ENGINEERINGBAY, ebays.first, 2)
            await self.fulfill_building_need(UnitTypeId.FACTORY, ebays.first)
            if factories:
                await self.fulfill_building_need(UnitTypeId.ARMORY, ebays.first)
                await self.fulfill_building_need(UnitTypeId.STARPORT, ebays.first)
        if ebays.idle:
            an_ebay = ebays.idle.first
            if self.inf_weapons < 1 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
            elif self.inf_armor < 1 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
            elif self.inf_weapons < 2 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
            elif self.inf_armor < 2 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
            elif self.inf_weapons < 3 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            elif self.inf_armor < 3 and await self.can_cast(
                    an_ebay, AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3):
                an_ebay(AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3)
            elif self.inf_weapons == 3 and await self.can_cast(
                    an_ebay, AbilityId.RESEARCH_HISECAUTOTRACKING):
                an_ebay(AbilityId.RESEARCH_HISECAUTOTRACKING)
            elif self.inf_weapons == 3 and await self.can_cast(
                    an_ebay, AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE):
                an_ebay(AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE)
        if armories.idle and self.inf_weapons == 2 and self.inf_armor == 2:
            an_armory = armories.idle.first
            if self.vehicle_armor < 1 and await self.can_cast(
                    an_armory, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1):
                an_armory(AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1)
            elif self.vehicle_armor < 2 and await self.can_cast(
                    an_armory, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1):
                an_armory(AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1)
            elif self.vehicle_armor < 3 and await self.can_cast(
                    an_armory, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1):
                an_armory(AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1)

    async def build_first_engineering_bay(self):
        if self.townhalls and self.gas_buildings and self.structures(UnitTypeId.BARRACKS).amount > 1:
            near = self.main_base.position.towards(self.game_info.map_center, 8)
            await self.fulfill_building_need(UnitTypeId.ENGINEERINGBAY, near)

    async def build_expansions(self):
        if self.can_build_once(UnitTypeId.COMMANDCENTER):
            await self.expand_now()
            return True
        return False

    async def build_refineries(self):
        if self.townhalls.amount < 2:
            return False
        if self.vespene > 1000:
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

    async def upgrade_ccs(self):
        need_orbital = self.need_orbital()
        if need_orbital:
            need_orbital(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
            return True
        need_planetary = self.need_planetary()
        if need_planetary:
            need_planetary(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)
            return True
        return False

    def need_orbital(self) -> Union[Unit, None]:
        in_progress = self.already_pending(UnitTypeId.ORBITALCOMMAND)
        if self.townhalls and not in_progress:
            initial_cc = self.townhalls.closest_to(self.start_location)
            if (initial_cc and
                    initial_cc.type_id == UnitTypeId.COMMANDCENTER and
                    self.structures(UnitTypeId.BARRACKS).amount > 0 and
                    self.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                return initial_cc
        return None

    def need_planetary(self) -> Union[Unit, None]:
        if (self.townhalls.amount > 1 and
                self.townhalls(UnitTypeId.COMMANDCENTER).idle and
                self.structures(UnitTypeId.ENGINEERINGBAY) and
                self.can_afford(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)):
            return self.townhalls(UnitTypeId.COMMANDCENTER).idle.closest_to(self.main_base)
        return None

    async def control_bio(self):
        troops = self.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
        if troops:
            enemy_units = self.enemy_units.visible
            threats = enemy_units - enemy_units({
                UnitTypeId.OVERLORD, UnitTypeId.OVERSEER, UnitTypeId.LARVA, UnitTypeId.EGG
            })
            for t in threats:
                if self.structures.closest_distance_to(t) < 30:
                    for m in troops:
                        m.attack(threats.closest_to(m))
                    return

            enemies = (enemy_units - enemy_units({UnitTypeId.LARVA, UnitTypeId.EGG})) + self.enemy_structures.visible
            if troops.amount >= 40 and enemies:
                for m in troops:
                    m.attack(enemies.closest_to(m))
                    return

            marines_at_enemy_base = troops.closer_than(10, self.main_target)
            if not enemies and marines_at_enemy_base.amount > 20:
                self.main_target = random.choice(self.empty_expansions())

            if troops.amount >= self.game_minutes * 2.5 or troops.amount >= 40:
                for m in troops:
                    if m.distance_to(self.main_target) > 5:
                        m.attack(self.main_target)
                return

            rally_point = self.center(troops).position
            for m in troops:
                if m.distance_to(rally_point) > 5:
                    m.move(rally_point)

    def empty_expansions(self) -> List[Point2]:
        expansions: List[Point2] = self.expansion_locations_list  # type: ignore
        return [
            x for x in expansions if self.townhalls.closest_distance_to(x) > 5
        ]

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
            troops = self.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
            for v in vikings:
                if v.tag in self.units_took_damage:
                    v.move(v.position.towards(self.start_location, 5))
                elif troops:
                    target = troops.closest_to(v)
                    if (target.distance_to(v)) > 3:
                        v.move(v.position.towards(target, 2))

    async def control_medivacs(self):
        medivacs = self.units(UnitTypeId.MEDIVAC)
        if medivacs:
            troops = self.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
            injured_marines = troops.filter(lambda i: i.health < i.health_max)
            if injured_marines:
                for m in medivacs:
                    target = injured_marines.closest_to(m)
                    if (target.distance_to(m)) > 3:
                        m.move(m.position.towards(target, 2))
            elif troops:
                for m in medivacs:
                    target = troops.closest_to(m)
                    if (target.distance_to(m)) > 3:
                        m.move(m.position.towards(target, 2))
            else:
                for m in medivacs:
                    if m.tag in self.units_took_damage:
                        m.move(m.position.towards(self.start_location, 5))

    def check_for_air(self):
        flying_threats = self.enemy_units.flying.exclude_type({
            UnitTypeId.OVERLORD, UnitTypeId.OVERSEER, UnitTypeId.OBSERVER
        })
        ground_threats = self.enemy_units(UnitTypeId.COLOSSUS)
        if flying_threats or ground_threats:
            self.need_air = True

    async def production(self):
        if self.supply_left > 0:
            idle_ccs = self.townhalls.idle
            if idle_ccs and self.workers.amount < 90:
                idle_ccs.random.train(UnitTypeId.SCV, can_afford_check=True)

            if not self.build_units:
                return
            marines = self.units(UnitTypeId.MARINE)
            if self.units(UnitTypeId.MEDIVAC).amount < marines.amount / 8:
                self.train(UnitTypeId.MEDIVAC)
            elif self.need_air and self.units(UnitTypeId.VIKINGFIGHTER).amount < 10:
                self.train(UnitTypeId.VIKINGFIGHTER)

            marauders = self.units(UnitTypeId.MARAUDER)
            if marines.amount > 10 and marines.amount > marauders.amount * 3:
                self.train(UnitTypeId.MARAUDER)
            if marines.amount < 90:
                self.train(UnitTypeId.MARINE)

    async def repair_ccs(self):
        for cc in self.townhalls:
            if cc.health < cc.health_max:
                health_ratio = cc.health / cc.health_max
                if health_ratio > 0.8:
                    wanted = 4
                elif health_ratio > 0.5:
                    wanted = 8
                else:
                    wanted = 16
                repairing_workers = await self.scvs_repairing(cc)
                wanted = wanted - repairing_workers.amount
                if wanted > 0:
                    avail_workers = self.workers.filter(lambda w: not w.is_repairing)
                    near_workers = avail_workers.closest_n_units(cc, wanted)
                    for nw in near_workers:
                        nw.repair(cc)
                break

    async def scvs_repairing(self, target: Unit) -> Units:
        return Units(
            [w for w in self.workers if (
                    w.is_repairing and
                    w.orders and
                    w.orders[0].target == target.tag)],
            self
        )

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float):
        self.units_took_damage.add(unit.tag)

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        await super().on_upgrade_complete(upgrade)

    async def on_start(self):
        await super().on_start()

        self.main_target = self.enemy_start_locations[0]
        if not self.build_units:
            await self.chat_send("DEBUG MODE: not building units")

    async def on_step(self, iteration: int):
        await super().on_step(iteration)

        # self.client.debug_sphere_out(self.townhalls.first, 9)
        self.check_for_air()

        await self.build_barracks()
        if self.state.game_loop % 5 == 0:
            await self.update_depots()
            await self.build_depots()
            await self.distribute_workers()
            await self.build_starports()
            await self.build_first_engineering_bay()
            await self.build_refineries()
            await self.build_turrets()
            await self.build_upgrades()
            await self.build_expansions()
            await self.upgrade_ccs()
        await self.control_bio()
        await self.control_vikings()
        await self.control_medivacs()
        await self.repair_ccs()
        await self.production()
        await self.orbital_commander.command()

        self.units_took_damage.clear()
