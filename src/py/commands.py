import utils.processing as proc
import numpy as np
import cv2 as cv
import elasticsearch
from utils.db import Image
import os

# search image library
def search(perf, es, evaluate, im_path, search_page=0):
    cv_img, tf_img = proc.images_from(im_path)

    if cv_img is None:
        return False

    perf.begin_section("query image processing")
    palette = proc.palette_hist(cv_img)
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

    hits = list(map(proc.hit_process, hits))

    perf.begin_section("color matching")
    hits, palettes, w_dists, w_scores = proc.color_sort(hits, palette)
    perf.end_section("color matching")

    return hits, palettes, w_dists, w_scores, palette, query_tags, rating

# process an image file
def process_file(evaluate, im_file):
    img = cv.imread(im_file)

    if img is None:
        return False, "invalid"

    existing = Image.select().where(Image.path == im_file).count()

    if existing > 0:
        return False, "dupe_path"

    palette = proc.palette_hist(img)
    tags_out, rating = evaluate(im_file)

    if rating[0] != "rating:safe":
        return False, "questionable"

    Image.create(
        id_=proc.rand_id(),
        path=im_file,
        colors=palette,
        tags=np.append([rating], tags_out, axis=0)
        )

    return True, "ok"

# initialize elastic index
def setup_elastic(es, clear):
    ingest = elasticsearch.client.IngestClient(es)

    if clear:
        es.indices.delete(index="anime", ignore=404)

        ingest_body = {
            "description": "Add timestamp",
            "processors": [
                {
                    "set": {
                        "field": "timestamp",
                        "value": "{{_ingest.timestamp}}"
                    }
                }
            ]
        }

        ingest.put_pipeline("timestamp", body=ingest_body)

    index_body = {
        "mappings": {
            "properties": {
                "path": {
                    "type": "text",
                    "analyzer": "keyword"
                },
                "id": {
                    "type": "long"
                }
            }
        }
    }

    es.indices.create(index="anime", ignore=400, body=index_body)

# index a file into elastic
def index_file(es, im_file):
    db_obj = None

    try:
        db_obj = Image.select().where(Image.path == im_file)[0]
    except IndexError as e:
        return False

    tags_out = list(map(lambda t: t[0], db_obj.tags))

    doc = {
        "path": im_file,
        "tags": tags_out,
        "id": db_obj.id_
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
            body=doc,
            pipeline="timestamp",
            id=db_obj.id_
        )
        return True

    return False

# delete a document
def delete(es, id_):
    id_ = int(id_)
    query = Image.select().where(Image.id_ == id_)[0]
    es.delete(index="anime", id=id_)
    os.remove(query.path)

    query.delete_instance()
    return query.path
