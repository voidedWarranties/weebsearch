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

# get file paths for image file
def get_paths(file):
    file = path.relpath(file, "library/")
    name = ".".join(file.split(".")[:-1])

    palette_path = "data/{}.colors.npy".format(name)
    tags_path = "data/{}.tags.txt".format(name)

    return palette_path, tags_path