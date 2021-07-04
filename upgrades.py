from sc2.ids.upgrade_id import UpgradeId


class Upgrades:

    inf_weapons: int = 0
    inf_armor: int = 0
    vehicle_weapons: int = 0
    vehicle_armor: int = 0

    def track(self, upgrade: UpgradeId):
        if upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL1:
            self.inf_weapons = 1
        elif upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL2:
            self.inf_weapons = 2
        elif upgrade == UpgradeId.TERRANINFANTRYWEAPONSLEVEL3:
            self.inf_weapons = 3
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL1:
            self.inf_armor = 1
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL2:
            self.inf_armor = 2
        elif upgrade == UpgradeId.TERRANINFANTRYARMORSLEVEL3:
            self.inf_armor = 3
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL1:
            self.vehicle_weapons = 1
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL2:
            self.vehicle_weapons = 2
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPWEAPONSLEVEL3:
            self.vehicle_weapons = 3
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1:
            self.vehicle_armor = 1
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2:
            self.vehicle_armor = 2
        elif upgrade == UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3:
            self.vehicle_armor = 3
