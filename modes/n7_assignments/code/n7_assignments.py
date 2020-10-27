import logging
import math
import random
from mpf.core.mode import Mode

class Mission():
    def __init__(self, name, description):
        self.id = name.replace(" ","_").replace("\n","_").lower()
        # There are linefeeds in the name for the main slide
        self.name = name
        # Remove linefeeds for the dossier slide
        self.long_name = name.replace("\n", " ")
        self.description = description
        self._completed_by_player = [False, False, False, False]

    def is_available(self, player):
        return self._completed_by_player[player.index] == False

STANDARD_MISSIONS = [
    Mission("Abandoned Mine", "Surface scans report potential\nalien signatures from within the\nmining facility. Anomalous life\nsigns detected. Whereabouts of\nfacility staff unknown."),
    Mission("Anomalous Weather Detected", "Sensors detecting anomalous\nweather patterns on the planet's\nsurface. Geth activity detected.\nRecommend extreme caution."),
    Mission("Captured\nMining Facility", "Mercenary activity detected inside\na mining facility on planet's surface.\nEclipse presence confirmed. Distress\nbeacon powered down at site.\nSensors detect multiple spacefaring\nvessel launches from facility."),
    Mission("Eclipse Smuggling Depot", "The planet Daratar is a suspected\nEclipse smuggling site. Cerberus\nwill pay handsomely for any intact\ncrates retrieved from the site.\nBe aware that Eclipse would rather\nsee the cargo destroyed than lose\nit to a rival organization."),
    Mission("Endangered\nResearch Station", "Planetary scans indicate that the\nSinmara colony is vulnerable to its\nsun's hazardous solar flares.\nThe magnetic shield must be\nreactivated to avoid exposing\ncolony to unstable solar activity\nand potential annihilation."),
    Mission("Imminent Ship Crash", "Scans detect a rapidly decaying ship\nin orbit. Ship's manifest notes\nvolatile munitions cargo onboard.\nHigh probability that the crash site\nwill be Jonus's largest human colony.\n\nGeth signatures detected aboard."),
    Mission("Lost Operative", "Scans detect a transmitter matching\nCerberus encryption. It is registered\nto an unknown operative in deep\ncover. Operative's life signs\nunconfirmed. Other transmissions\nthat match known Eclipse coded\ncommunications also detected."),
    Mission("Mining the Canyon", "Scans detect one YMIR heavy mech\nsignature matching an unknown\n(possibly pirate) registration. Mech\nappears to be disabled but\nbroadcasting a looping message.\nResource scans indicate large\nquantities of mineral resources."),
    Mission("MSV Estevanico", "Scans indicate the presence of a\nlarge shipwreck. Signature bears\nsimilarity to the missing merchant\nfreighter MSV Estevanico. Structural\nintegrity is critical. Life support is\ndamaged but partially functional.\nRecommend extreme caution."),
    Mission("Quarian Crash Site", "Surface scans show evidence of a\nshipwreck meeting quarian design\nspecifications. Identity of ship\nunknown. Number of life signs\ndetected in vicinity: uncertain.\nLocal wildlife may interfere with\naccuracy of biological scan."),
]

MERC_MISSIONS = [
    # Blue Suns Missions
    Mission("Archeological Dig Site", "Mercenary activity detected on\nplanet surface. Communications\nmatch Blue Suns encoding protocols.\nPossible location for rumored site\nof illegal archeological activity.\nBlue Suns intentions unknown."),
    Mission("MSV Strontium Mule", "Derelict ship MSV Strontium Mule,\nvisibly damaged from weapons fire.\nShip not responding to hails despite\nlife signs aboard. Transmissions\nusing known Blue Suns encryption\ndetected. Airlocks sealed, but ship\ncan be boarded through cargo hold."),
    Mission("Blue Suns Base", "Distress beacon is confirmed to\nbe a fabrication set to lure\nunsuspecting ships into orbit for\npirate ambush. Surface scans\nshow Blue Suns communication\nsignatures concentrated\naround a shuttle hangar bay."),
    Mission("Javelin Missiles\nLaunched", "Scans detect a colony defended by\na Javelin missile base. A distress\nsignal indicates that the base is\nc ompromised by batarians who\nhave launched two missiles at the\ncolony. Total destruction of colony\nis imminent."),
    # Blood Pack Missions
    Mission("Communications Relay", "Scans indicate a high-powered\ncommunications relay on the planet.\nCommunications match known\nBlood Pack protocols. Krogan and\nvorcha signals are massed inside\nwhat appears to be a mining\noperation. Advise caution."),
    Mission("Blood Pack Base", "Surface scans show a crude base\nestablished on the planet's surface.\nCommunications match known\nBlood Pack protocols. Numerous life\nsigns matching vorcha genealogy\ndetected. Resource scans match\ndata on weapons manufacturing.")
]

VI_MISSIONS = [
    Mission("Wrecked\nMerchant Freighter", "Surface scans indicate wreckage of\na merchant freighter, configuration\nunknown. Damage to ship\ncatastrophic. Detecting movement,\nbut no signs of life."),
    Mission("Abandoned\nResearch Station", "Data mining confirms the last\nreported location of merchant\nfreighter MSV Corsica. Possibility\nexists that clues pertaining to the\nanomaly that caused the mass\nmalfunction of the mechs can be\nfound aboard this station."),
    Mission("Hahne-Kedar Facility", "Facility reports emergency lockdown\nat this location. Hazard scans show\na large number of virus-infected\nmechs quarantined within the\nfacility. Deactivate the production\nline to disrupt the creation of\nadditional infected mechs."),
]


class N7Assignments(Mode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        super().start(**kwargs)
        self._mission = target_mission
        self.player["assignments_played"] += 1

    def mode_start(self, **kwargs):
        rating = math.ceil(100 * (self.player["earned_assignments_completed"] + 1) / self.player["assignments_played"])
        self.machine.events.post("set_n7_mission",
            title=self._mission.name,
            long_title=self._mission.long_name,
            description=self._mission.description,
            id=self._mission.id,
            rating=rating)

    def _find_next_mission(self, mission_set):
        for mission in mission_set:
            if mission.is_available(self.player):
                return mission

    def _find_random_mission(self, mission_set):
        try:
            return random.choice([mission for mission in mission_set if mission.is_available(self.player)])
        except IndexError:
            return None