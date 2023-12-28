"""MPF handlers for upgrade eligibility."""

import logging
import random
from mpf.core.custom_code import CustomCode

MAX_ITEMS = 4
UPGRADES = {
    "tick_interval": {
        "name": "Heavy Skin Weave",
        "description": "Extend all mode timers\nby {}%",
        "amount": 0.05,
        "mineral": "iridium",
        "cost": 30000,
        "product": "Lattice Shunting",
        "image": "lattice",
    },
    "mineral_rate": {
        "name": "Advanced Mineral Scanner",
        "description": "Earn {}% more minerals\nwhen scanning",
        "amount": 0.1,
        "mineral": "iridium",
        "cost": 90000,
        "product": "Argus Scanner Array",
        "image": "scanner"
    },
    "ball_save_period": {
        "name": "Damage Protection",
        "description": "Increase all ball save\ndurations by {}%",
        "amount": 0.1,
        "mineral": "palladium",
        "cost": 30000,
        "product": "Ablative VI",
        "image": "armor_ablative",
    },
    "random_ball_save": {
        "name": "Redundant Field Generator",
        "description": "{}% chance of ball save\non drain (once per ball)",
        "amount": 0.03,
        "mineral": "palladium",
        "cost": 60000,
        "product": "Burst Regeneration",
        "image": "armor_burstshield",
    },
    "award_medigel": {
        "name": "Medigel Capacity",
        "description": "Earn medigel {}% faster\nwhen completing\nreputation lanes",
        "amount": 0.05,
        "mineral": "platinum",
        "cost": 25000,
        "product": "Microscanner",
        "image": "armor_microscanner",
    },
    "double_medigel": {
        "name": "Trauma Module",
        "description": "{}% chance that a levelup\nawards double medigel",
        "amount": 0.1,
        "mineral": "platinum",
        "cost": 50000,
        "product": "Medical VI",
        "image": "armor_trauma_module",
    },
    "power_tick_interval": {
        "name": "Biotic Duration",
        "description": "Increase power durations\nby {}%",
        "amount": 0.1,
        "mineral": "eezo",
        "cost": 2500,
        "product": "Neural Mask",
        "image": "biotics_neuralmask",
    },
    "cooldown_rate": {
        "name": "Biotic Cooldown",
        "description": "Accelerate power\ncooldown rate by {}%",
        "amount": 0.1,
        "mineral": "eezo",
        "cost": 7500,
        "product": "Smart Amplifier",
        "image": "biotics_hyperamp"
    },
}


def sort_keys_by_name(key):
    return UPGRADES[key]["name"]


class Upgrade:
    def __init__(self, name, description, mineral, cost):
        self.name = name
        self.description = description
        self.mineral = mineral
        self.cost = cost

    def is_affordable(self, player):
        return player["mineral_{}".format(self.mineral)] >= self.cost


class ResearchUpgrade(Upgrade):
    def __init__(self, name, description, perk, amount, mineral, cost, product, image):
        super().__init__(name, description, mineral, cost)
        self.perk = perk
        self.amount = amount
        self.product = product
        self.image = image

    def __repr__(self):
        return "<ArmorUpgrade.{}:{} '{}''>".format(self.perk, self.amount, self.name)

    def to_kwargs(self, player, next_level=False):
        level = player["research_{}_level".format(self.perk)] + (1 if next_level else 0)
        return {
            "title": self.name,
            "image": self.image,
            "full_title": "{} {}".format(self.name, level),
            "description": self.description.format(int(self.amount * 100 * level)),
            "mineral": self.mineral,
            "mineral_name": "Element Zero" if self.mineral == "eezo" else self.mineral,
            "player_mineral": player["mineral_{}".format(self.mineral)],
            "cost": self.cost,
            "level": level,
            "product": "{} {}/6".format(self.product, level),
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


RESEARCH = {key: ResearchUpgrade(perk=key, **value) for (key, value) in UPGRADES.items()}


class Research(CustomCode):
    def on_load(self):
        self.log = logging.getLogger("Research")
        self.log.setLevel(1)
        self.log.debug("Research custom code started!")
        self.machine.events.add_handler("check_research", self._on_check)
        self.machine.events.add_handler("start_mode_store", self._on_store)
        self.machine.events.add_handler("research_purchased", self._on_purchase)
        # On reputation lane completion, check for a medigel award
        self.machine.events.add_handler("check_award_medigel", self._check_award_medigel)
        # On levelup medigel award, check for one to go twice!
        self.machine.events.add_handler("check_double_medigel", self._check_double_medigel)
        # On drain, check for a random save
        self.machine.events.add_handler("ball_drain", self._check_random_ball_save)

        # Track handlers we create for the store, so we can release them
        self._store_handlers = []

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

    def _check_award_medigel(self, **kwargs):
        chance = self.machine.game.player["research_award_medigel_perk"] + \
            self.machine.game.player["reputation"]
        if chance > 0 and random.random() < chance:
            self.machine.events.post("award_medigel_success")

    def _check_double_medigel(self, **kwargs):
        chance = self.machine.game.player["research_double_medigel_perk"]
        if chance > 0 and random.random() < chance:
            self.machine.events.post("double_medigel_success")

    def _check_random_ball_save(self, balls: int, **kwargs):
        # If we drain during a ball search or tilt, there may not be a player
        if not self.machine.game or not self.machine.game.player:
            return
        chance = self.machine.game.player["research_random_ball_save_perk"]
        self.log.info("Checking random ball save with {}% chance".format(chance * 100))
        # Don't save if there are multiple balls in play (or none draining)
        if balls <= 0 or self.machine.game.balls_in_play > 1:
            return {}

        if chance > 0 and random.random() < chance:
            self.machine.events.post("random_ball_save_success")
            self.machine.ball_devices["playfield"].add_ball(balls=1, player_controlled=False)
            # This is a relay event. We can change 'balls' to prevent drain
            return {"balls": balls - 1}

    def _on_purchase(self, **kwargs):
        if kwargs["selection"] == "nothing":
            return
        upgrade = RESEARCH[kwargs["selection"]]
        player = self.machine.game.player
        if not upgrade.check(player):
            self.log.warning("Player attempted to purchase upgrade {} but check failed!".format(upgrade))
            return
        upgrade.award(player)
        self.machine.events.post("upgrade_awarded", **upgrade.to_kwargs(player))

    def _on_store(self, **kwargs):
        options = self.get_purchaseable_options()
        result = random.sample(options, k=min(len(options), MAX_ITEMS))
        # Sort by name
        result.sort(key=sort_keys_by_name)
        self.machine.game.player["store_options"] = "|".join(result)
        self.machine.events.post("research_options", options=result)

        # Create handlers for store events
        self._store_handlers.append(
            self.machine.events.add_handler("store_item_highlighted", self._on_store_item))

    def _on_store_item(self, **kwargs):
        if kwargs["item"] == "nothing":
            self.machine.events.post("clear_store_selection")
        else:
            upgrade = RESEARCH[kwargs["item"]]
            # Return all the kwargs we need for that item
            self.machine.events.post("update_store_selection",
                                     **upgrade.to_kwargs(self.machine.game.player, next_level=True))
