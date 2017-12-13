from mpf.core.config_processor import ConfigProcessor
import re
import os, sys
import shutil

verbose = False

def match_configs(gamePath, doCopy=False):
  allconfigs = RequiredSounds()
  gamesounds = GameSounds(gamePath)

  soundCheck = {}
  counts = { 'found': [], 'missing': [], 'available': [], 'unavailable': [] }

  for mode, modesounds in allconfigs.getAllConfigs().items():
    for track, sounds in modesounds.byTrack().items():
      for sound in sounds:
        modepath = "modes/{}/sounds/{}/".format(mode, track)
        gamepath = None
        exists = False
        try:
          exists = os.stat(modepath)
          counts['found'].append(sound)
        except(FileNotFoundError):
          counts['missing'].append(sound)
          try:
            gamepath = gamesounds.getFilePath(sound)
            counts['available'].append(sound)
          except(ValueError):
            counts['unavailable'].append(sound)

        soundCheck[sound] = { "mode": mode, "modepath": modepath, "gamepath": gamepath, "exists": exists}

  available = len(counts['available'])

  if doCopy:
    print("\n{} {} files into modes:".format("Copying" if doCopy else "Simulating copy of", available))
    print("--------------------------------------------")
    original_umask = os.umask(0)
    for idx, filename in enumerate(counts['available']):
      src = soundCheck[filename]['gamepath']
      dst = soundCheck[filename]['modepath']
      print(" {}/{}: {} -> {}".format(idx+1, available, src, dst))
      os.makedirs(dst, mode=0o774, exist_ok=True)
      shutil.copy2(src, dst)
    os.umask(original_umask)

  print("Found {} sounds across {} config files.".format(len(soundCheck), len(allconfigs)))
  print(" - {} files accounted for".format(len(counts['found'])))
  print(" - {} missing files available {}".format(available, "and copied" if doCopy else "for copy"))
  if (len(counts['unavailable']) > 0):
    print(" - {} files missing and unavailable:".format(len(counts['unavailable'])))
    for filename in counts['unavailable']:
      print("    : {} ({})".format(filename, soundCheck[filename]['mode']))

def prune_files(doDelete=False):
  allconfigs = RequiredSounds()
  existingsounds = GameSounds('./')

  orphanedfiles = []
  matchedfilescount = 0

  for file in existingsounds.getFiles():
    mode = allconfigs.findRequiringMode(file)
    if not mode:
      orphanedfiles.append(existingsounds.getFilePath(file))
    else:
      if verbose:
        print("{} -> {}".format(file, mode.name))
      matchedfilescount += 1

  print("Found {} required files and {} orphaned files.\n".format(matchedfilescount, len(orphanedfiles)))
  if (len(orphanedfiles) > 0):
    print("REMOVING ORPHANED FILES:" if doDelete else "ORPHANED FILES TO REMOVE:")
    for orphan in orphanedfiles:
      print(orphan)
      if doDelete:
        os.remove(orphan)

class RequiredSounds(object):
  def __init__(self):
    self._allconfigs = {} # Key: mode/config name, Value: ModeSounds object
    self._sounds_by_filename = {} # Key: array of filenames, Value: ModeSounds object
    self._allsoundfiles = []
    for path, dirs, files in os.walk('modes'):
      for file in files:
        if file.endswith('.yaml'):
          configfilename = file[:-5]
          conf = ConfigProcessor.load_config_file('{}/{}'.format(path,file), "mode")
          sounds = ModeSounds(configfilename)
          sounds.parseConfig(conf)
          if len(sounds) > 0:
            self._allconfigs[configfilename] = sounds

  def getAllConfigs(self):
    return self._allconfigs

  def findRequiringMode(self, filename):
    # So we only have to do this once, make all of the sound files in a Mode into an array key
    if not self._sounds_by_filename:
      for sounds in self._allconfigs.values():
        for filename in sounds.all():
          self._sounds_by_filename[filename] = sounds
          self._allsoundfiles.append(filename)

    # Easiest check: is this file required _anywhere_ ?
    if filename not in self._allsoundfiles:
      return None

    # Next check: find which mode requires it
    for filelist in self._sounds_by_filename:
      if filename in filelist:
        return self._sounds_by_filename[filelist]

  def __len__(self):
    return len(self._allconfigs)

class GameSounds(object):
  def __init__(self, root):
    # Most efficient way: two arrays in parallel?
    self._soundfiles, self._soundpaths = [], []
    for path, dirs, files in os.walk(root):
      for file in files:
        if file.endswith('.ogg'):
          self._soundfiles.append(file)
          self._soundpaths.append(path)

  def getFilePath(self, filename):
    idx = self._soundfiles.index(filename)
    return "{}/{}".format(self._soundpaths[idx], self._soundfiles[idx])

  def getFiles(self):
    return self._soundfiles

class ModeSounds(object):
  def __init__(self, modeName=None):
    self._dict = {}
    self._tracks = []
    self._files = []
    self.name = modeName

  def parseConfig(self, modeConfig):
    if not 'sounds' in modeConfig or not modeConfig['sounds']:
      return self

    for sound in modeConfig['sounds'].values():
      self.addSound(sound)

  def addSound(self, soundDict):
    fileName = soundDict['file']
    # If a track is explicitly defined, use it
    if 'track' in soundDict and soundDict['track']:
      trackName = soundDict['track']
    elif fileName.startswith('en_us_'):
      trackName = 'voice'
    elif fileName.startswith('mus_'):
      trackName = 'music'
    else:
      trackName = 'unknown'

    self._addTrack(trackName)
    self._files.append(fileName)
    self._dict[trackName].append(fileName)

  def checkSound(self, filename):
    return filename in self._files

  def _addTrack(self, trackName):
    if not trackName in self._tracks:
      self._tracks.append(trackName)
      self._dict[trackName] = []

  def all(self):
    return self._files

  def byTrack(self):
    return self._dict

  def __str__(self):
    return self._dict.__str__()

  def __repr__(self):
    return "<ModeSounds '{}': {} files>".format(self.name, len(self))

  def __len__(self):
    return len(self._files)

def main():
  args = sys.argv[1:]
  writeMode = False

  if "-v" in args:
    verbose = True
  if "-w" in args:
    writeMode = True

  if args[0] == "prune":
    prune_files(doDelete=writeMode)

  elif args[0] == "copy":
    # The second arg needs to be a path
    try:
      os.stat(args[1])
      match_configs(args[1], doCopy=writeMode)
    except(IndexError):
      print("MeSound requires a path to your Mass Effect 2 audio dump folder.")
      print("Usage: python mesound.py [prune|copy] <path_to_masseffect_sounds> [-v|-w]")
    except(FileNotFoundError):
      print("MeSound requires a path to your Mass Effect 2 audio dump folder.")
      print("Path not found: '{}'".format(args[0]))

  else:
    print("""
---Mass Effect Pinball Sound Script---

Use this script to copy audio files from your Mass Effect 2 game into the
corresponding ME2 Pinball mode folders. Requires a data dump folder created by 
Mass Effect 2 Extractor containing source audio folders and ogg files 
(e.g. 'endgm2_longwalk_a_s_int', 'en_us_player_f_endgm2_escape_c_00287372_f.ogg')

Options:
  copy  - Copy all required audio files into the ME2 mode folders
  prune - Remove all mode audio files not referenced in config files (will not affect dump folder)

Params:
  path_to_masseffect_sounds - Path to the data dump folder created by Mass Effect 2 Extractor

Flags:
  -v    - Verbose mode
  -w    - Write mode (actually copy/prune files)

Usage: 
>> python mesound.py [prune|test|copy] <path_to_masseffect_sounds> [-v|-w]
""")

if __name__ == "__main__":
  main()