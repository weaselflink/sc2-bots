from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer

from spin_bot import SpinBot


def main():
    player_config = [
        Bot(Race.Terran, SpinBot()),
        Computer(Race.Protoss, Difficulty.Hard)
    ]
    run_game(
        maps.get("EphemeronLE"),
        player_config,
        realtime=False
    )


if __name__ == "__main__":
    main()
