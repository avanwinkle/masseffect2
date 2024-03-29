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
        "cost": 60000,
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
    # TODO: Disabled until I figure out how to manage a ball save after drain
    # "random_ball_save": {
    #     "name": "Redundant Field Generator",
    #     "description": "{}% chance of ball save\non drain (once per ball)",
    #     "amount": 0.05,
    #     "mineral": "palladium",
    #     "cost": 60000,
    #     "product": "Burst Regeneration",
    #     "image": "armor_burstshield",
    # },
    "award_medigel": {
        "name": "Medigel Capacity",
        "description" :"Extra {}% chance of earning\nmedigel when completing\nreputation lanes",
        "description": "Earn medigel {}% faster\nwhen completing\nreputation lanes",
        "amount": 0.05,
        "mineral": "platinum",
        "cost": 30000,
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
        "cost": 3000,
        "product": "Neural Mask",
        "image": "biotics_neuralmask",
    },
    "cooldown_rate": {
        "name": "Biotic Cooldown",
        "description": "Accelerate power\ncooldown rate by {}%",
        "amount": 0.1,
        "mineral": "eezo",
        "cost": 6000,
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
        self._cost = cost

    def get_cost(self, player):
        # The cost goes up by 20% each time, rounded to 100
        return int((self._cost * (1 + 0.2 * player[f"research_{self.perk}_level"])) // 100 * 100)


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
        # A player can only purchase an upgrade once per level
        level = player["research_{}_level".format(self.perk)] + (1 if next_level else 0)
        next_amount = self.amount * level
        return {
            "title": self.name,
            "image": self.image,
            "full_title": "{} {}".format(self.name, level),
            "description": self.description.format(int(next_amount * 100)),
            "mineral": self.mineral,
            "mineral_name": "Element Zero" if self.mineral == "eezo" else self.mineral,
            "player_mineral": player["mineral_{}".format(self.mineral)],
            "cost": self.get_cost(player),
            "level": level,
            "product": "{} {}/6".format(self.product, level),
        }

    def check(self, player):
        next_level = player[f"research_{self.perk}_level"] + 1
        # Maximum of six levels per upgrade
        if next_level > 6:
            return False
        # If the player already purchased this research at this level, no good
        if player["level"] == player[f"research_{self.perk}_last_player_level"]:
            return False
        # If the player's level is too low to purchase the next level of research
        # (e.g. must be level 6 to purchase level 3 upgrades)
        if (next_level * 2) - 1 > player["level"]:
            return False
        # Can the player afford it?
        cost = self.get_cost(player)
        print(f"Calculated cost of {self.perk} (level {next_level}) at {cost}")
        return player["mineral_{}".format(self.mineral)] >= cost

    def award(self, player):
        # Pay for it first, before the level (and price) goes up
        player["mineral_{}".format(self.mineral)] -= self.get_cost(player)
        # Increase the player's perk by the research perk amount
        player["research_{}_perk".format(self.perk)] += self.amount
        # Track the level of this research project
        player["research_{}_level".format(self.perk)] += 1
        # Track the level at which the player purchased this research
        player["research_{}_last_player_level".format(self.perk)] = player["level"]


RESEARCH = {key: ResearchUpgrade(perk=key, **value) for (key, value) in UPGRADES.items()}


class Research(CustomCode):
    def on_load(self):
        self.log = logging.getLogger("Research")
        self.log.setLevel(30)  # TODO: Use LogMixin
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
        # Track handlers we create for the store
        self.machine.events.add_handler("store_item_highlighted", self._on_store_item)

    def get_purchaseable_options(self):
        options = []
        player = self.machine.game.player
        for key, upgrade in RESEARCH.items():
            if upgrade.check(player):
                options.append(key)
        return options

    def _on_check(self, **kwargs):
        del kwargs
        success = len(self.get_purchaseable_options()) > 0
        self.machine.events.post("research_check_{}".format("passed" if success else "failed"))

    def _check_award_medigel(self, **kwargs):
        del kwargs
        # Player's "reputation" is an int grown by lane completions and N7 assignments.
        # Reputation is a 1% chance for award medigel, multiplied by the perk
        # But not if the player already has medigel
        if self.machine.game.player["medigel"]:
            return
        chance = (self.machine.game.player["reputation"] *
            (1 + self.machine.game.player["research_award_medigel_perk"])) / 100
        self.info_log("Checking award medigel with %s reputation and %s perk, total chance is %s",
                      self.machine.game.player["reputation"],
                      self.machine.game.player["research_award_medigel_perk"],
                      chance)
        if chance > 0 and random.random() < chance:
            self.machine.events.post("award_medigel_success")

    def _check_double_medigel(self, **kwargs):
        del kwargs
        chance = self.machine.game.player["research_double_medigel_perk"]
        if chance > 0 and random.random() < chance:
            self.machine.events.post("double_medigel_success")

    def _check_random_ball_save(self, balls: int, **kwargs):
        # If we drain during a ball search or tilt, there may not be a player
        if not self.machine.game or not self.machine.game.player:
            return
        player = self.machine.game.player
        # If the player already has a random ball save, or does not have the perk, do nothing
        if player["random_ball_saved"] or not player["research_random_ball_save_perk"]:
            return

        chance = player["research_random_ball_save_perk"]
        self.log.info("Checking random ball save with {}% chance".format(chance * 100))
        # Don't save if there are multiple balls in play (or none draining)
        if balls <= 0 or self.machine.game.balls_in_play > 1:
            return {}

        if chance > 0 and random.random() < chance:
            self.machine.events.post("random_ball_save_success")
            self.machine.ball_devices["playfield"].add_ball(balls=1, player_controlled=False)
            # This is a relay event. We can change 'balls' to prevent drain
            return {"balls": balls - 1}
            # Store that we've saved on this ball
            player["random_ball_saved"] = 1

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


    def _on_store_item(self, **kwargs):
        if kwargs["item"] == "nothing":
            self.machine.events.post("clear_store_selection")
        else:
            upgrade = RESEARCH[kwargs["item"]]
            # Return all the kwargs we need for that item
            self.machine.events.post("update_store_selection",
                                     **upgrade.to_kwargs(self.machine.game.player, next_level=True))
