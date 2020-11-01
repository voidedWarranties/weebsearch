# utility functions for processing
# (search & process)
import cv2 as cv
import numpy as np
from sklearn.cluster import MiniBatchKMeans
import utils.fs as fs
from os import path
import random
import string

# generate a random string
def rand_id(n=16):
    s = string.ascii_letters + string.digits
    return ''.join(random.choice(s) for _ in range(n))

# elasticsearch hit to output format
def hit_process(hit):
    out = hit["_source"]
    out["id"] = hit["_id"]
    out["score"] = hit["_score"]

    return out

# convert bytes (usu. from base64) to an opencv image
def bytes_to_mat(data):
    np_raw = np.frombuffer(data, dtype="uint8")
    cv_img = cv.imdecode(np_raw, cv.IMREAD_COLOR)

    return cv_img

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

# weights distances in list of list of distances
# 0.5, 0.25, 0.125, etc
def weight(diffs):
    width = diffs.shape[1]
    weighted = 0.5 * diffs[:, 0]
    for i in range(1, width):
        weighted += (0.5 ** (i + 1)) * diffs[:,i]
    
    return weighted

# sort hits based on distance between palettes and
# reference palette
def color_sort(hits, palette):
    palettes = []
    
    for hit in hits:
        palette_path, _ = fs.get_paths(hit["path"])

        if path.exists(palette_path):
            palettes.append(np.load(palette_path))
    
    dists = distances(palette, palettes)
    w_dists = weight(dists)
    sort = np.argsort(w_dists)

    hits = np.array(hits)[sort]
    palettes = np.array(palettes)[sort]
    w_dists = w_dists[sort]

    return hits, palettes, w_dists

# generates palette from histogram and clusters
def gen_palette(hist, clusters):
    palette = []
    for i, (r, g, b) in enumerate(clusters):
        palette.append([r, g, b, hist[i]])
    
    palette.sort(key=lambda c: tuple(c[:3]))

    return np.array(palette)

# uses kmeans to calculate a palette with probability information
# sorts by r, g, b values
# returns vector with shape (k, 4) where each row is r, g, b, %
def palette_hist(img):
    resized = cv.resize(img, (512, 512))
    resized_rgb = cv.cvtColor(resized, cv.COLOR_BGR2RGB)
    
    resized_colors = resized_rgb.reshape((-1, 3))

    clt = MiniBatchKMeans(n_clusters=8, batch_size=500, random_state=0).fit(resized_colors)

    labels = np.arange(0, len(clt.labels_) + 1)
    hist, _ = np.histogram(clt.labels_, bins=labels, density=True)

    hist = hist.astype("float32")
    palette = gen_palette(hist, clt.cluster_centers_)

    return palette