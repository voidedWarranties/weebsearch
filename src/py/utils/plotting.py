# utility functions for plotting
import matplotlib.pyplot as plt
import math
import cv2 as cv
import numpy as np
import utils.processing as proc

# create a color palette image
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

# get text and images to be plotted
def get_plot_data(res, img):
    hits, _, w_dists, w_scores, _, query_tags, rating = res

    titles = ["Query Image"]
    texts = [multiline(np.append([rating[0]], query_tags[:9]))]
    images = [img]
    for i, hit in enumerate(hits):
        path_trimmed = (hit["path"][:40] + "...") if len(hit["path"]) > 40 else hit["path"]
        titles.append("#{} {}".format(i + 1, path_trimmed))

        label = "ID: {}".format(hit["id"])
        label += "\nSearch Score: {}".format(hit["score"])
        label += "\nColor Difference: {}".format(math.floor(w_dists[i] * 1000) / 1000)
        label += "\nWeighted Score: {}".format(math.floor(w_scores[i] * 1000) / 1000)
        label += "\n" + multiline(hit["tags"][:10])
        texts.append(label)

        images.append(cv.imread(hit["path"]))
    
    return titles, texts, images

# plot results from cmd.search
def plot(im_path, res, save_loc=None):
    cv_img = None
    if isinstance(im_path, str):
        cv_img = cv.imread(im_path)
    else:
        cv_img = proc.bytes_to_mat(im_path)
    
    _, palettes, _, _, palette, _, _ = res
    titles, texts, images = get_plot_data(res, cv_img)

    palettes = [hist_mat(v) for v in np.append([palette], palettes, axis=0)]

    tile_images(images, palettes, titles, texts)
    
    plt.tight_layout()
    
    if save_loc:
        plt.savefig(save_loc, facecolor="lightgray")
    else:
        plt.show()

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

        color_plt = axarr[x + 1, y]
        color_plt.title.set_text(title)
        color_plt.imshow(palette)

    for x in range(width * 2):
        for y in range(width):
            axarr[x, y].axis("off")