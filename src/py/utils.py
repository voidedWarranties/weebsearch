import numpy as np
import cv2 as cv
from sklearn.cluster import MiniBatchKMeans
import glob
import time
import os
from os import path
import math
import matplotlib.pyplot as plt

# convert array of tags to multiline string
def multiline(arr, line_len = 30):
    lines = []
    line = arr[0]
    sep = ", "
    for i, word in enumerate(arr[1:]):
        if len(line + sep + word) > line_len:
            lines.append(line + sep)
            line = word
        else:
            line += sep + word
    
    lines.append(line)
    
    return "\n".join(lines)

# plt keypress handler
def press(e):
    if e.key == "escape":
        plt.close("all")

def ensure_dir(dir_path):
    if not path.exists(dir_path):
        os.makedirs(dir_path)

def plot(im_path, res, save_loc=None):
    cv_img = None
    if not isinstance(im_path, str):
        np_raw = np.frombuffer(im_path, dtype="uint8")
        cv_img = cv.imdecode(np_raw, cv.IMREAD_COLOR)
    else:
        cv_img = cv.imread(im_path)
    
    hits, palettes, w_dists, palette, query_tags, rating = res

    titles = ["Query Image"]
    texts = [multiline(np.append([rating[0]], query_tags[:9]))]
    images = [cv_img]
    for i, hit in enumerate(hits):
        hit_path = (hit["path"][:40] + "...") if len(hit["path"]) > 40 else hit["path"]
        titles.append("#{} {}".format(i + 1, hit_path))
        label = "ID: {}".format(hit["id"])
        label += "\nSearch Score: {}".format(hit["score"])
        label += "\nColor Difference: {}".format(math.floor(w_dists[i] * 1000) / 1000)
        label += "\n" + multiline(hit["tags"][:10])
        texts.append(label)

        images.append(cv.imread(hit["path"]))

    palettes = [hist_mat(v) for v in np.append([palette], palettes, axis=0)]

    tile_images(images, palettes, titles, texts)
    
    for i in plt.get_fignums():
        plt.figure(i).canvas.mpl_connect("key_press_event", press)
    
    plt.tight_layout()
    
    if save_loc:
        plt.savefig(save_loc, facecolor="lightgray")
    else:
        plt.show()

# elasticsearch hit process
def hit_process(hit):
    out = hit["_source"]
    out["id"] = hit["_id"]
    out["score"] = hit["_score"]

    return out

# get file paths for image file
def get_paths(file):
    file = path.relpath(file, "library/")
    name = ".".join(file.split(".")[:-1])

    palette_path = "data/{}.colors.npy".format(name)
    tags_path = "data/{}.tags.txt".format(name)

    return palette_path, tags_path

# yields every file in `files`
# override: whether the check for all data files should be overriden
def iterate_library(files="library/*"):
    for im_file in glob.glob(files):
        if im_file.endswith(".npy") or im_file.endswith(".txt"):
            continue

        yield im_file

# https://www.compuphase.com/cmetric.htm
# palette: list of colors, palettes: list of list of colors - (-1, 4) r, g, b, probability
# calculates rgb differences between palette and each palette in palettes
def distances(palette, palettes):
    palettes = np.array(palettes)

    palette = palette[:,:-1]
    palettes = palettes[:,:,:-1]
    
    r1 = palette[:,0]
    r2 = palettes[:,:,0]
    
    r_bar = (r1 + r2) / 2

    coeff_r = 2 + r_bar / 256
    coeff_g = 4
    coeff_b = 2 + (255 - r_bar) / 256

    d_c = np.square(palettes - palette)
    d_c[:,:,0] *= coeff_r
    d_c[:,:,1] *= coeff_g
    d_c[:,:,2] *= coeff_b
    d_c = np.sum(d_c, axis=2)
    d_c = np.sqrt(d_c)

    return d_c

# uses kmeans to calculate a palette with probability information
# sorts by r, g, b values
def batch_hist(img):
    resized = cv.resize(img, (512, 512))
    resized_rgb = cv.cvtColor(resized, cv.COLOR_BGR2RGB)
    
    resized_colors = resized_rgb.reshape((-1, 3))

    clt = MiniBatchKMeans(n_clusters=8, batch_size=500, random_state=0).fit(resized_colors)

    labels = np.arange(0, len(clt.labels_) + 1)
    hist, _ = np.histogram(clt.labels_, bins = labels)

    hist = hist.astype("float32")
    hist /= hist.sum()

    hist = list(zip(hist, clt.cluster_centers_))
    hist.sort(key=lambda x: tuple(x[1]))

    palette = np.array(
        list(map(lambda x: np.append(x[1], [x[0]]), hist))
    )

    return palette

# creates a mat from histogram data from batch_hist
def hist_mat(hist):
    height = 1
    width = len(hist) * height * 3
    bar = np.zeros((height, width, 3), dtype = "uint8")
    startX = 0

    for r, g, b, percent in hist:
        endX = startX + width / len(hist)
        cv.rectangle(bar, (int(startX), 0), (int(endX), height), [int(r), int(g), int(b)], -1)
        startX = endX
    
    return bar

# create subplot from data
def tile_images(images, palettes, titles, texts):
    width = math.ceil(math.sqrt(len(images)))
    f, axarr = plt.subplots(width * 2, width, figsize=(20, 10))
    f.patch.set_facecolor("lightgray")

    for i, (img, palette, title, text) in enumerate(zip(images, palettes, titles, texts)):
        x = math.floor(i / width) * 2
        y = i % width

        factor = 256 / img.shape[1]
        img = cv.resize(img, (int(img.shape[1] * factor), int(img.shape[0] * factor)))
        img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        im_plt = axarr[x, y]
        im_plt.imshow(img_rgb)
        im_plt.text(1, 0, text, bbox=dict(facecolor="white", pad=2), size="x-small", transform=im_plt.transAxes)

        axarr[x + 1, y].title.set_text(title)
        axarr[x + 1, y].imshow(palette)

    for x in range(width * 2):
        for y in range(width):
            axarr[x, y].axis("off")

# weights distances in list of list of distances
# 0.5, 0.25, 0.125, etc
def weight(diffs):
    width = diffs.shape[1]
    weighted = 0.5 * diffs[:, 0]
    for i in range(1, width):
        weighted += (0.5 ** (i + 1)) * diffs[:,i]
    
    return weighted