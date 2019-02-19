SQUADMATES = ("garrus", "grunt", "jack", "jacob", "kasumi", "legion", "miranda", "mordin", "samara", "tali", "thane", "zaeed")
BIOTICMATES = ("jack", "jacob", "miranda", "samara", "thane")
TECHMATES = ("garrus", "jacob", "kasumi", "legion", "mordin", "tali", "thane")

def _mate_status_is(player, squadmate, status):
  return player["status_{}".format(squadmate)] == status

def _get_available_mates(player, mates=SQUADMATES, status=4, include_specialist=True):
  specialist = None if include_specialist else player["specialist"]
  return [mate for mate in mates if (_mate_status_is(player, mate, status) and mate != specialist)]

class SquadmateStatus():
  @staticmethod
  def all_mates():
    return SQUADMATES

  @staticmethod
  def all_biotics():
    return BIOTICMATES

  @staticmethod
  def all_techs():
    return TECHMATES

  @staticmethod
  def available_mates(player, **kwargs):
    return _get_available_mates(player, **kwargs)

  @staticmethod
  def available_biotics(player):
    return _get_available_mates(player, mates=BIOTICMATES)

  @staticmethod
  def available_techs(player):
    return _get_available_mates(player, mates=TECHMATES)

  @staticmethod
  def recruitable_mates(player):
    return _get_available_mates(player, status=3)

  @staticmethod
  def dead_mates(player):
    return _get_available_mates(player, status=-1)
