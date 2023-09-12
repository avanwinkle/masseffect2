"""Generate all pyc files in the proper folder tree.

This file must be run with a working directory of project root.
"""
import os
import sys
import shutil
import logging
import py_compile
from datetime import datetime

import mpf
from mpf.commands import build

DEST_PATH = "dist"
ASSET_FOLDERS = ("fonts", "images", "sounds", "videos")
machine_path = "/home/pi/me2"


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger("GenerateCodeTree")
log.setLevel(1)

def generate_tree():

    # Clear out the old build
    if os.path.isdir(DEST_PATH):
        shutil.rmtree(DEST_PATH)
    os.makedirs(DEST_PATH)

    log.info("Copying assets to build folder...")
    for folder in ASSET_FOLDERS:
        if os.path.isdir(folder):
            shutil.copytree(folder, os.path.join(DEST_PATH, folder))

    log.info("Generating code tree from project root %s...", os.getcwd())
    for folder in ["scriptlets", "modes"]:
        if os.path.isdir(os.path.join(DEST_PATH, folder)):
            shutil.rmtree(os.path.join(DEST_PATH, folder))
        base_path = folder
        for path, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".py"):
                    target_path = os.path.join(DEST_PATH, path)
                    target_file = os.path.join(target_path, file.replace(".py", ".pyc"))
                    log.debug(" - creating target path %s from path %s", target_path, path)
                    if not os.path.isdir(target_path):
                        os.makedirs(target_path)
                    py_compile.compile(os.path.join(path, file), target_file, optimize=2)
                    log.debug(" - saved %s", target_file)
            for dir in dirs:
                if dir in ASSET_FOLDERS:
                    log.debug("Found asset folder %s on path %s", dir, path)
                    source_path = os.path.join(path, dir)
                    dest_path = os.path.join(DEST_PATH, source_path)
                    shutil.copytree(source_path, dest_path)
    # Make sure we have logs and data folders
    for folder in ["logs", "data"]:
        path = os.path.join(DEST_PATH, folder)
        if not os.path.isdir(path):
            os.makedirs(path)
    log.info("Code tree generation complete")


def make_zip():
    now = datetime.now()
    filename = "ME2UPDATE-%s" % now.strftime("%y%m_%d_%H%M")
    shutil.make_archive(filename, 'zip', DEST_PATH)
    return os.path.join(f"{filename}.zip")


def main():
    generate_tree()
    mpf_path = os.path.dirname(mpf.__file__)
    log.info("Generating production bundle at path %s", os.getcwd())
    build.Command([os.path.join(mpf_path, '__main__.py'),
                                'production_bundle',
                                '-c', 'config,production',
                                '--dest-path=%s' % machine_path], os.getcwd())
    for bundle in ("mpf_config.bundle", "mpf_mc_config.bundle"):
        shutil.copyfile(bundle, os.path.join(DEST_PATH, bundle))
    log.info("Successfully built production bundles with machine path %s" % machine_path)

    # Check for a copy path
    if "-c" in sys.argv:
        copy_idx = sys.argv.index("-c")
        copy_path = sys.argv[copy_idx + 1]
        log.info("Compressing and copying to path %s", copy_path)
        z = make_zip()
        shutil.copyfile(z, os.path.join(copy_path, z))
        log.info("Copy complete!")
    elif "-z" in sys.argv:
        log.info("Compressing dist folder")
        z = make_zip()
        log.info("Successfully build %s" % z)


if __name__ == "__main__":
    if "-d" in sys.argv:
        d_idx = sys.argv.index("-d")
        machine_path = sys.argv[d_idx + 1]
    main()
