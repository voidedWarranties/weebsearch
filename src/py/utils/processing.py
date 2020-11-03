# utility functions for processing
# (search & process)
import cv2 as cv
import numpy as np
from sklearn.cluster import MiniBatchKMeans
import random
import string
import six
import utils.processing as proc
from utils.db import Image

# generate images suitable for dan and opencv
# from a variable that could be a filepath or bytes
def images_from(path_or_bytes):
    if isinstance(path_or_bytes, str):
        cv_img = cv.imread(path_or_bytes)
        return cv_img, path_or_bytes

    cv_img = proc.bytes_to_mat(path_or_bytes)
    tf_img = six.BytesIO(path_or_bytes)
    return cv_img, tf_img

# generate a random string
def rand_id(n=16):
    s = string.digits
    return int(''.join(random.choice(s) for _ in range(n)))

# elasticsearch hit to output format
def hit_process(hit):
    out = hit["_source"]
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
    paths = list(map(lambda h: h["path"], hits))

    palettes = [] 
    for hit in hits:
        res = Image.select().where(Image.path == hit["path"])[0]
        palettes.append(res.colors)
    
    es_scores = list(map(lambda x: x["score"], hits))
    es_scores_norm = np.array(es_scores) / np.sum(es_scores)
    
    dists = distances(palette, palettes)
    w_dists = weight(dists)
    w_dists_norm = w_dists / np.sum(w_dists)

    w_scores = 130 * es_scores_norm - 30 * w_dists_norm

    sort = np.argsort(-w_scores)

    hits = np.array(hits)[sort]
    palettes = np.array(palettes)[sort]
    w_dists = w_dists[sort]
    w_scores = w_scores[sort]

    return hits, palettes, w_dists, w_scores

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