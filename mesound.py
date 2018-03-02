from mpf.core.config_processor import ConfigProcessor
from mpf.core.utility_functions import Util
import re
import os, sys
import shutil
import logging
from datetime import datetime

class SoundManager():
  def __init__(self, verbose=False):
    self.machine_configs = None
    self.machine_assets = None
    self.source_media = None
    self.source_path = None

    self._orphanedfiles = []
    self._misplacedfiles = []
    self._duplicatefiles = []

    self.log = logging.getLogger()
    self.log.addHandler(logging.StreamHandler(sys.stdout))
    self.log.setLevel("DEBUG" if verbose else "INFO")
    self._get_source_path()

  def _load_configs_for_source(self):
    if not self.machine_configs:
      self.log.info("Loading config files...")
      self.machine_configs = RequiredSounds()
    if not self.source_media:
      self.log.info("Loading media files from source folder...")
      self.source_media = GameSounds(self.source_path)
  
  def _load_configs_for_machine(self):
    if not self.machine_configs:
      self.log.info("Loading config files...")
      self.machine_configs = RequiredSounds()
    if not self.machine_assets:
      self.log.info("Loading assets from machine folder...")
      self.machine_assets = GameSounds("./")

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
        sourcepath = set_media_path()
    try:
      os.stat(sourcepath)
    except(FileNotFoundError):
      print("MPFSound requires a path to your source media folder.")
      print("Path not found: '{}'\nExiting...".format(sourcepath))
      sys.exit()
    self.source_path = sourcepath

  def parse_machine_assets(self, writeMode=False):
    self._load_configs_for_machine()
    matchedfilescount = 0

    dupes = self.machine_assets.getDuplicates()

    for idx, filename in enumerate(self.machine_assets.getFiles()):
      filepath = self.machine_assets.getFilePath(filename)
      mode = self.machine_configs.findRequiringMode(filename)
      # If this file is not required by any configs
      if not mode:
        self._orphanedfiles.append(filepath)
      else:
        expectedpath = "./modes/{}/sounds/{}/{}".format(mode.name, mode.findTrackForSound(filename), filename)
        if filepath != expectedpath:
          self.log.info("{} is in the wrong place. Expected {}".format(filepath, expectedpath))
          self._misplacedfiles.append((filepath, expectedpath))
        elif filename in dupes:
          # The expected path is for the ONE mode that legit requires this file
          for dupepath in dupes[filename]:
            if expectedpath != dupepath and not dupepath in self._duplicatefiles:
              self._duplicatefiles.append(dupepath)
        else:
          matchedfilescount += 1
          self.log.debug("Matched {} in node {}".format(filename, mode.name))
    self.log.info("Found {} required files, {} duplicate files, {} misplaced files, and {} orphaned files.\n".format(
          matchedfilescount, len(self._duplicatefiles), len(self._misplacedfiles), len(self._orphanedfiles)))
    self.cleanup_machine_assets(writeMode)

  def cleanup_machine_assets(self, writeMode=False):
    if (len(self._orphanedfiles) > 0):
      self.log.info("REMOVING ORPHANED FILES:" if writeMode else "ORPHANED FILES TO REMOVE:")
      for orphan in self._orphanedfiles:
        self.log.info("- {}".format(orphan))
        if writeMode:
          os.remove(orphan)
    if (len(self._duplicatefiles) > 0):
      self.log.info("REMOVING DUPLICATE FILES:" if writeMode else "DUPLICATE FILES TO REMOVE:")
      for orphan in self._duplicatefiles:
        self.log.info("- {}".format(orphan))
        if writeMode:
          os.remove(orphan)
    if (len(self._misplacedfiles) > 0):
      self.log.info("MOVING MISPLACED FILES:" if writeMode else "MISPLACED FILES TO MOVE:")
      for filepath, expectedpath in self._misplacedfiles:
        self.log.info(" {} -> {}".format(filepath, expectedpath))
        if writeMode:
          os.rename(filepath, expectedpath)

  def match_configs_to_source(self, writeMode=False):
    self._load_configs_for_source()
    soundCheck = {}
    allconfigs = self.machine_configs.getAllConfigs()
    counts = { 'found': [], 'missing': [], 'available': [], 'unavailable': [] }
    
    for mode, modesounds in allconfigs.items():
      for track, sounds in modesounds.byTrack().items():
        for sound in sounds:
          if sound in soundCheck:
            print("ERROR: Sound file '{}'' in mode {} also exists in mode {}".format(
                  sound, mode, soundCheck[sound]['mode']))
            return
          modepath = "modes/{}/sounds/{}/".format(self.machine_configs.getModeParent(mode), track)
          gamepath = None
          exists = False
          try:
            exists = os.stat("{}{}".format(modepath, sound))
            counts['found'].append(sound)
          except(FileNotFoundError):
            counts['missing'].append(sound)
            try:
              gamepath = self.source_media.getFilePath(sound)
              counts['available'].append(sound)
            except(ValueError):
              counts['unavailable'].append(sound)

          soundCheck[sound] = { "mode": mode, "modepath": modepath, "gamepath": gamepath, "exists": exists}
          if mode != self.machine_configs.getModeParent(mode):
            print(soundCheck[sound])
    available = len(counts['available'])

    if writeMode:
      print("\n{} {} files into modes:".format("Copying" if writeMode else "Simulating copy of", available))
      print("--------------------------------------------")
      original_umask = os.umask(0)
      for idx, filename in enumerate(counts['available']):
        src = soundCheck[filename]['gamepath']
        dst = soundCheck[filename]['modepath']
        print(" {}/{}: {} -> {}".format(idx+1, available, src, dst))
        os.makedirs(dst, mode=0o774, exist_ok=True)
        shutil.copy2(src, dst)
      os.umask(original_umask)

    self.log.info("Found {} assets defined across {} config files.".format(len(soundCheck), len(allconfigs)))
    self.log.info(" - {} files accounted for".format(len(counts['found'])))
    self.log.info(" - {} missing files available {}".format(available, "and copied" if writeMode else "for copy"))
    self.log.debug("    : {} -> {}".format(
                   ("/").join(soundCheck[filename]['gamepath'].split("/")[-2:]), soundCheck[filename]['modepath'])
                   for filename in counts['available'])
    if (len(counts['unavailable']) > 0):
      self.log.info(" - {} files missing and unavailable:".format(len(counts['unavailable'])))
      for filename in counts['unavailable']:
        self.log.info("    : {} ({})".format(filename, soundCheck[filename]['mode']))


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
          conf = ConfigProcessor.load_config_file('{}/{}'.format(path,filename), "mode")
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
    return "{}/{}".format(self._soundpaths[idx], self._soundfiles[idx])

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
  0. Exit this program

""".format(os.getcwd(), soundManager.source_path))
    selection = input(">> ")
    if selection == "1" or selection == "2":
      writeMode = selection == "2"
      soundManager.parse_machine_assets(writeMode=writeMode)
      soundManager.match_configs_to_source(writeMode=writeMode)
    elif selection == "3":
      soundManager.set_source_path()
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
      soundManager.match_configs_to_source(writeMode=writeMode)
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
