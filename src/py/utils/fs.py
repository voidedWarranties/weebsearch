# utility functions for filesystem
import os
from os import path
import glob

# yields every file in `files`
def iterate_library(files="library/*"):
    for im_file in glob.glob(files):
        if im_file.endswith(".npy") or im_file.endswith(".txt"):
            continue

        yield im_file

# create dir if it doesn't exist
def ensure_dir(dir_path):
    if not path.exists(dir_path):
        os.makedirs(dir_path)
