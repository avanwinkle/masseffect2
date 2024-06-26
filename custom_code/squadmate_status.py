"""Helper utility for getting lists of squadmates."""

import random
from mpf.core.utility_functions import Util

# Order the squadmates left-to-right on backbax
SQUADMATES = ("zaeed", "legion", "samara", "tali", "mordin", "garrus", "miranda",
              "grunt", "jacob", "thane", "jack", "kasumi")
BIOTICMATES = ("samara", "miranda", "jacob", "thane", "jack")
TECHMATES = ("legion", "tali", "mordin", "garrus", "jacob", "thane", "kasumi")
CASUAL_UNLOCKS = ("grunt", "jack", "garrus", "kasumi", "mordin")
UNLOCK_WEIGHTS = (3, 3, 3, 1, 3)

def _mate_status_is(player, squadmate, status):
    # A bug exists where player can be None. Figure out how?!
    return player["status_{}".format(squadmate)] == status


def _get_available_mates(player, mates=SQUADMATES, status=4, include_specialist=True, exclude=None):
    exclude = Util.string_to_list(exclude)
    if not include_specialist:
        exclude.append(player["specialist"])
    return [mate for mate in mates if (_mate_status_is(player, mate, status) and mate not in exclude)]


class SquadmateStatus():
    """Class to provide public methods for getting squadmates."""

    @staticmethod
    def all_mates():
        """Return all squadmates."""
        return SQUADMATES

    @staticmethod
    def all_biotics():
        """Return all biotic specialists."""
        return BIOTICMATES

    @staticmethod
    def all_techs():
        """Return all tech specialists."""
        return TECHMATES

    @staticmethod
    def available_mates(player, **kwargs):
        """Return all available mates: recruited AND alive."""
        return _get_available_mates(player, **kwargs)

    @staticmethod
    def available_biotics(player):
        """Return all available biotic specialists."""
        return _get_available_mates(player, mates=BIOTICMATES)

    @staticmethod
    def available_techs(player):
        """Return all available tech specialists."""
        return _get_available_mates(player, mates=TECHMATES)

    @staticmethod
    def random_mate(player, exclude=None):
        """Return a random squadmate who is available."""
        return random.choice(_get_available_mates(player, exclude=exclude))

    @staticmethod
    def random_recruit():
        """ Return a random squadmate to start unlocked in casual mode."""
        return random.choices(CASUAL_UNLOCKS, weights=UNLOCK_WEIGHTS)[0]

    @staticmethod
    def random_selected(player, exclude=None):
        """ Return at random one of the two mates currently selected."""
        return random.choice([mate for mate in [player["selected_mate_one"], player["selected_mate_two"]] if mate != exclude])

    @staticmethod
    def recruitable_mates(player):
        """Return all squadmates who have available recruitment missions."""
        return _get_available_mates(player, status=3)

    @staticmethod
    def dead_mates(player):
        """Return all squadmates who are dead."""
        return _get_available_mates(player, status=-1)

    @staticmethod
    def final_mates(player):
        """Return all squadmates who survived the Suicide Mission."""
        return _get_available_mates(player, status=5)
