"""Sound asset manager for MPF."""

from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip
from mpf.core.utility_functions import Util
from mpf import _version
import io
import logging
import os
import pickle
import re
import shutil
import sys
import tempfile
from datetime import datetime

# Requires: pysoundfile (via pip)
import soundfile as sf

README = """
ME2 Sound Manager
=================

Sound Manager automates the population of media assets into the mode folders of
a Mission Pinball game. It will copy new files, reorganized moved files, cleanup
unused files, and warn of missing and duplicated files.

Mass Effect 2 Pinball requires a data dump folder containing source audio files
extracted from Mass Effect 2. This folder can be generated by running this very
Sound Manager program in "extract" mode on an existing ME2 Pinball folder, or by
using a tool called Mass Effect 2 Extractor on the PC edition of the game.

Note: The full asset extraction requires a copy of Mass Effect 2 (PC only) and
            is ~1.7GB. This is recommended on your main development computer.
            The Sound Manager extraction is ~100MB and is designed for copying to
            low-storage pinball controllers (e.g. Raspberry, BeagleBone)

For other projects, your mileage may vary. Contact mpf@anthonyvanwinkle.com with
any questions or feedback.

Instructions:
-------------

1. Identify the location of your source media folder (where this file is). The
     Sound Manager remembers the last media folder path, so it's recommended to
     choose a permanent location and store future assets in that same folder.

2. From the ME2 root folder, run the following command:
            python mesound.py update

3. If you have not run Sound Manager before (or the previous media folder does
not exist), you will be prompted to enter the media folder location.

That's it!


Interactive Mode:
-----------------

You can run Sound Manager interactively with the following command:
            python mesound.py

Interactive mode contains the following features:

    1. Update Assets
            - The default function of Sound Manager. Will copy and move media files,
                remove unused files, and report any missing/duplicate assets.

    2. Analyze machine and audio
            - Read-only behavior. Performs the same analysis as the update routine,
                but does not write or delete any files.

    3. Set media source folder
            - Set or change the folder containing the Mass Effect 2 extracted audio
                files.

    4. Refresh configs and files
            - Reloads the MPF modes and configurations. Useful if Sound Manager is
                kept running while config changes are saved.

    5. Clear cached media source tree
            - Refreshes the source media files. For performance reasons, the source
                asset folder tree is cached. If any source assets are moved, renamed,
                or added, a refresh may be necessary.

                Note: On startup, Sound Manager will log whether it's referencing cached
                asset files or building a new cache.

"""

class SoundManager():
    """Master class for managing audio (and video) assets."""

    def __init__(self, verbose=False):
        """Initialize and find sources."""
        self.machine_configs = None
        self.machine_assets = None
        self.source_media = None
        self.source_path = None
        self._analysis = None
        self.cache_file_name = "mesound_cache"
        self.exports_folder = "./mesound_exports"
        self.conversion_root_folder = "./mesound_conversion"
        self.conversion_originals_folder = "{}/originals".format(self.conversion_root_folder)
        self.conversion_converted_folder = "{}/converted".format(self.conversion_root_folder)
        self.converted_media = None

        self.log = logging.getLogger()
        self.log.addHandler(logging.StreamHandler(sys.stdout))
        self.log.setLevel("DEBUG" if verbose else "INFO")
        self._get_source_path()

    def _get_cache_path(self):
        return os.path.join(tempfile.gettempdir(), self.cache_file_name)

    def _write_to_cache(self, data):
        with open(self._get_cache_path(), 'wb') as f:
            pickle.dump(data, f)

    def clear_cache(self):
        """Remove cached asset tree, if it exists."""
        try:
            os.remove(self._get_cache_path())
            self.log.info("Cache file removed")
        except Exception as e:
            self.log.warning("Unable to remove cache file: {}".format(e))

    def _load_machine_configs(self, refresh=False):
        if refresh or not self.machine_configs:
            self.log.info("  Loading config files...")
            self.machine_configs = RequiredSounds()

    def _load_source_media(self, refresh=False):
        self.log.info("  Looking for source media cache...")
        try:
            with open(self._get_cache_path(), 'rb') as f:
                self.source_media = pickle.load(f)
                stamp = os.path.getmtime(self._get_cache_path())
                self.log.info("    - Cache found from {}".format(
                              datetime.fromtimestamp(stamp).strftime("%b %d %Y %H:%M:%S")))
        except Exception as e:
            self.log.warning("    - Could not load cache file: {}".format(e))

        if refresh or not self.source_media:
            self.log.info("  Loading media files from source folder...")
            self.source_media = GameSounds(self.source_path)

            self.log.info("   - creating cache of source media...")
            self._write_to_cache(self.source_media)

        if refresh or not self.converted_media:
            try:
                os.stat(self.conversion_converted_folder)
                self.log.info("  Loading converted media files...")
                self.converted_media = GameSounds(self.conversion_converted_folder)
            except(FileNotFoundError):
                self.log.info("  No converted media files found.")

    def _load_machine_assets(self, refresh=False):
        if refresh or not self.machine_assets:
            self.log.info("  Loading assets from machine folder...")
            self.machine_assets = GameSounds("./", paths_to_exclude=[
                self.exports_folder, self.conversion_originals_folder, self.conversion_converted_folder])

    def refresh(self):
        """Re-traverse the configs and asset folders."""
        self._load_machine_configs(refresh=True)
        self._load_source_media(refresh=True)
        self._load_machine_assets(refresh=True)

    def set_source_path(self):
        """Define the path to look for media assets."""
        print("Set path to your media source folder:")
        rawpath = input(">> ").strip()
        # Store full paths, not relative
        if "~" in rawpath:
            root = os.environ.get('HOME') or os.environ.get('USERPROFILE')
            if not root:
                raise OSError("Unable to find home path in environment.")
            source_path = rawpath.replace("~", root)
        else:
            source_path = rawpath
        f = open("./.mesound_path", "w")
        f.write(source_path)
        f.close()
        self.clear_cache()
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

    def parse_machine_assets(self, write_mode=False, force_update=False):
        """Main method for mapping assets to config files and updating (if write-mode)."""
        self.log.info("\nMPF Sound Asset Manager [{}]".format("WRITE MODE" if write_mode else "READ-ONLY"))
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
            'misplaced': {},  # Key: expected file path; Value: current/wrong file path
            'orphaned': [],
            'duplicated': [],
            'sounds': {}  # Key: sound file name; Value: sound object
        }

        self.log.info("\nComparing current file tree to config assets:")

        dupes = self.machine_assets.get_duplicates()
        # First, look through all the files that exist in the mode folders to find orphaned, misplaced, and duplicate
        for __idx, filename in enumerate(self.machine_assets.get_files()):
            filepath = self.machine_assets.get_file_path(filename)
            mode = self.machine_configs.find_requiring_mode(filename)
            # If this file is not required by any configs
            if not mode:
                self._analysis['orphaned'].append(filepath)
            else:
                expectedpath = "./modes/{}/sounds/{}/{}".format(
                    mode.name, mode.find_track_for_sound(filename), filename)
                if filepath != expectedpath:
                    self.log.info("{} is in the wrong place. Expected {}".format(filepath, expectedpath))
                    self._analysis['misplaced'][expectedpath] = filepath
                elif filename in dupes:
                    # The expected path is for the ONE mode that legit requires this file
                    for dupepath in dupes[filename]:
                        if expectedpath != dupepath and dupepath not in self._analysis['duplicated']:
                            self._analysis['duplicated'].append(dupepath)
                else:
                    matchedfilescount += 1
                    self.log.debug("Matched {} in node {}".format(filename, mode.name))

        allconfigs = self.machine_configs.get_all_configs()

        for mode, modesounds in allconfigs.items():
            for track, sounds in modesounds.by_track().items():
                for sound in sounds:
                    if sound in self._analysis['sounds']:
                        print("ERROR: Sound file '{}' in mode {} also exists in mode {}".format(
                              sound, mode, self._analysis['sounds'][sound]['mode']))
                        return
                    modepath = "./modes/{}/sounds/{}/".format(self.machine_configs.get_mode_parent(mode), track)
                    sourcepath = None
                    exists = False
                    expectedpath = "{}{}".format(modepath, sound)
                    try:
                        # To force an update, don't "find" any files
                        if force_update:
                            raise FileNotFoundError
                        exists = os.stat(expectedpath)
                        self._analysis['found'].append(sound)
                    except(FileNotFoundError):
                        # Is this file misplaced? Are we planning on moving it?
                        if expectedpath in self._analysis['misplaced']:
                            pass
                        else:
                            self._analysis['missing'].append(sound)
                            try:
                                sourcepath = self.source_media.get_file_path(sound)
                                self._analysis['available'][expectedpath] = sourcepath
                            except(ValueError):
                                self._analysis['unavailable'].append(sound)

                    self._analysis['sounds'][sound] = {"mode": mode,
                                                       "modepath": modepath,
                                                       "sourcepath": sourcepath,
                                                       "exists": exists}

        self.log.info("  Found {} assets defined across {} config files.".format(
                      len(self._analysis['sounds']), len(allconfigs)))
        self.log.info("   - {} files correctly accounted for".format(
                      len(self._analysis['found'])))
        if self._analysis['misplaced']:
            self.log.info("   - {} misplaced files{}".format(
                          len(self._analysis['misplaced']), " will be moved" if write_mode else ""))
        if self._analysis['duplicated']:
            self.log.info("   - {} duplicate files{}".format(
                          len(self._analysis['duplicated']), " will be removed" if write_mode else ""))
        if self._analysis['orphaned']:
            self.log.info("   - {} orphaned files{}".format(
                          len(self._analysis['orphaned']), " will be removed" if write_mode else ""))
        if self._analysis['available']:
            self.log.info("   - {} missing files available {}".format(
                          len(self._analysis['available']), "and copied" if write_mode else "for copy"))
            for filename, sourcepath in self._analysis['available'].items():
                self.log.debug("    : {} -> {}".format(sourcepath, filename))
        if self._analysis['unavailable']:
            self.log.info("   - {} files missing and unavailable".format(
                          len(self._analysis['unavailable'])))

    def cleanup_machine_assets(self, write_mode=False, force_update=False):
        """Method to actually move/copy/delete asset files from MPF mode folders."""
        if not self._analysis:
            self.parse_machine_assets(write_mode=write_mode, force_update=force_update)

        files_changed = 0

        if self._analysis['orphaned']:
            self.log.info(("Removing {} orphaned files:" if write_mode else "{} orphaned files to remove").format(
                          len(self._analysis["orphaned"])))
            for orphan in self._analysis['orphaned']:
                self.log.info(" - {}".format(orphan))
                if write_mode:
                    os.remove(orphan)
                    files_changed += 1
        if self._analysis['duplicated']:
            self.log.info(("Removing {} duplicate files..." if write_mode else "{} duplicate files to remove").format(
                          len(self._analysis["duplicated"])))
            for orphan in self._analysis['duplicated']:
                self.log.info(" - {}".format(orphan))
                if write_mode:
                    os.remove(orphan)
                    files_changed += 1
        if self._analysis['misplaced']:
            self.log.info(("Moving {} misplaced files..." if write_mode else "{} misplaced files will be moved").format(
                          len(self._analysis["misplaced"])))
            for expectedpath, filepath in self._analysis['misplaced'].items():
                self.log.info(" - {} -> {}".format(filepath, expectedpath))
                if write_mode:
                    os.makedirs(expectedpath.rsplit("/", 1)[0], mode=0o755, exist_ok=True)
                    os.rename(filepath, expectedpath)
                    files_changed += 1
        if self._analysis['available']:
            self.log.info(("Copying {} new files..." if write_mode else "{} new files will be copied").format(
                          len(self._analysis["available"])))
            original_umask = os.umask(0)
            for idx, availitem in enumerate(self._analysis['available'].items()):
                dst = availitem[0]
                src = availitem[1]
                self.log.debug(" - {}/{}: {} -> {}".format(idx + 1, len(self._analysis['available']), src, dst))
                # Ensure the target directory exists
                if write_mode:
                    os.makedirs(dst.rsplit("/", 1)[0], mode=0o755, exist_ok=True)
                    shutil.copy2(src, dst)
                    files_changed += 1
            os.umask(original_umask)

        if self._analysis['unavailable']:
            self.log.info("\nWARNING: {} file{} could not be found:".format(
                          len(self._analysis['unavailable']), "" if len(self._analysis['unavailable']) == 1 else "s"))
            for filename in self._analysis['unavailable']:
                self.log.warning(" - {} ({})".format(filename, self._analysis['sounds'][filename]['mode']))

        # Any previous analysis is no longer valid
        if write_mode:
            videocount = self._copy_video_assets(export=False)
            self._analysis = None
            self.log.info("\nMachine copy and cleanup complete! {} audiofile{} and {} video file{} changed.".format(
                files_changed or "No",
                "" if files_changed == 1 else "s",
                videocount or "no",
                "" if videocount == 1 else "s"))
        else:
            self.log.info("\nSimulation complete, no files changed.")

    def export_machine_assets(self):
        """Batch output all assets within MPF folders to a single folder for compression/backup."""
        if not self._analysis:
            self.parse_machine_assets()

        os.makedirs(self.exports_folder, mode=0o755, exist_ok=True)
        count = 0
        size = 0

        for filename in self._analysis['found']:
            sound = self._analysis['sounds'][filename]
            path = "{}{}".format(sound['modepath'], filename)
            shutil.copy2(path, "{}/{}".format(self.exports_folder, filename))
            size += sound['exists'].st_size
            count += 1

        videocount = self._copy_video_assets(export=True)

        # Dump the readme too, to have instructions handy on the in-cabinet controller
        text = open("{}/_README.txt".format(self.exports_folder), mode="w")
        text.write(README)
        text.close()

        self.log.info("\nExport complete: {} audio files, {} MB (plus {} videos)".format(
                      count, round(size / 100000) / 10, videocount))

    def analyze_sample_rates(self, mode=None):
        """Assess all sound files to determine sample rates."""
        if not self._analysis:
            self.parse_machine_assets()
        if mode == "export":
            os.makedirs(self.conversion_originals_folder, mode=0o755, exist_ok=True)

        rates = {}
        mostCommonRate = None
        leastCommonFiles = []

        self.log.info("\nAnalyzing sample rates for {} files...".format(len(self._analysis['sounds'])))

        if mode != "import":
            for filename in self._analysis['found']:
                sound = self._analysis['sounds'][filename]
                path = "{}{}".format(sound['modepath'], filename)
                data, samplerate = sf.read(path)
                if samplerate not in rates:
                    rates[samplerate] = {"count": 0, "files": []}
                rates[samplerate]["count"] += 1
                rates[samplerate]["files"].append(path)

            self.log.info("\nAnalysis complete:")
            for rank, rankedRate in enumerate(sorted(rates.keys(), key=lambda x: rates[x]["count"], reverse=True)):
                self.log.info("  {}: {} files".format(rankedRate, rates[rankedRate]["count"]))
                if rank == 0:
                    mostCommonRate = rankedRate
                else:
                    leastCommonFiles += rates[rankedRate]["files"]

        if mode == "export":
            text = open("{}/RatesAnalysis.txt".format(self.conversion_root_folder), mode="w")
            text.write("\n".join(leastCommonFiles))
            text.close()
            self.log.info("\n{} files are not {} Hz, see mesound_conversions/RatesAnalysis.txt for details".format(
                len(leastCommonFiles), mostCommonRate))

            for filename in leastCommonFiles:
                shutil.copy2(filename, "{}/{}".format(self.conversion_originals_folder, filename.split("/").pop()))
            self.log.info("\n - Those files have been copied to {}".format(self.conversion_originals_folder))
            self.log.info(" - If you batch process them into {},\n".format(self.conversion_converted_folder) +
                          "   this program will import them to their correct mode folders")

        elif mode == "import":
            self.log.info("\nCopying converted files back into mode folders...")
            count = 0
            for filename in self.converted_media.get_files():
                source_path = "{}/{}".format(self.conversion_converted_folder, filename)
                sound = self._analysis['sounds'][filename]
                dest_path = "{}{}".format(sound['modepath'], filename)

                self.log.debug("{} -> {}".format(source_path, dest_path))
                # Make a backup of the original
                shutil.move(dest_path, re.sub(r'\.ogg$', '.original.ogg', dest_path))
                shutil.copy2(source_path, dest_path)
                count += 1
            self.log.info("Successfully copied {} converted files into their mode folders".format(count))

    def _copy_video_assets(self, export=True):
        videoroot = "./videos"
        exportroot = "{}/videos".format(self.exports_folder)
        count = 0

        if export:
            src = videoroot
            dst = exportroot
        else:
            src = exportroot
            dst = videoroot

        os.makedirs(dst, mode=0o755, exist_ok=True)
        for path, dirs, files in os.walk(src):
            for filename in files:
                if filename[0] == ".":
                    continue
                target = "{}/{}".format(dst, filename)
                # Always copy on export, but not import
                docopy = export
                try:
                    os.stat(target)
                except(FileNotFoundError):
                    docopy = True

                if docopy:
                    shutil.copy2("{}/{}".format(src, filename), target)
                    count += 1
        return count


class RequiredSounds(object):
    """Class object to parse, return, and query mode config files."""

    def __init__(self):
        """Initialize: create config mappings and walk config files."""
        self._allconfigs = {}  # Key: mode/config name, Value: ModeSounds object
        self._childconfigs = {}  # Key: mode/config name, Value: ModeSounds object
        self._sounds_by_filename = {}  # Key: array of filenames, Value: ModeSounds object
        self._source = None 
        self._allsoundfiles = []
        # Track modes that are imported into parent modes, so we don't scan them twice
        self._configparents = {}  # Key: child config name, Value: parent config

        loader_roundtrip = YamlRoundtrip()
        for path, __dirs, files in os.walk('modes'):
            for filename in files:
                if filename.endswith('.yaml'):
                    configfilename = filename[:-5]
                    with io.open('{}/{}'.format(path, filename), 'r', encoding='utf-8') as f:
                        source = f.read()
                    conf = loader_roundtrip.process(source)
                    sounds = ModeSounds(configfilename)
                    sounds.parse_config(conf)
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

    def get_all_configs(self):
        """Return all configs mapped by the MPF machine project."""
        return self._allconfigs

    def get_mode_parent(self, modename):
        """If the mode is a child mode, return the parents path."""
        return self._configparents.get(modename, modename)

    def find_requiring_mode(self, filename):
        """For a given asset filename, find the mode that includes that filename in its config file."""
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
        """Get the length of config files."""
        return len(self._allconfigs)


class GameSounds(object):
    """Class to traverse asset tree and return file information for assets in the MPF machine and mode folders."""

    def __init__(self, fileroot, paths_to_exclude=[]):
        """Initialize: traverse the asset files path and map asset filenames."""
        # Most efficient way: two arrays in parallel?
        self._soundfiles, self._soundpaths = [], []
        self._originalfiles, self._originalpaths = [], []
        for path, dirs, files in os.walk(fileroot):
            # Don't look in the exports folder!
            if path in paths_to_exclude:
                continue
            for filename in files:
                if re.search(r'\.(ogg|wav)$', filename):
                    if re.search(r'\.original\.ogg$', filename):
                        self._originalfiles.append(filename)
                        self._originalpaths.append(path)
                    else:
                        if filename in self._soundfiles:
                            print("File {} found in {} but also in {}".format(
                                  filename, path, self._soundpaths[self._soundfiles.index(filename)]))
                        self._soundfiles.append(filename)
                        self._soundpaths.append(path)

    def get_file_path(self, filename):
        """Return the path of the first occurance of a filename."""
        idx = self._soundfiles.index(filename)
        return "{}/{}".format(self._soundpaths[idx], filename)

    def get_duplicates(self):
        """Return a mapping of assets with filenames appearing in multiple mode folders."""
        dupes = {}
        for idx, filename in enumerate(self._soundfiles):
            if self._soundfiles.index(filename) != idx:
                if filename not in dupes:
                    # Add the first instance from before we knew it was a dupe
                    dupes[filename] = ["{}/{}".format(self._soundpaths[self._soundfiles.index(filename)], filename)]
                dupes[filename].append("{}/{}".format(self._soundpaths[idx], filename))
        return dupes

    def get_files(self):
        """Return the mapping of asset files to their containing mode folders."""
        return self._soundfiles


class ModeSounds(object):
    """Class to parse a mode's config file and find asset file definitions."""

    def __init__(self, mode_name=None):
        """Initialize."""
        self._dict = {}
        self._tracks = []
        self._files = []
        self._pool_tracks = {}
        self.name = mode_name

    def parse_config(self, mode_config):
        """Parse a yaml config file and create mappings for required assets."""
        if not mode_config.get('sounds'):
            return self

        for sound_pool in mode_config.get('sound_pools', {}).values():
            for soundname in Util.string_to_list(sound_pool['sounds']):
                if soundname in self._pool_tracks and self._pool_tracks[soundname] != sound_pool['track']:
                    print("ERROR: Sound {} exists in multiple pools/tracks in config {}".format(soundname, self.name))
                    return
                try:
                    self._pool_tracks[soundname] = sound_pool['track']
                except KeyError:
                    raise AttributeError("Sound pool '{}'' has no track".format(soundname))

        for soundname, sound in mode_config['sounds'].items():
            self._add_sound(sound, pool_track=self._pool_tracks.get(soundname))

    def _add_sound(self, sound_dict, pool_track=None):
        """Add a sound mapping for an asset file identified in the config."""
        filename = sound_dict['file']
        # If a track is explicitly defined, use it
        if 'track' in sound_dict and sound_dict['track']:
            trackname = sound_dict['track']
        # If this sound is in a sound pool with a track, use that
        elif pool_track:
            trackname = pool_track
        # Mass Effect 2 Pinball defaults:
        elif filename.startswith('en_us_'):
            trackname = 'voice'
        elif filename.startswith('mus_'):
            trackname = 'music'
        else:
            trackname = 'unknown'

        self._add_track(trackname)
        self._files.append(filename)
        self._dict[trackname].append(filename)

    def find_track_for_sound(self, filename):
        """Identify the track requested for the filename (to know its folder)."""
        for trackname, sounds in self._dict.items():
            if filename in sounds:
                return trackname

    def _add_track(self, trackname):
        if trackname not in self._tracks:
            self._tracks.append(trackname)
            self._dict[trackname] = []

    def all(self):
        """Return all the files in the config."""
        return self._files

    def by_track(self):
        """Return all the files mapped by their track name."""
        return self._dict

    def __repr__(self):
        """String repr."""
        return "<ModeSounds '{}': {} files>".format(self.name, len(self))

    def __len__(self):
        """Length is the number of files."""
        return len(self._files)


def interactive(manager):
    """Interactive shell mode."""
    running = True
    while running:
        print("""
MPF Sound Asset Manager
===============================
    Machine Folder: {}
    Source Folder:  {}
===============================

    1. Update assets (copy & prune)

    2. Analyze machine and audio

    3. Set media source folder

    4. Refresh configs and files

    5. Clear cached media source tree

    6. Export assets

    7. Analyze sample rates (takes time)

    8. Force refresh of all files

    0. Exit this program
""".format(os.getcwd(), manager.source_path))
        selection = input(">> ")
        if selection == "1" or selection == "2":
            write_mode = selection == "1"
            manager.cleanup_machine_assets(write_mode=write_mode)
        elif selection == "3":
            manager.set_source_path()
        elif selection == "4":
            manager.refresh()
        elif selection == "5":
            manager.clear_cache()
        elif selection == "6":
            manager.export_machine_assets()
        elif selection == "7":
            manager.analyze_sample_rates()
        elif selection == "8":
            manager.cleanup_machine_assets(write_mode=True, force_update=True)
        elif selection == "0" or not selection:
            running = False


def main():
    """Primary method: do something."""
    args = sys.argv[1:]
    verbose = "-v" in args
    write_mode = "-w" in args

    manager = SoundManager(verbose=verbose)

    if not manager.source_path:
        print("ERROR: Source media not found. Exiting.")
        return

    if not args or args[0] == "-i":
        interactive(manager)
        return

    if args:
        starttime = datetime.now()
        if args[0] == "parse":
            manager.parse_machine_assets(write_mode=write_mode)
        elif args[0] == "copy":
            manager.cleanup_machine_assets(write_mode=write_mode)
        elif args[0] == "update":
            manager.cleanup_machine_assets(write_mode=True)
        elif args[0] == "clear":
            manager.clear_cache()
        elif args[0] == "export":
            manager.export_machine_assets()
        elif args[0] == "convert":
            mode = "export" if "--export" in args else "import" if "--import" in args else None
            manager.analyze_sample_rates(mode=mode)
        endtime = datetime.now()
        manager.log.info("\nOperation complete in {:.2f} seconds".format((endtime - starttime).total_seconds()))

        return

    print("""
---Mission Pinball Audio File Script---

Use this script to copy audio files from your source media folder into the
corresponding MPF Pinball mode folders.

Options:
    update - Copy all audio files referenced in configs from the source folder
                     to the appropriate modes/(name)/sounds/(track) folders, and remove
                     all audio files not referenced in config files

    parse -  Print analysis of config files and source folder with summary of
                     files to move/copy/remove

    export - Export the asset files from the MPF mode folders to a single folder,
                     for quick setup on a machine without the complete Mass Effect 2
                     extraction folder (i.e. the in-cabinet pinball controller).

    clear -  Clear cached directory trees (for use when source media files change)

Params:
    path_to_sounds - Path to the folder containing all the source audio files

Flags:
    -v    - Verbose mode
    -w    - Write mode

Usage:
>> python mesound.py [copy|parse|clear] [<path_to_sounds>] [-v|-w]
""")


if __name__ == "__main__":
    main()
