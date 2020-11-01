import utils
from os import path
import numpy as np
import cv2 as cv
import six

# search image library
def search(perf, es, evaluate, im_path, search_page=0):
    cv_img = None
    tf_img = None

    if isinstance(im_path, str):
        cv_img = cv.imread(im_path)
        tf_img = im_path
    else:
        np_raw = np.frombuffer(im_path, dtype="uint8")
        cv_img = cv.imdecode(np_raw, cv.IMREAD_COLOR)
        tf_img = six.BytesIO(im_path)
    
    perf.begin_section("query image processing")
    palette = utils.batch_hist(cv_img)
    perf.end_section("query image processing")

    perf.begin_section("query tag processing")
    tags_out, rating = evaluate(tf_img)
    query_tags = list(map(lambda x: x[0], tags_out))
    perf.end_section("query tag processing")

    perf.begin_section("elasticsearch")

    page_size = 24
    search_from = 0
    if search_page != 0:
        search_from = page_size * search_page + 1

    query = {
        "size": 24,
        "from": page_size * search_page,
        "query": {
            "multi_match": {
                "query": " ".join(query_tags),
                "fields": ["tags"]
            }
        }
    }

    res = es.search(index="anime", body=query)
    perf.end_section("elasticsearch")

    hits = res["hits"]["hits"]
    if len(hits) < 1:
        return False

    hits = list(map(utils.hit_process, hits))

    palettes = []
    
    for hit in hits:
        palette_path, _ = utils.get_paths(hit["path"])

        if path.exists(palette_path):
            palettes.append(np.load(palette_path))
    
    perf.begin_section("color matching")
    dists = utils.distances(palette, palettes)
    w_dists = utils.weight(dists)
    sort = np.argsort(w_dists)
    perf.end_section("color matching")

    hits = np.array(hits)[sort]
    palettes = np.array(palettes)[sort]
    w_dists = w_dists[sort]

    return hits, palettes, w_dists, palette, query_tags, rating

# process an image file
def process_file(evaluate, im_file):
    palette_path, tags_path = utils.get_paths(im_file)

    if not path.exists(palette_path):
        palette = utils.batch_hist(cv.imread(im_file))
        np.save(palette_path, palette)
    
    if not path.exists(tags_path):
        tags_out, rating = evaluate(im_file)

        out = " ".join(rating)
        for tag in tags_out:
            out += "\n" + " ".join(tag)
        
        with open(tags_path, "w") as f:
            f.write(out)

# initialize elastic index
def setup_elastic(es, clear):
    if clear:
        es.indices.delete(index="anime", ignore=404)
    
    index_body = {
        "mappings": {
            "properties": {
                "path": {
                    "type": "text",
                    "analyzer": "keyword"
                }
            }
        }
    }

    es.indices.create(index="anime", ignore=400, body=index_body)

# index a file into elastic
def index_file(es, im_file):
    _, tags_path = utils.get_paths(im_file)

    if not path.exists(tags_path):
        return

    tags_out = []

    with open(tags_path, "r") as f:
        content = [x.strip() for x in f.readlines()]
        
        for line in content:
            tag, confidence = line.split(" ")
            tags_out.append(tag)
    
    doc = {
        "path": im_file,
        "tags": tags_out
    }

    res = es.count(index="anime", body={
        "query": {
            "term": {
                "path": im_file
            }
        }
    })

    if not res["count"]:
        es.index(
            index="anime",
            body=doc
        )
        return True
    
    return False