from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

from spin_bot import SpinBot

run_game(
    maps.get("AcropolisLE"),
    [Bot(Race.Terran, SpinBot()), Computer(Race.Zerg, Difficulty.Hard)],
    realtime=False
)
