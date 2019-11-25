"""MPF handlers for upgrade eligibility."""

import logging
import random
from mpf.core.custom_code import CustomCode


class Upgrade:
    def __init__(self, name, description, mineral, cost):
        self.name = name
        self.description = description
        self.mineral = mineral
        self.cost = cost

    def is_affordable(self, player):
        return player["mineral_{}".format(self.mineral)] >= self.cost


class ResearchUpgrade(Upgrade):
    def __init__(self, name, description, perk, amount, mineral, cost):
        super().__init__(name, description, mineral, cost)
        self.perk = perk
        self.amount = amount

    def __repr__(self):
        return "<ArmorUpgrade.{}:{} '{}''>".format(self.perk, self.amount, self.name)

    def to_kwargs(self, player, next_level=False):
        level = player["research_{}_level".format(self.perk)] + (1 if next_level else 0)
        return {
            "title": self.name,
            "full_title": "{} {}".format(self.name, level),
            "description": self.description.format(int(self.amount * 100 * level)),
            "mineral": self.mineral,
            "cost": self.cost,
            "level": level
        }

    def check(self, player):
        next_level = player["research_{}_level".format(self.perk)] + 1
        # If the player already purchased this research at this level, no good
        if player["level"] == player["research_{}_last_player_level".format(self.perk)]:
            return False
        # If the player's level is too low to purchase the next level of research
        if (next_level * 2) - 1 > player["level"]:
            return False
        # Can the player afford it?
        return player["mineral_{}".format(self.mineral)] >= self.cost

    def award(self, player):
        # Increase the player's perk by the research perk amount
        player["research_{}_perk".format(self.perk)] += self.amount
        # Track the level of this research project
        player["research_{}_level".format(self.perk)] += 1
        # Track the level at which the player purchased this research
        player["research_{}_last_player_level".format(self.perk)] = player["level"]
        # And of course, pay for it
        player["mineral_{}".format(self.mineral)] -= self.cost


RESEARCH = {
    "tick_interval": ResearchUpgrade("Heavy Skin Weave", "Extend timers by {}%",
                                     "tick_interval", 0.05, "iridium", 30000),
    "mineral_rate": ResearchUpgrade("Argus Scanner Array", "Earn {}% more minerals",
                                    "mineral_rate", 0.1, "iridium", 90000),
    "ball_save_period": ResearchUpgrade("Damage Protection", "Increase ball saves by {}%",
                                        "ball_save_period", 0.1, "palladium", 30000),
    "random_ball_save": ResearchUpgrade("Redundant Field Generator", "{}% chance of ball save on drain",
                                        "random_ball_save", 0.03, "palladium", 60000),
    "award_medigel": ResearchUpgrade("Medigel Capacity", "Earn medigel {}% faster",
                                     "award_medigel", 0.05, "platinum", 25000),
    "double_medigel": ResearchUpgrade("Trauma Module", "{}% chance of double medigel",
                                      "double_medigel", 0.1, "platinum", 50000),
    "power_tick_interval": ResearchUpgrade("Biotic Duration", "Increase power duration by {}%",
                                           "power_tick_interval", 0.1, "eezo", 2500),
    "cooldown_rate": ResearchUpgrade("Biotic Cooldown", "Accelerate power cooldown by {}%",
                                     "cooldown_rate", 0.1, "eezo", 7500),
}


class Research(CustomCode):
    def on_load(self):
        self.log = logging.getLogger("Research")
        self.log.setLevel(1)
        self.log.debug("Research custom code started!")
        self.machine.events.add_handler("check_research", self._on_check)
        self.machine.events.add_handler("start_mode_store", self._on_store)
        self.machine.events.add_handler("research_purchased", self._on_purchase)

    def get_purchaseable_options(self):
        options = []
        player = self.machine.game.player
        for key, upgrade in RESEARCH.items():
            if upgrade.check(player):
                options.append(key)
        return options

    def _on_check(self, **kwargs):
        success = len(self.get_purchaseable_options()) > 0
        self.machine.events.post("research_check_{}".format("passed" if success else "failed"))

    def _on_purchase(self, **kwargs):
        upgrade = RESEARCH[kwargs["selection"]]
        player = self.machine.game.player
        if not upgrade.check(player):
            self.log.warning("Player attempted to purchase upgrade {} but check failed!".format(upgrade))
            return
        upgrade.award(player)
        self.machine.events.post("upgrade_awarded", **upgrade.to_kwargs(player))

    def _on_store(self, **kwargs):
        options = self.get_purchaseable_options()
        result = random.sample(options, k=min(len(options), 3))
        self.machine.game.player["store_options"] = "|".join(result)
        self.machine.events.post("research_options", options=result)
