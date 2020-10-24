import logging
import random
from mpf.core.mode import Mode

class Mission():
    def __init__(self, name, description):
        self.id = name.replace(" ","_").lower()
        self.name = name
        self.description = description
        self._completed_by_player = [False, False, False, False]
    
    def is_available(self, player):
        return self._completed_by_player[player.index] == False

STANDARD_MISSIONS = [
    Mission("Abandoned Mine", "It's an abandoned mine! Oh no scary!"),
    Mission("Captured Mining Facility", "Who took it?"),
    Mission("Endangered Research Station", "Save it from the sun!"),
    Mission("Imminent Ship Crash", "WE'RE CRASHING"),
    Mission("Lost Operative", "Where'd ya go, buddy?"),
    Mission("Mining the Canyon", "Mine, boys, mine every mountain and dig, boys, dig every stream"),
    Mission("MSV Estevanico", "Done ship be dangerous! Watch out!"),
    Mission("Quarian Crash Site", "Lunch time!"),
]

MERC_MISSIONS = [
    # Blue Suns Missions
    Mission("Archeological Dig Site", "Dr. Grant? Dr. Sattler?"),
    Mission("MSV Strontium Mule", "Nice ship. Where all the crew?"),
    Mission("Blue Suns Base", "AVEEENNNGGGGEeEE"),
    Mission("Javelin Missiles Launched", "It's a real Sophie's choice, isn't it?"),
    # Blood Pack Missions
    Mission("Communications Relay", "what are those silly blood pack up to?"),
    Mission("Blood Pack Base", "Get 'em, boys!")
]

VI_MISSIONS = [
    Mission("Wrecked Merchant Freighter", "183 murderous robots, oh my!"),
    Mission("Abandoned Research Station", "Robot lady wanna kill me!"),
    Mission("Hahne-Kedar Facility", "Stop the bots!"),
]


class N7Assignments(Mode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("N7 Assignments")
        self.log.setLevel(10)
        self._mission = None
        
    def start(self, **kwargs):
        """ Override the initial start method so we can prevent start if there are no missions """
        target_mission = None
        iteration = self.player["assignments_played"] + 1
        # Every third mission is a possible VI mission
        if iteration % 3 == 0:
            target_mission = self._find_next_mission(VI_MISSIONS)
        # Every other mission is a possible Blue Suns or Blood Pack misison
        if not target_mission and iteration % 2 == 0:
            self.log.debug("- no vi missions")
            target_mission = self._find_next_mission(MERC_MISSIONS)
        if not target_mission:
            self.log.debug("- no merc missions")
            target_mission = self._find_random_mission(STANDARD_MISSIONS)
        if not target_mission:
            self.log.debug("- no standard missions")
            # Getting here means we aren't on a 2/3 multiple but there are no standard missions left.
            # Try for a merc mission before we abandon all hope
            target_mission = self._find_next_mission(VI_MISSIONS + MERC_MISSIONS)
        if not target_mission:
            self.log.debug("- no fallback missions")
            # ABORT!
            return

        self.log.debug("Fonud an N7 assignment! '{}'".format(target_mission.name))
        # If we made it this far, there's a mission to do. Proceed with the mode starting
        super().start(**kwargs)
        self._mission = target_mission
        self.player["assignments_played"] += 1

    def mode_start(self, **kwargs):
        self.machine.events.post("set_n7_mission", 
            title=self._mission.name,
            id=self._mission.id)

    def _find_next_mission(self, mission_set):
        for mission in mission_set:
            if mission.is_available(self.player):
                return mission
    
    def _find_random_mission(self, mission_set):
        try:
            return random.choice([mission for mission in mission_set if mission.is_available(self.player)])
        except IndexError:
            return None