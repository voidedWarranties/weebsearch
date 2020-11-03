from multiprocessing import Process, Queue
import queue
from threading import Thread
import json
from performance import Performance
from os import path
import zmq
import base64
import commands as cmd
import utils.plotting as plotting
from operator import itemgetter

project_dir = "dan-model"

def data_process(zipped):
    out_arr = []
    for hit, palette, dist, w_score in zipped:
        out = hit
        out["palette"] = palette.tolist()
        out["dist"] = dist
        out["w_score"] = w_score
        out_arr.append(out)
    
    return out_arr

class ResponseThread(Thread):
    def __init__(self, out_q, sock):
        super(ResponseThread, self).__init__(daemon=True)

        self.out_q = out_q
        self.sock = sock
    
    def run(self):
        while True:
            identity, line = self.out_q.get()
            self.sock.send(identity, zmq.SNDMORE)
            self.sock.send_string(line)

class Processor(Process):
    def __init__(self):
        super(Processor, self).__init__(daemon=True)
        self.in_q = Queue()
        self.out_q = Queue()
    
    def process(self, im_file):
        im_file = path.relpath(im_file)
        success, msg = cmd.process_file(self.evaluate, im_file)

        return {
            "file": im_file,
            "success": success,
            "msg": msg
        }
    
    def index(self, im_file):
        im_file = path.relpath(im_file)
        indexed = cmd.index_file(self.es, im_file)

        return {
            "indexed": indexed
        }
    
    def search(self, im_file, query):
        perf = Performance(False)

        im_bytes = base64.b64decode(im_file)

        search_page = 0
        try:
            search_page = query["page"]
        except KeyError as e:
            pass
        
        res = cmd.search(perf, self.es, self.evaluate, im_bytes, int(search_page))

        if res:
            hits, palettes, w_dists, w_scores, palette, query_tags, rating = res

            zipped = list(zip(hits, palettes, w_dists, w_scores))
            processed = data_process(zipped)

            should_plot = True

            try:
                if not query["plot"]:
                    should_plot = False
            except KeyError as e:
                pass
                
            plt_bytes = None

            if should_plot:
                perf.begin_section("plotting")
                plt_bytes = plotting.plot(im_bytes, res, True)
                perf.end_section("plotting")
            
            out_dict = {
                "palette": palette.tolist(),
                "query_tags": query_tags,
                "query_rating": rating[0],
                "results": processed,
                "performance": perf.gen_report()
            }

            send_img = base64.b64encode(plt_bytes).decode("utf-8") if should_plot else "*"

            return {
                "data": out_dict,
                "plot": send_img,
                "success": True
            }
        
        return {
            "success": False
        }
    
    def run(self):
        import utils.dan as dan
        from elasticsearch import Elasticsearch
        
        self.evaluate = dan.setup_dan(project_dir)

        self.es = Elasticsearch()
        cmd.setup_elastic(self.es, False)

        while True:
            identity, line = self.in_q.get()

            try:
                query = json.loads(line)
                command = query["cmd"]
                im_file = query["file"]

                result = None

                if command == "process":
                    result = self.process(im_file)
                elif command == "index":
                    result = self.index(im_file)
                elif command == "search":
                    result = self.search(im_file, query)
                
                if result is not None:
                    result["id"] = query["id"]
                    result["cmd"] = command

                    self.out_q.put([identity, json.dumps(result)])
            except (json.decoder.JSONDecodeError, KeyError) as e:
                pass
