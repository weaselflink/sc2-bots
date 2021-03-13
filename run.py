from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

from second import SecondBot

run_game(
    maps.get("AcropolisLE"),
    [Bot(Race.Terran, SecondBot()), Computer(Race.Random, Difficulty.Hard)],
    realtime=False
)
