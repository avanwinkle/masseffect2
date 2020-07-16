
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
#      - Redundant field generator 1-6: random chance for a ball save on drain [PALLADIUM]
#  - Cybernetic upgrades:
#      - Heavy Skin weave 1-6: increase timer durations [IRIDIUM]
#      - Argus Scanner Array 1-6: accelerate awarding of minerals [IRIDIUM]
#  - Medigel upgrades
#     - Medigel capacity 1-6: award medigel when lower lanes completed [PLATINUM]
#     - Trauma module 1-6: random chance to light both outlanes on medigel [PLATINUM]
#  - Bio-amp / Omni-tool upgrades:
#      - Biotic duration: 1-6 increase power durations [EEZO]
#      - Tech duration: 1-6 increase timer durations [EEZO]
#      - Biotic cooldown: accelerate awarding of powers [EEZO]
#      - Tech cooldown: accelerate awarding of powers [EEZO]

import logging
import random
from mpf.modes.carousel.code.carousel import Carousel

PERKS = ["award_medigel_bool", "double_medigel_bool", "ball_save_period",
         "cooldown_rate", "mineral_rate", "point_multiplier", "tick_interval"]
POWERS = ["adrenaline", "armor", "cloak", "charge", "drone", "singularity"]


class Store(Carousel):
    def mode_init(self):
        super().mode_init()
        self.log = logging.getLogger("Store")
        self.log.setLevel(20)
        self.mineral = None

    def mode_start(self, **kwargs):
        self._all_items = self.machine.game.player["store_options"].split("|")

        # For high-flow mode, pick an item at random and purchase it
        if self.machine.game.player["high_flow"]:
            self.log.debug("Store is in high-flow, randomly selecting an item")
            self._items = [random.choice(self._all_items)]
            self._select_item()
            # Play an event for the sound
            # TODO: Create slides that show what item was purchased, using
            # this event and the existing codex images. Put it in global so
            # it can display after store closes.
            self.machine.events.post("store_high_flow_skip", purchase=self._items[0])
            self.machine.events.post("mode_store_will_stop")
            return
        
        self._all_items.append("nothing")
        super().mode_start(**kwargs)
        self.log.debug("Store is starting")
        self.machine.events.post("store_{}_highlighted".format(self._all_items[0]))
        self.add_mode_event_handler("slide_store_slide_active", self._update_highlighted_item)

    def _update_highlighted_item(self, direction=None, **kwargs):
        h = self._get_highlighted_item()
        for item in self._all_items:
            if item == h:
                self.machine.events.post("store_{}_highlighted".format(item))
                self.machine.events.post("store_item_highlighted", item=item)
            else:
                self.machine.events.post("store_{}_default".format(item))

    def _select_item(self, **kwargs):
        super()._select_item()
        selection = self._get_highlighted_item()
        self.machine.events.post("research_purchased", selection=selection)

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
