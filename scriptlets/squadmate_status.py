"""Helper utility for getting lists of squadmates."""

import random
from mpf.core.utility_functions import Util

SQUADMATES = ("garrus", "grunt", "jack", "jacob", "kasumi", "legion",
              "miranda", "mordin", "samara", "tali", "thane", "zaeed")
BIOTICMATES = ("jack", "jacob", "miranda", "samara", "thane")
TECHMATES = ("garrus", "jacob", "kasumi", "legion", "mordin", "tali", "thane")


def _mate_status_is(player, squadmate, status):
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
    def recruitable_mates(player):
        """Return all squadmates who have available recruitment missions."""
        return _get_available_mates(player, status=3)

    @staticmethod
    def dead_mates(player):
        """Return all squadmates who are dead."""
        return _get_available_mates(player, status=-1)
