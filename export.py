"""Generate all pyc files in the proper folder tree.

This file must be run with a working directory of project root.
"""
import os
import subprocess
import sys
import shutil
import logging
import py_compile
from datetime import datetime
import hashlib
from functools import partial


try:
    import mpf
    from mpf.commands import build
    from mpf._version import __version__ as mpfversion
except ModuleNotFoundError as e:
    raise ModuleNotFoundError("Unable to find MPF. Please verify pypy or virtual environment.")
from custom_code.version_checker import REQUIRED_MPF_VERSION as me2version

DEST_PATH = "dist"
ASSET_FOLDERS = ("fonts", "images", "sounds", "videos")
EXPORT_PREFIX = "ME2UPDATE"
machine_path = "/home/pi/me2"


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger("GenerateCodeTree")


now = datetime.now()
timestamp = now.strftime("%y%m_%d_%H%M")

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
    for folder in ["custom_code", "modes"]:
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
    for folder in ["logs", "data", "config"]:
        path = os.path.join(DEST_PATH, folder)
        if not os.path.isdir(path):
            os.makedirs(path)
    # Special case: copy the FadeCandy config
    fcpath = "config/fadecandy.json"
    shutil.copyfile(fcpath, os.path.join(DEST_PATH, fcpath))
    log.info("Code tree generation complete")


def generate_hash(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    checksum = sha256_hash.hexdigest()
    log.debug("Checksum %s: %s", path, checksum)
    return checksum


def generate_update_file(package_list=None):
    with open(os.path.join(DEST_PATH, "UPDATE"), "w") as f:
        f.writelines([
            f"timestamp={now.strftime('%a %b %d %H:%M:S %Z %Y')}\n",
            f"version={timestamp.replace('_', '.')}\n",
            f"mpf_config.bundle={generate_hash(os.path.join(DEST_PATH, 'mpf_config.bundle'))}\n",
            f"mpf_mc_config.bundle={generate_hash(os.path.join(DEST_PATH, 'mpf_mc_config.bundle'))}\n"
        ])
        if package_list:
            f.write(
                f"packages={','.join(package_list)}\n"
            )

def make_zip():
    filename = f"{EXPORT_PREFIX}-{timestamp}"
    shutil.make_archive(filename, 'zip', DEST_PATH)
    return f"{filename}.zip"

def generate_packages():

    if not "-b" in sys.argv and not "-p" in sys.argv:
        return

    package_list = []
    package_dest_path = os.path.join(DEST_PATH, "packages")
    os.makedirs(package_dest_path)

    """Packages can be *built* with the -b argument, comma separated"""
    if "-b" in sys.argv:
        build_idx = sys.argv.index("-b")
        build_list = sys.argv[build_idx + 1].split(",")
        for b in build_list:
            # By default a wheel will be built, but another extension can be provided
            if "." in b:
                b, extension = b.split(".", 1)
            else:
                extension = ".whl"
            # Assume that the repos are in the parent root folder
            build_source_path = os.path.join("..", b)
            log.info("Building package modules %s at path %s", build_list, build_source_path)
            subprocess.check_call([sys.executable, "-m", "build", build_source_path])
            # Find the wheel
            build_dist_path = os.path.join(build_source_path, "dist")
            build_file = newest(build_dist_path, extension)
            log.info(" - found built module %s", build_file)
            build_filename = build_file.split("/")[-1]
            log.info(" - copying %s to %s", build_file, os.path.join(package_dest_path, build_filename))
            shutil.copyfile(build_file,
                            os.path.join(package_dest_path, build_filename))
            package_list.append(build_filename)

    """Packages can be entered with the -p argument, comma separated"""
    if "-p" in sys.argv:
        package_idx = sys.argv.index("-p")
        package_items = sys.argv[package_idx + 1].split(",")
        package_source_path = os.path.join("packages")
        package_dest_path = os.path.join(DEST_PATH, "packages")
        log.info("Bundling packages: %s", package_items)
        for p in package_items:
            shutil.copyfile(os.path.join(package_source_path, p),
                            os.path.join(package_dest_path, p))
            package_list.append(p)

    return package_list

def main():
    print(f'Found MPF version {mpfversion} and ME2 version {me2version}')
    if mpfversion != me2version:
        raise ValueError(f"Version mismatch! MPF {mpfversion} vs ME2 {me2version}")
    generate_tree()
    mpf_path = os.path.dirname(mpf.__file__)
    log.info("Generating production bundle at path %s", os.getcwd())
    build.Command([os.path.join(mpf_path, '__main__.py'),
                                'production_bundle',
                                '-c', 'config,production',
                                '--dest-path=%s' % machine_path], os.getcwd())

    for bundle in ("mpf_config.bundle", "mpf_mc_config.bundle"):
        shutil.copyfile(bundle, os.path.join(DEST_PATH, bundle))

    package_list = generate_packages()
    generate_update_file(package_list)

    # Check for a copy path
    if "-c" in sys.argv:
        copy_idx = sys.argv.index("-c")
        copy_path = sys.argv[copy_idx + 1]
        # Optionally remove all previous on the copy destination
        if "-r" in sys.argv:
            log.info("Looking for previous update files to delete from %s", copy_path)
            files_deleted = 0
            for __path, __dirs, files in os.walk(copy_path):
                for file in files:
                    if file.startswith(EXPORT_PREFIX):
                        os.remove(os.path.join(copy_path, file))
                        files_deleted += 1
            if files_deleted:
                log.info(" - Deleted %s previous update file%s from storage device.", files_deleted, "" if files_deleted==1 else "s")
            else:
                log.info(" - No previous update files found.")
        log.info("Compressing and copying to path %s", copy_path)
        filename = make_zip()
        shutil.copyfile(filename, os.path.join(copy_path, filename))
    elif "-z" in sys.argv:
        log.info("Compressing dist folder")
        make_zip()

def newest(path, extension):
    files = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in files if basename.endswith(extension)]
    return max(paths, key=os.path.getctime)

if __name__ == "__main__":
    if "-d" in sys.argv:
        d_idx = sys.argv.index("-d")
        machine_path = sys.argv[d_idx + 1]
    main()
