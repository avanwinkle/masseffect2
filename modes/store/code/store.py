
# ** RESEARCH UPGRADES ** GOING TO TRY THIS
# These upgrades are aquired from the store and provide
# passive benefits during gameplay. They are stackable
# and persist throughout the player's career.
#
# When the player enters a store, one of the four elements is chosen at random
# and the two options for that element are available to purchase (or the player
# can decline and purchase nothing).
#
# For the 1-6 minor upgrades, the player can purchase up to 1/2 of their current
# level and can purchase the same minor upgrade once per level. If the player
# cannot afford or has already purchased the minor upgrade, it will be grayed
# out. If they cannot afford the major upgrade, it will be grayed out.
#
# Random selection of the store to open will be weighed against what's
# available. Minerals with both grayed out will not be chosen. Minerals with one
# available have 1/2 the chance of those with two. If there are no purchase
# options, the store will not be enabled and the player can re-light the store
# to try again.
#
#  - Shield upgrades
#      - Damage protection 1-6: increase ball save times [PALLADIUM]
#      - Redundant field generator: random chance for a ball save on drain [PALLADIUM]
#  - Cybernetic upgrades:
#      - Heavy Skin weave 1-6: increase points and multipliers [IRIDIUM]
#      - Argus Scanner Array: accelerate awarding of minerals [IRIDIUM]
#  - Medigel upgrades
#     - Medigel capacity 1-6: award medigel when lower lanes completed [PLATINUM]
#     - Trauma module: light both outlanes for medigel save [PLATINUM]
#  - Bio-amp / Omni-tool upgrades:
#      - Biotic duration: 1-6 increase timer durations [EEZO]
#      - Tech duration: 1-6 increase timer durations [EEZO]
#      - Biotic cooldown: accelerate awarding of powers [EEZO]
#      - Tech cooldown: accelerate awarding of powers [EEZO]

import logging
from mpf.core.mode import Mode

PERKS = ["award_medigel_bool", "double_medigel_bool", "ball_save_period",
         "cooldown_rate", "mineral_rate", "point_multiplier", "tick_interval"]
POWERS = ["adrenaline", "armor", "cloak", "charge", "drone", "singularity"]


class Upgrade:
    def __init__(self, name, description, mineral, cost):
        self.name = name
        self.description = description
        self.mineral = mineral
        self.cost = cost

    def is_affordable(self, player):
        return player["mineral_{}".format(self.mineral)] >= self.cost


class ArmorUpgrade(Upgrade):
    def __init__(self, name, description, perk, amount, mineral, cost):
        super().__init__(name, description, mineral, cost)
        self.perk = perk
        self.amount = amount

    def __repr__(self):
        return "<ArmorUpgrade.{}:{} '{}''>".format(self.perk, self.amount, self.name)

    def activate(self, player):
        for perk in PERKS:
            value = 1
            if self.name == perk:
                value = self.amount
            elif perk[-5:] == "_bool":
                value = 0
            player["perk_{}".format(perk)] = value


class BonusPower(Upgrade):
    def __init__(self, name, description, power, mineral, cost):
        super().__init__(name, description, mineral, cost)
        self.power = power

    def __repr__(self):
        return "<BonusPower.{}>".format(self.name)

    def activate(self, player):
        player["power"] = self.power
        player["power_is_bonus"] = 1


ARMOR_UPGRADES = [
    ArmorUpgrade("Stimulator Conduits", "Slow down timers by 10%",
                 "tick_interval", 1.1, "iridium", 30000),
    ArmorUpgrade("Capacitor Chestplate", "Complete lower lanes to light medigel",
                 "award_medigel_bool", 1, "platinum", 60000),
    ArmorUpgrade("Life Support Webbing", "Medigel lights on both outlanes",
                 "double_medigel_bool", 1, "platinum", 30000),
    ArmorUpgrade("N7 Shoulder Guards", "Increase points by 3%",
                 "point_multiplier", 1.03, "iridium", 50000),
    ArmorUpgrade("Recon Hood", "Increase points by 5%",
                 "point_multiplier", 1.05, "iridium", 75000),
    ArmorUpgrade("N7 Greaves", "Increase ball save duration by 10%",
                 "ball_save_period", 1.1, "palladium", 30000),
    ArmorUpgrade("Heavy Damping Gauntlets", "Increase ball save duration by 20%",
                 "ball_save_period", 1.2, "palladium", 60000),
    ArmorUpgrade("Archon Visor", "Reduce power cooldown by 5%",
                 "cooldown_rate", 0.95, "eezo", 15000),
    ArmorUpgrade("Death Mask", "Increase mineral collection by 10%",
                 "mineral_rate", 0.9, "iridium", 90000),
]

BONUS_POWERS = [
    BonusPower("Adrenaline Rush", "Stop all timers for 15s", "adrenaline", "eezo", 4000),
    BonusPower("Tech Armor", "Enable 10s ball save", "armor", "eezo", 4000),
    BonusPower("Tactical Cloak", "Use flippers to rotate lit shots", "cloak", "eezo", 8000),
    BonusPower("Biotic Charge", "Hit a lit shot at random", "charge", "eezo", 8000),
    BonusPower("Combat Drone", "Add a ball", "drone", "eezo", 6000),
    BonusPower("Singularity", "Target hits count as lane hits", "singularity", "eezo", 10000),
]


class Store(Mode):
    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("Store")
        self.log.setLevel(10)
        self.settings = config.get("mode_settings")

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        player = self.machine.game.player
        self.log.debug("Store is starting")
        # Look for items to purchase
        available_armors = [armor for armor in ARMOR_UPGRADES if armor.is_affordable(player)]
        available_powers = [power for power in BONUS_POWERS if power.is_affordable(player)]
        self.log.debug(" - Armors available: {}".format(available_armors))
        self.log.debug(" - Powers available: {}".format(available_powers))


# ** ARMOR UPGRADES ** NOT GOING TO TRY YET
# These upgrades are aquired from the store and provide a
# passive benefit during gameplay. Only one upgrade can be
# equipped at a time, though previously-purchase upgrades can
# be re-equipped at no cost. These upgrades provide more powerful
# bonuses than the weapon upgrades. They do *not* persist
# across games.
#
#
#  Armor slots:
#    - Stimulator conduits:     increase timer durations      (increase storm speed 10%)
#    - Capacitor chestplate:    award medigel on lower lanes  (reduce shield delay 10%)
#    - Life support webbing:    light medigel on both lanes   (increase health 10%)
#    - N7 shoulder guards:      increase points               (increase damage 3%)
#    - Recon hood:              increase points               (increase damage 5%)
#    - N7 greaves:              increase ball save times      (increase shields 3%)
#    - Heavy damping gauntlets: increase ball save times      (increase shields 5%)
#    - Archon visor:            accelerate awarding of powers (reduce cooldown 5%)
#    - Death mask:              accelerate mineral collection (increase negotiation 10%)
#
