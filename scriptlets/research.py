"""MPF handlers for upgrade eligibility."""

import logging
import math
import random
from mpf.core.custom_code import CustomCode

RESEARCH = {
  "iridium": {
    "minor": ResearchUpgrade("Heavy Skin Weave",
                             "tick_interval", 0.05, "iridium", 30000),
    "major": ResearchUpgrade("Argus Scanner Array",
                             "mineral_rate", 0.1, "iridium", 90000),
  },
  "palladium": {
    "minor": ResearchUpgrade("Damage Protection",
                             "ball_save_period", 0.1, "palladium", 30000),
    "major": ResearchUpgrade("Redundant Field Generator",
                             "random_ball_save", 0.03, "palladium", 60000),
  },
  "platinum": {
    "minor": ResearchUpgrade("Medigel Capacity",
                             "award_medigel", 0.05, "platinum", 25000),
    "major": ResearchUpgrade("Trauma Module",
                             "double_medigel", 0.1, "platinum", 50000),
  },
  "eezo": {
    "minor": ResearchUpgrade("Biotic Duration",
                             "power_tick_interval", 0.1, "eezo", 2500),
    "major": ResearchUpgrade("Biotic Cooldown",
                             "cooldown_rate", 0.1, "eezo", 7500),
  }
}



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

    def check(self, player):
      # If the player already purchased this research at this level, no good
      if player["level"] == player["research_{}_last_player_level".format(self.perk)]:
        return False
      # If the player's level is too low to purchase the next level of research
      if math.ceil(player["level"] / 2) >= player["research_{}_level".format(self.perk)]:
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


class BonusPower(Upgrade):
    def __init__(self, name, description, power, mineral, cost):
        super().__init__(name, description, mineral, cost)
        self.power = power

    def __repr__(self):
        return "<BonusPower.{}>".format(self.name)

    def activate(self, player):
        player["power"] = self.power
        player["power_is_bonus"] = 1

BONUS_POWERS = [
    BonusPower("Adrenaline Rush", "Stop all timers for 15s", "adrenaline", "eezo", 4000),
    BonusPower("Tech Armor", "Enable 10s ball save", "armor", "eezo", 4000),
    BonusPower("Tactical Cloak", "Use flippers to rotate lit shots", "cloak", "eezo", 8000),
    BonusPower("Biotic Charge", "Hit a lit shot at random", "charge", "eezo", 8000),
    BonusPower("Combat Drone", "Add a ball", "drone", "eezo", 6000),
    BonusPower("Singularity", "Target hits count as lane hits", "singularity", "eezo", 10000),
]


class Research(CustomCode):
  def on_load(self):
    self.machine.events.add_handler("check_research", self._on_check)

  def _on_check(self, **kwargs):
    minerals = []
    player = self.machine.game.player
    for mineral, upgrades in RESEARCH.items():
      # One weight for each
      for upgrade in upgrades.values():
        if upgrade.check(player):
          minerals.append(mineral)

    self.machine.events.post("research_check_{}".format("passed" if len(minerals) > 0 else "failed"))
