import random
from typing import List, Set, Callable, Union

from sc2 import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from spin_bot_base import SpinBotBase


class CombatMicro:
    bot: SpinBotBase
    hard_counter_types: Set[UnitTypeId] = {
        UnitTypeId.COLOSSUS,
        UnitTypeId.BATTLECRUISER,
        UnitTypeId.MEDIVAC,
        UnitTypeId.BROODLORD
    }
    bio_priority_targets: Set[UnitTypeId] = {
        UnitTypeId.BANELING,
        UnitTypeId.ARCHON
    }
    main_target: Point2 = Point2()
    enough_troops: bool = False

    def __init__(self, bot: SpinBotBase):
        super().__init__()
        self.bot = bot

    async def on_start(self):
        self.main_target = self.bot.enemy_start_locations[0]

    async def update(self):
        await self._control_bio()
        await self._control_medivacs()
        await self._control_vikings()

    async def _control_bio(self):
        troops = self.bot.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
        if troops:
            rally_point: Point2 = self.bot.center(troops).position  # type: ignore
            enemy_units = self.bot.enemy_units.visible
            threats = enemy_units - enemy_units({
                UnitTypeId.OVERLORD, UnitTypeId.OVERSEER, UnitTypeId.LARVA, UnitTypeId.EGG
            })
            for t in threats:
                if self.bot.structures.closest_distance_to(t) < 15:
                    for m in troops:
                        self._attack_or_rally(m, threats, rally_point)
                    return

            if not self.enough_troops:
                self.enough_troops = troops.amount >= self.bot.game_minutes * 2.5 or troops.amount >= 40
            else:
                self.enough_troops = troops.amount >= self.bot.game_minutes * 2 or troops.amount >= 30
            enemies = (
                    (enemy_units - enemy_units({UnitTypeId.LARVA, UnitTypeId.EGG})) +
                    self.bot.enemy_structures.visible
            )
            if self.enough_troops and enemies:
                for m in troops:
                    self._attack_or_rally(m, enemies, rally_point)
                return

            marines_at_enemy_base = troops.closer_than(10, self.main_target)
            if not enemies and marines_at_enemy_base.amount > 20:
                self.main_target = random.choice(self._empty_expansions())

            if self.enough_troops:
                for m in troops:
                    if m.distance_to(self.main_target) > 5:
                        m.attack(self.main_target)
                return

            for m in troops:
                if m.distance_to(rally_point) > 5:
                    self._fighting_move(m, enemies, rally_point)

    def _fighting_move(self, unit: Unit, targets: Units, rally: Point2):
        if not unit.weapon_ready or not targets:
            self._move_near(unit, rally)
            return
        attackable_enemies = CombatMicro._attackable_enemies(unit, targets)
        best = CombatMicro._best_target(unit, attackable_enemies, only_in_range=True)
        if best:
            unit.attack(best)
            return
        self._move_near(unit, rally)

    def _attack_or_rally(self, unit: Unit, targets: Units, rally: Point2):
        attackable_enemies = CombatMicro._attackable_enemies(unit, targets)
        priority_targets = self._priority_targets(targets)
        if priority_targets:
            best = CombatMicro._best_target(unit, priority_targets)
        else:
            best = CombatMicro._best_target(unit, attackable_enemies)
        if best:
            self.bot.client.debug_line_out(unit, best)
            closest_distance = unit.distance_to(best) - (unit.radius + best.radius)
            if (not unit.weapon_ready) and closest_distance > 2:
                distance = min(closest_distance, unit.distance_to_weapon_ready)
                unit.move(unit.position.towards(best, distance))
            else:
                unit.attack(best)
            return
        self._move_near(unit, rally)

    def _priority_targets(self, targets: Units) -> Units:
        return targets.subgroup(
            [t for t in targets if (
                    t.type_id in self.bio_priority_targets or
                    (t.type_id == UnitTypeId.SENTRY and BuffId.GUARDIANSHIELD in t.buffs)
            )]
        )

    def _move_near(self, unit: Unit, rally: Point2):
        if unit.distance_to(rally) > 5:
            self.bot.client.debug_line_out(unit, rally.to3)
            unit.move(rally)

    @staticmethod
    def _attackable_enemies(unit: Unit, targets: Units):
        return targets.subgroup([
            t for t in targets if (
                    unit.can_attack_both or
                    (not t.is_flying and unit.can_attack_ground) or
                    (t.is_flying and unit.can_attack_air)
            )
        ])

    @staticmethod
    def _best_target(unit: Unit, targets: Units, only_in_range: bool = False) -> Union[Unit, None]:
        if not targets:
            return None
        in_range = targets.subgroup(
            [t for t in targets if unit.target_in_range(t)]
        )
        if in_range:
            in_range.sort(key=CombatMicro._range_sorter(unit))
            in_range.sort(key=CombatMicro._injured_sorter())
            in_range.sort(key=CombatMicro._damage_output_sorter(unit))
            return in_range.first
        if only_in_range:
            return None
        return targets.closest_to(unit)

    @staticmethod
    def _range_sorter(unit: Unit) -> Callable[[Unit], float]:
        def sort_key(t: Unit) -> float:
            return unit.distance_to(t)

        return sort_key

    @staticmethod
    def _damage_output_sorter(unit: Unit) -> Callable[[Unit], float]:
        def sort_key(t: Unit) -> float:
            return unit.calculate_damage_vs_target(t)[0]

        return sort_key

    @staticmethod
    def _injured_sorter() -> Callable[[Unit], float]:
        def sort_key(t: Unit) -> float:
            return t.health_percentage

        return sort_key

    async def _control_vikings(self):
        vikings = self.bot.units(UnitTypeId.VIKINGFIGHTER)
        if vikings:
            main_targets = self.bot.enemy_units(self.hard_counter_types).visible
            if main_targets:
                for v in vikings:
                    v.attack(main_targets.closest_to(v))
                return
            secondary_targets = self.bot.enemy_units.visible.flying
            if secondary_targets:
                for v in vikings:
                    v.attack(secondary_targets.closest_to(v))
                return
            troops = self.bot.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
            for v in vikings:
                if v.tag in self.bot.units_took_damage:
                    v.move(v.position.towards(self.bot.start_location, 5))
                elif troops:
                    target = troops.closest_to(v)
                    if (target.distance_to(v)) > 3:
                        v.move(v.position.towards(target, 2))

    async def _control_medivacs(self):
        medivacs = self.bot.units(UnitTypeId.MEDIVAC)
        if medivacs:
            troops = self.bot.units({UnitTypeId.MARINE, UnitTypeId.MARAUDER})
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
                    if m.tag in self.bot.units_took_damage:
                        m.move(m.position.towards(self.bot.start_location, 5))

    def _empty_expansions(self) -> List[Point2]:
        expansions: List[Point2] = self.bot.expansion_locations_list  # type: ignore
        return [
            x for x in expansions if self.bot.townhalls.closest_distance_to(x) > 5
        ]
