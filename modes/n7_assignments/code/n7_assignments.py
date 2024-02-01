"""Custom code for N7 Assignments mode."""
import math
import random
from mpf.core.mode import Mode


class Mission():

    """A mission instance to store name, description, and state."""

    def __init__(self, name, callout, description):
        """Create an instance of N7 Mission data."""
        self.id = name.replace(" ", "_").replace("\n", "_").lower()
        # There are linefeeds in the name for the main slide
        self.name = name
        # Remove linefeeds for the dossier slide
        self.long_name = name.replace("\n", " ")
        self.description = description
        self.callout = callout
        self._completed_by_player = [False, False, False, False]

    def is_available(self, player):
        """Return true if the given player has not yet completed this mission."""
        return not self._completed_by_player[player.index]


STANDARD_MISSIONS = [
    Mission("Abandoned Mine", "anomaly", "Surface scans report potential\nalien signatures from within the\nmining facility. Anomalous life\nsigns detected. Whereabouts of\nfacility staff unknown."),
    Mission("Anomalous Weather\nDetected", "anomalous_weather", "Sensors detecting anomalous\nweather patterns on the planet's\nsurface. Geth activity detected.\nRecommend extreme caution."),
    Mission("Captured\nMining Facility", "distress", "Mercenary activity detected inside\na mining facility on planet's surface.\nEclipse presence confirmed. Distress\nbeacon powered down at site.\nSensors detect multiple spacefaring\nvessel launches from facility."),
    Mission("Eclipse Smuggling Depot", "eclipse_smuggling_depot", "The planet Daratar is a suspected\nEclipse smuggling site. Cerberus\nwill pay handsomely for any intact\ncrates retrieved from the site.\nBe aware that Eclipse would rather\nsee the cargo destroyed than lose\nit to a rival organization."),
    Mission("Endangered\nResearch Station", "anomaly", "Planetary scans indicate that the\nSinmara colony is vulnerable to its\nsun's hazardous solar flares.\nThe magnetic shield must be\nreactivated to avoid exposing\ncolony to unstable solar activity\nand potential annihilation."),
    Mission("Imminent Ship Crash", "imminent_ship_crash", "Scans detect a rapidly decaying ship\nin orbit. Ship's manifest notes\nvolatile munitions cargo onboard.\nHigh probability that the crash site\nwill be Jonus's largest human colony.\n\nGeth signatures detected aboard."),
    Mission("Lost Operative", "anomaly", "Scans detect a transmitter matching\nCerberus encryption. It is registered\nto an unknown operative in deep\ncover. Operative's life signs\nunconfirmed. Other transmissions\nthat match known Eclipse coded\ncommunications also detected."),
    Mission("Mining the Canyon", "anomaly", "Scans detect one YMIR heavy mech\nsignature matching an unknown\n(possibly pirate) registration. Mech\nappears to be disabled but\nbroadcasting a looping message.\nResource scans indicate large\nquantities of mineral resources."),
    Mission("MSV Estevanico", "distress", "Scans indicate the presence of a\nlarge shipwreck. Signature bears\nsimilarity to the missing merchant\nfreighter MSV Estevanico. Structural\nintegrity is critical. Life support is\ndamaged but partially functional.\nRecommend extreme caution."),
    Mission("Quarian Crash Site", "quarian_crash_site", "Surface scans show evidence of a\nshipwreck meeting quarian design\nspecifications. Identity of ship\nunknown. Number of life signs\ndetected in vicinity: uncertain.\nLocal wildlife may interfere with\naccuracy of biological scan."),
]

MERC_MISSIONS = [
    # Blue Suns Missions
    Mission("Archeological Dig Site", "anomaly", "Mercenary activity detected on\nplanet surface. Communications\nmatch Blue Suns encoding protocols.\nPossible location for rumored site\nof illegal archeological activity.\nBlue Suns intentions unknown."),
    Mission("MSV Strontium Mule", "distress", "Derelict ship MSV Strontium Mule,\nvisibly damaged from weapons fire.\nShip not responding to hails despite\nlife signs aboard. Transmissions\nusing known Blue Suns encryption\ndetected. Airlocks sealed, but ship\ncan be boarded through cargo hold."),
    Mission("Blue Suns Base", "distress", "Distress beacon is confirmed to\nbe a fabrication set to lure\nunsuspecting ships into orbit for\npirate ambush. Surface scans\nshow Blue Suns communication\nsignatures concentrated\naround a shuttle hangar bay."),
    Mission("Javelin Missiles\nLaunched", "javelin_missiles_launched", "Scans detect a colony defended by\na Javelin missile base. A distress\nsignal indicates that the base is\nc ompromised by batarians who\nhave launched two missiles at the\ncolony. Total destruction of colony\nis imminent."),
    # Blood Pack Missions
    Mission("Communications Relay", "anomaly", "Scans indicate a high-powered\ncommunications relay on the planet.\nCommunications match known\nBlood Pack protocols. Krogan and\nvorcha signals are massed inside\nwhat appears to be a mining\noperation. Advise caution."),
    Mission("Blood Pack Base", "anomaly", "Surface scans show a crude base\nestablished on the planet's surface.\nCommunications match known\nBlood Pack protocols. Numerous life\nsigns matching vorcha genealogy\ndetected. Resource scans match\ndata on weapons manufacturing.")
]

VI_MISSIONS = [
    Mission("Wrecked\nMerchant Freighter", "distress", "Surface scans indicate wreckage of\na merchant freighter, configuration\nunknown. Damage to ship\ncatastrophic. Detecting movement,\nbut no signs of life."),
    Mission("Abandoned\nResearch Station", "anomaly", "Data mining confirms the last\nreported location of merchant\nfreighter MSV Corsica. Possibility\nexists that clues pertaining to the\nanomaly that caused the mass\nmalfunction of the mechs can be\nfound aboard this station."),
    Mission("Hahne-Kedar Facility", "distress", "Facility reports emergency lockdown\nat this location. Hazard scans show\na large number of virus-infected\nmechs quarantined within the\nfacility. Deactivate the production\nline to disrupt the creation of\nadditional infected mechs."),
]


class N7Assignments(Mode):

    """Mode code for selecting (usually) random N7 assignments."""

    def __init__(self, *args, **kwargs):
        """Initialize mode with no mission and track that it hasn't been played yet."""
        super().__init__(*args, **kwargs)
        self._mission = None

    def start(self, mode_priority=None, callback=None, **kwargs):
        """Override the initial start method so we can prevent start if there are no missions."""
        target_mission = None
        iteration = self.player["assignments_played"] + 1
        # Every third mission is a possible VI mission
        if iteration % 3 == 0:
            target_mission = self._find_next_mission(VI_MISSIONS)
        # Every other mission is a possible Blue Suns or Blood Pack misison
        if not target_mission and iteration % 2 == 0:
            self.debug_log("- no vi missions")
            target_mission = self._find_next_mission(MERC_MISSIONS)
        if not target_mission:
            self.debug_log("- no merc missions")
            target_mission = self._find_random_mission(STANDARD_MISSIONS)
        if not target_mission:
            self.debug_log("- no standard missions")
            # Getting here means we aren't on a 2/3 multiple but there are no standard missions left.
            # Try for a merc mission before we abandon all hope
            target_mission = self._find_next_mission(VI_MISSIONS + MERC_MISSIONS)
        if not target_mission:
            self.debug_log("- no fallback missions")
            # ABORT!
            return

        # TESTING: Allow a specific mission
        # TEST_MISSION = "blue_suns_base"
        # if TEST_MISSION:
        #     target_mission = next(x for x in MERC_MISSIONS if x.id == TEST_MISSION)

        # If we made it this far, there's a mission to do. Proceed with the mode starting
        self._mission = target_mission
        super().start(mode_priority, callback, **kwargs)

    def mode_start(self, **kwargs):
        """Setup the event for populating slide data on start."""
        del kwargs
        self.player["assignments_played"] += 1

        # If this is the first mission, 100%
        if self.player["assignments_played"] == 1:
            rating = 100
        else:
            rating = math.ceil(100 * self.player["assignments_completed"] / self.player["assignments_played"])
        self.machine.events.post("set_n7_mission",
                                 title=self._mission.name,
                                 long_title=self._mission.long_name,
                                 description=self._mission.description,
                                 id=self._mission.id,
                                 rating=rating)

        self.add_mode_event_handler("n7_assignment_hit", self._on_hit)
        self.machine.auditor.audit_event("mode_n7_assignments_started")
        self.machine.clock.schedule_once(self._play_callout, 1)

    def _check_achievement(self, rating):
        if rating == 100:
            return "platinum"
        elif rating >= 75:
            return "gold"
        elif rating >= 50:
            return "silver"
        elif rating >= 25:
            return "bronze"
        else:
            return "default"

    def _find_next_mission(self, mission_set):
        for mission in mission_set:
            if mission.is_available(self.player):
                return mission

    def _find_random_mission(self, mission_set):
        try:
            return random.choice([mission for mission in mission_set if mission.is_available(self.player)])
        except IndexError:
            return None

    def _play_callout(self, **kwargs):
        del kwargs
        self.machine.events.post("n7_callout", callout=self._mission.callout)

    def _on_hit(self, **kwargs):
        del kwargs
        # Increment assignments count, reputation, and xp
        self.player["assignments_completed"] += 1
        self.player["earned_assignments_completed"] += 1
        self.player["reputation"] += 3
        self.player["xp"] += self.machine.variables.get_machine_var("assignment_xp")
        # In addition to the shot amount, multiply by the number of missions completed
        self.player["score"] += self.player["mission_shot_value"] * self.player["earned_assignments_completed"]
        rating = math.ceil(100 *
            self.player["assignments_completed"] / self.player["assignments_played"])
        achievement = self._check_achievement(rating)
        self.machine.events.post("n7_assignment_success", rating=rating, achievement=achievement)
