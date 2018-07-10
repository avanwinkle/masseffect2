from mpf.core.config_processor import ConfigProcessor
from mpf.core.config_validator import ConfigValidator
from mpf.core.utility_functions import Util
import re
import os, sys
import shutil
import logging
from datetime import datetime

configProcessor = ConfigProcessor(ConfigValidator(None))

class SoundManager():
  def __init__(self, verbose=False):
    self.machine_configs = None
    self.machine_assets = None
    self.source_media = None
    self.source_path = None
    self._analysis = None

    self.log = logging.getLogger()
    self.log.addHandler(logging.StreamHandler(sys.stdout))
    self.log.setLevel("DEBUG" if verbose else "INFO")
    self._get_source_path()

  def _load_machine_configs(self, refresh=False):
    if refresh or not self.machine_configs:
      self.log.info("  Loading config files...")
      self.machine_configs = RequiredSounds()

  def _load_source_media(self, refresh=False):
    if refresh or not self.source_media:
      self.log.info("  Loading media files from source folder...")
      self.source_media = GameSounds(self.source_path)

  def _load_machine_assets(self, refresh=False):
    if refresh or not self.machine_assets:
      self.log.info("  Loading assets from machine folder...")
      self.machine_assets = GameSounds("./")

  def refresh(self):
    self._load_machine_configs(refresh=True)
    self._load_source_media(refresh=True)
    self._load_machine_assets(refresh=True)

  def set_source_path(self):
    print("Set path to your media source folder:")
    rawpath = input(">> ").strip()
    # Store full paths, not relative
    source_path = rawpath.replace("~", os.environ['HOME'])
    f = open("./.mesound_path", "w")
    f.write(source_path)
    f.close()
    return source_path

  def _get_source_path(self):
    sourcepath = self.source_path
    if not sourcepath:
      try:
        f = open("./.mesound_path")
        sourcepath = f.readline()
        f.close()
        if not sourcepath or not os.stat(sourcepath):
          raise FileNotFoundError
      except(FileNotFoundError):
        print("Unable to read media source path.")
        sourcepath = self.set_source_path()
    try:
      os.stat(sourcepath)
    except(FileNotFoundError):
      print("MPFSound requires a path to your source media folder.")
      print("Path not found: '{}'\nExiting...".format(sourcepath))
      sys.exit()
    self.source_path = sourcepath

  def parse_machine_assets(self, writeMode=False):
    self.log.info("\nMPF Sound Asset Manager [{}]".format("WRITE MODE" if writeMode else "READ-ONLY"))
    self.log.info("----------------------------------------------------")
    self.log.info("Parsing machine configs, assets, and source media:")
    self._load_machine_configs()
    self._load_machine_assets()
    self._load_source_media()
    matchedfilescount = 0

    self._analysis = {
      'found': [],
      'missing': [],
      'available': {},
      'unavailable': [],
      'misplaced': {}, # Key: expected file path; Value: current/wrong file path
      'orphaned': [],
      'duplicated': [],
      'sounds': {} # Key: sound file name; Value: sound object
    }

    dupes = self.machine_assets.getDuplicates()
    # First, look through all the files that exist in the mode folders to find orphaned, misplaced, and duplicate
    for idx, filename in enumerate(self.machine_assets.getFiles()):
      filepath = self.machine_assets.getFilePath(filename)
      mode = self.machine_configs.findRequiringMode(filename)
      # If this file is not required by any configs
      if not mode:
        self._analysis['orphaned'].append(filepath)
      else:
        expectedpath = "./modes/{}/sounds/{}/{}".format(mode.name, mode.findTrackForSound(filename), filename)
        if filepath != expectedpath:
          self.log.info("{} is in the wrong place. Expected {}".format(filepath, expectedpath))
          self._analysis['misplaced'][expectedpath] = filepath
        elif filename in dupes:
          # The expected path is for the ONE mode that legit requires this file
          for dupepath in dupes[filename]:
            if expectedpath != dupepath and not dupepath in self._analysis['duplicated']:
              self._analysis['duplicated'].append(dupepath)
        else:
          matchedfilescount += 1
          self.log.debug("Matched {} in node {}".format(filename, mode.name))

    allconfigs = self.machine_configs.getAllConfigs()

    for mode, modesounds in allconfigs.items():
      for track, sounds in modesounds.byTrack().items():
        for sound in sounds:
          if sound in self._analysis['sounds']:
            print("ERROR: Sound file '{}'' in mode {} also exists in mode {}".format(
                  sound, mode, self._analysis['sounds'][sound]['mode']))
            return
          modepath = "./modes/{}/sounds/{}/".format(self.machine_configs.getModeParent(mode), track)
          sourcepath = None
          exists = False
          expectedpath = "{}{}".format(modepath, sound)
          try:
            exists = os.stat(expectedpath)
            self._analysis['found'].append(sound)
          except(FileNotFoundError):
            # Is this file misplaced? Are we planning on moving it?
            if expectedpath in self._analysis['misplaced']:
              pass
            else:
              self._analysis['missing'].append(sound)
              try:
                sourcepath = self.source_media.getFilePath(sound)
                self._analysis['available'][expectedpath] = sourcepath
              except(ValueError):
                self._analysis['unavailable'].append(sound)

          self._analysis['sounds'][sound] = { "mode": mode, "modepath": modepath, "sourcepath": sourcepath, "exists": exists}

    self.log.info("\nFound {} assets defined across {} config files.".format(len(self._analysis['sounds']), len(allconfigs)))
    self.log.info(" - {} files accounted for".format(len(self._analysis['found'])))
    if self._analysis['misplaced']:
      self.log.info(" - {} misplaced files{}".format(len(self._analysis['misplaced']), " will be moved" if writeMode else ""))
    if self._analysis['duplicated']:
      self.log.info(" - {} duplicate files{}".format(len(self._analysis['duplicated']), " will be removed" if writeMode else ""))
    if self._analysis['orphaned']:
      self.log.info(" - {} orphaned files{}".format(len(self._analysis['orphaned']), " will be removed" if writeMode else ""))
    if self._analysis['available']:
      self.log.info(" - {} missing files available {}".format(len(self._analysis['available']), "and copied" if writeMode else "for copy"))
      self.log.debug("    : {} -> {}".format(sourcepath, filename) for filename, sourcepath in self._analysis['available'].items())
    if self._analysis['unavailable']:
      self.log.info(" - {} files missing and unavailable:".format(len(self._analysis['unavailable'])))
      for filename in self._analysis['unavailable']:
        self.log.info("    : {} ({})".format(filename, self._analysis['sounds'][filename]['mode']))
    self.log.info("\n")

  def cleanup_machine_assets(self, writeMode=False):
    if not self._analysis:
      self.parse_machine_assets(writeMode=writeMode)

    if self._analysis['orphaned']:
      self.log.info("REMOVING ORPHANED FILES:" if writeMode else "ORPHANED FILES TO REMOVE:")
      for orphan in self._analysis['orphaned']:
        self.log.info("- {}".format(orphan))
        if writeMode:
          os.remove(orphan)
    if self._analysis['duplicated']:
      self.log.info("REMOVING DUPLICATE FILES:" if writeMode else "DUPLICATE FILES TO REMOVE:")
      for orphan in self._analysis['duplicated']:
        self.log.info("- {}".format(orphan))
        if writeMode:
          os.remove(orphan)
    if self._analysis['misplaced']:
      self.log.info("MOVING MISPLACED FILES:" if writeMode else "MISPLACED FILES TO MOVE:")
      for expectedpath, filepath in self._analysis['misplaced'].items():
        self.log.info(" {} -> {}".format(filepath, expectedpath))
        if writeMode:
          os.makedirs(expectedpath.rsplit("/", 1)[0], mode=0o755, exist_ok=True)
          os.rename(filepath, expectedpath)
    if self._analysis['available']:
      self.log.info("COPYING AVAILABLE FILES:" if writeMode else "AVAILABLE FILES TO COPY:")
      original_umask = os.umask(0)
      for idx, availitem in enumerate(self._analysis['available'].items()):
        dst = availitem[0]
        src = availitem[1]
        self.log.info(" {}/{}: {} -> {}".format(idx+1, len(self._analysis['available']), src, dst))
        # Ensure the target directory exists
        if writeMode:
          os.makedirs(dst.rsplit("/", 1)[0], mode=0o755, exist_ok=True)
          shutil.copy2(src, dst)
      os.umask(original_umask)

    # Any previous analysis is no longer valid
    self._analysis = None
    self.log.info("\n Machine cleanup {} complete!\n".format("changes" if writeMode else "simulation"))

class RequiredSounds(object):
  def __init__(self):
    self._allconfigs = {} # Key: mode/config name, Value: ModeSounds object
    self._childconfigs = {} # Key: mode/config name, Value: ModeSounds object
    self._sounds_by_filename = {} # Key: array of filenames, Value: ModeSounds object
    self._allsoundfiles = []
    # Track modes that are imported into parent modes, so we don't scan them twice
    self._configparents = {} # Key: child config name, Value: parent config

    for path, dirs, files in os.walk('modes'):
      for filename in files:
        if filename.endswith('.yaml'):
          configfilename = filename[:-5]
          conf = configProcessor.load_config_file('{}/{}'.format(path,filename), "mode")
          sounds = ModeSounds(configfilename)
          sounds.parseConfig(conf)
          if len(sounds) > 0:
            self._allconfigs[configfilename] = sounds

          for importedconfigname in conf.get('config', []):
            self._configparents[importedconfigname[:-5]] = configfilename

    # Wait until all configs have been imported, because load order is unpredictable
    for configfilename in self._configparents:
      if configfilename in self._allconfigs:
        self._childconfigs[configfilename] = self._allconfigs[configfilename]
        # TODO: Allow the sounds to exist in their child modes and zip up to parents later
        del self._allconfigs[configfilename]

  def getAllConfigs(self):
    return self._allconfigs

  def getModeParent(self, modename):
    # If the mode is a child mode, return the parents path
    return self._configparents.get(modename, modename)

  def findRequiringMode(self, filename):
    # So we only have to do this once, make all of the sound files in a Mode into an array key
    if not self._sounds_by_filename:
      for sounds in self._allconfigs.values():
        for soundname in sounds.all():
          self._sounds_by_filename[soundname] = sounds
          self._allsoundfiles.append(soundname)

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
  def __init__(self, fileroot):
    # Most efficient way: two arrays in parallel?
    self._soundfiles, self._soundpaths = [], []
    for path, dirs, files in os.walk(fileroot):
      for filename in files:
        if re.search(r'\.(ogg|wav)$', filename):
          if filename in self._soundfiles:
            print("File {} found in {} but also in {}".format(filename, path, self._soundpaths[self._soundfiles.index(filename)]))
          self._soundfiles.append(filename)
          self._soundpaths.append(path)

  def getFilePath(self, filename):
    """Return the path of the first occurance of a filename"""
    idx = self._soundfiles.index(filename)
    return "{}/{}".format(self._soundpaths[idx], filename)

  def getDuplicates(self):
    dupes = {}
    for idx, filename in enumerate(self._soundfiles):
      if self._soundfiles.index(filename) != idx:
        if not filename in dupes:
          # Add the first instance from before we knew it was a dupe
          dupes[filename] = ["{}/{}".format(self._soundpaths[self._soundfiles.index(filename)], filename)]
        dupes[filename].append("{}/{}".format(self._soundpaths[idx], filename))
    return dupes

  def getFiles(self):
    return self._soundfiles

class ModeSounds(object):
  def __init__(self, modeName=None):
    self._dict = {}
    self._tracks = []
    self._files = []
    self._pool_tracks = {}
    self.name = modeName

  def parseConfig(self, modeConfig):
    if not modeConfig.get('sounds'):
      return self

    for sound_pool in modeConfig.get('sound_pools', {}).values():
      for soundname in Util.string_to_list(sound_pool['sounds']):
        if soundname in self._pool_tracks and self._pool_tracks[soundname] != sound_pool['track']:
          print("ERROR: Sound {} exists in multiple pools/tracks in config {}".format(soundname, self.name))
          return
        self._pool_tracks[soundname] = sound_pool['track']

    for soundname, sound in modeConfig['sounds'].items():
      self.addSound(sound, poolTrack=self._pool_tracks.get(soundname))

  def addSound(self, soundDict, poolTrack=None):
    fileName = soundDict['file']
    # If a track is explicitly defined, use it
    if 'track' in soundDict and soundDict['track']:
      trackName = soundDict['track']
    # If this sound is in a sound pool with a track, use that
    elif poolTrack:
      trackName = poolTrack
    # Mass Effect 2 Pinball defaults:
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

  def getSoundsForTrack(self, trackname):
    try:
      return self._dict[trackname]
    except(KeyError):
      print("ERROR: Mode {} has no track '{}'".format(self.name, trackname))
      return None

  def findTrackForSound(self, filename):
    for trackname, sounds in self._dict.items():
      if filename in sounds:
        return trackname

  def _addTrack(self, trackName):
    if not trackName in self._tracks:
      self._tracks.append(trackName)
      self._dict[trackName] = []

  def all(self):
    return self._files

  def byTrack(self):
    return self._dict

  def __repr__(self):
    return "<ModeSounds '{}': {} files>".format(self.name, len(self))

  def __len__(self):
    return len(self._files)


def interactive(soundManager):
  running = True
  while running:
    print("""
MPF Sound Asset Manager
===============================
  Machine Folder: {}
  Source Folder:  {}
===============================

  1. Analyze machine and audio

  2. Copy & prune assets

  3. Set media source folder

  4. Refresh configs and files

  0. Exit this program
""".format(os.getcwd(), soundManager.source_path))
    selection = input(">> ")
    if selection == "1" or selection == "2":
      writeMode = selection == "2"
      soundManager.cleanup_machine_assets(writeMode=writeMode)
    elif selection == "3":
      soundManager.set_source_path()
    elif selection == "4":
      soundManager.refresh()
    elif selection == "0" or not selection:
      running = False


def main():

  args = sys.argv[1:]
  verbose = "-v" in args
  writeMode = "-w" in args

  soundManager = SoundManager(verbose=verbose)

  if not soundManager.source_path:
    print("ERROR: Source media not found. Exiting.")
    return

  if not args or args[0] == "-i":
    interactive(soundManager)
    return

  if args:
    if args[0] == "prune":
      soundManager.parse_machine_assets(writeMode=writeMode)
      return
    elif args[0] == "copy":
      soundManager.cleanup_machine_assets(writeMode=writeMode)
      return


  print("""
---Mission Pinball Audio File Script---

Use this script to copy audio files from your source media folder into the
corresponding MPF Pinball mode folders.

For Mass Effect 2 Pinball, requires a data dump folder created by
Mass Effect 2 Extractor containing source audio folders and ogg files
(e.g. 'endgm2_longwalk_a_s_int', 'en_us_player_f_endgm2_escape_c_00287372_f.ogg')

For other projects, your mileage may vary. Contact mpf@anthonyvanwinkle.com
with any questions or feedback.

Options:
  copy  - Copy all audio files referenced in configs from the source folder
          to the appropriate modes/(name)/sounds/(track) folders

  prune - Remove all audio files from mode folders not referenced in config files
          and move any misplaced audio files to the correct mode folder

Params:
  path_to_sounds - Path to the folder containing all the source audio files

Flags:
  -v    - Verbose mode
  -w    - Write mode (actually copy/prune files)

Usage:
>> python mesound.py [prune|test|copy] <path_to_sounds> [-v|-w]
""")

if __name__ == "__main__":
  main()
