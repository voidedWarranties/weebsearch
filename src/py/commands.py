import utils.processing as proc
import utils.fs as fs
from os import path
import numpy as np
import cv2 as cv
import six
import elasticsearch

# search image library
def search(perf, es, evaluate, im_path, search_page=0):
    cv_img = None
    tf_img = None

    if isinstance(im_path, str):
        cv_img = cv.imread(im_path)
        tf_img = im_path
    else:
        cv_img = proc.bytes_to_mat(im_path)
        tf_img = six.BytesIO(im_path)
    
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
    hits, palettes, w_dists = proc.color_sort(hits, palette)
    perf.end_section("color matching")

    return hits, palettes, w_dists, palette, query_tags, rating

# process an image file
def process_file(evaluate, im_file):
    palette_path, tags_path = fs.get_paths(im_file)

    if not path.exists(palette_path):
        palette = proc.palette_hist(cv.imread(im_file))
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
                }
            }
        }
    }

    es.indices.create(index="anime", ignore=400, body=index_body)

# index a file into elastic
def index_file(es, im_file):
    _, tags_path = fs.get_paths(im_file)

    if not path.exists(tags_path):
        return

    tags_out = []

    with open(tags_path, "r") as f:
        content = [x.strip() for x in f.readlines()]
        
        for line in content:
            tag, confidence = line.split(" ")
            tags_out.append(tag)
    
    tb_id = proc.rand_id()
    
    doc = {
        "path": im_file,
        "tags": tags_out,
        "id": tb_id
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
            id=tb_id
        )
        return True
    
    return False