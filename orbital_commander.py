from sc2 import AbilityId, UnitTypeId
from sc2.unit import Unit
from sc2.units import Units

from spin_bot_base import SpinBotBase


class OrbitalCommander:
    bot: SpinBotBase
    call_down = AbilityId.CALLDOWNMULE_CALLDOWNMULE

    def __init__(self, bot: SpinBotBase):
        super().__init__()
        self.bot = bot

    async def update(self):
        if self.bot.state.game_loop % 10 != 0:
            return
        await self._mule()

    async def _mule(self):
        orbitals = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready
        if orbitals:
            can_mule = await self._can_mule(orbitals)
            if can_mule:
                muleable = self._muleable_minerals()
                if muleable:
                    can_mule.random(self.call_down, muleable.random)

    async def _can_mule(self, orbitals: Units) -> Units:
        can_cast = [o for o in orbitals if await self._can_cast_mule(o)]
        return Units(can_cast, self.bot)

    async def _can_cast_mule(self, unit: Unit):
        return await self.bot.can_cast(unit, self.call_down, only_check_energy_and_cooldown=True)

    def _muleable_minerals(self) -> Units:
        ready_bases = self.bot.townhalls.ready
        if not ready_bases:
            return Units([], self.bot)
        else:
            return self.bot.mineral_field.in_distance_of_group(ready_bases, 9)