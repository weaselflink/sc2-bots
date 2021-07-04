from math import floor
from typing import Union, Optional, List

from sc2.constants import *
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from combat_micro import CombatMicro
from spin_bot_base import SpinBotBase
from orbital_commander import OrbitalCommander


class SpinBot(SpinBotBase):

    build_units: bool = True
    need_air: bool = False
    orbital_commander: OrbitalCommander
    combat_micro: CombatMicro

    def __init__(self):
        super().__init__()
        self.orbital_commander = OrbitalCommander(self)
        self.combat_micro = CombatMicro(self)

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
        depots = self.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})
        can_build = self.can_build_once(UnitTypeId.SUPPLYDEPOT)
        if not can_build:
            return False
        if not depots:
            await self.build_depot()
            return True
        if self.supply_cap < 30 and self.supply_left < 2:
            await self.build_depot()
            return True
        if self.supply_cap >= 30 and self.supply_left < 4:
            await self.build_depot()
            return True
        return False

    async def build_depot(self):
        depot_placement_positions = self.empty_ramp_corners()
        if depot_placement_positions:
            await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions[0])
        else:
            await self.build(
                UnitTypeId.SUPPLYDEPOT,
                self.townhalls.first.position.towards(self.game_info.map_center, 8)
            )

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
        barracks = self.structures(UnitTypeId.BARRACKS)
        return barracks.subgroup(
            [b for b in self.structures(UnitTypeId.BARRACKS) if await self.room_for_addon(b)]
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
        needs_orbital_upgrade = await self.need_orbital()
        if needs_orbital_upgrade:
            needs_orbital_upgrade(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
            return True
        needs_planetary_upgrade = await self.need_planetary()
        if needs_planetary_upgrade:
            needs_planetary_upgrade(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)
            return True
        return False

    async def need_orbital(self) -> Union[Unit, None]:
        in_progress = self.already_pending(UnitTypeId.ORBITALCOMMAND)
        if self.townhalls and not in_progress:
            initial_cc = self.townhalls.closest_to(self.start_location)
            if (initial_cc and
                    await self.can_cast(
                        initial_cc,
                        AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
                    )):
                return initial_cc
        return None

    async def need_planetary(self) -> Union[Unit, None]:
        needing = self.townhalls.idle.subgroup(
            [t for t in self.townhalls.idle if (
                    t.distance_to(self.start_location) > 9 and
                    await self.can_cast(t, AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)
            )]
        )
        if needing:
            return needing.first
        return None

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
            if marines.amount >= 4 and marines.amount > marauders.amount * 2:
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
        return self.workers.subgroup(
            [w for w in self.workers if (
                    w.is_repairing and
                    w.orders and
                    w.orders[0].target == target.tag)]
        )

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        await super().on_upgrade_complete(upgrade)

    async def on_start(self):
        await super().on_start()
        await self.combat_micro.on_start()

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
        await self.combat_micro.update()
        await self.repair_ccs()
        await self.upgrade_ccs()
        await self.production()
        await self.orbital_commander.update()

        self.units_took_damage.clear()
