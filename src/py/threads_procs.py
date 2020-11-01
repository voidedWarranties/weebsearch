from multiprocessing import Process, Queue
import queue
from threading import Thread
import json
from performance import Performance
from os import path
import zmq
import base64
import commands as cmd

project_dir = "dan-model"

def data_process(zipped):
    out_arr = []
    for hit, palette, dist in zipped:
        out = hit
        out["palette"] = palette.tolist()
        out["dist"] = dist
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
    
    def process(self, line_split):
        command, identifier, im_file = line_split[:3]

        im_file = path.relpath(im_file)
        cmd.process_file(self.evaluate, im_file)

        return ">>{}$process${}".format(identifier, im_file)
    
    def index(self, line_split):
        command, identifier, im_file = line_split[:3]
        im_file = path.relpath(im_file)
        indexed = cmd.index_file(self.es, im_file)

        return ">>{}$index${}".format(identifier, 1 if indexed else 0)
    
    def search(self, line_split):
        command, identifier, im_file = line_split[:3]

        perf = Performance(False)

        im_bytes = base64.b64decode(im_file)

        search_page = 0
        try:
            search_page = line_split[4]
        except IndexError as e:
            pass
        
        res = cmd.search(perf, self.es, self.evaluate, im_bytes, int(search_page))

        if res:
            hits, palettes, w_dists, palette, query_tags, rating = res

            zipped = list(zip(hits, palettes, w_dists))
            processed = data_process(zipped)

            out_path = "out/{}.png".format(identifier)

            should_plot = True

            try:
                if line_split[3] == "0":
                    should_plot = False
            except IndexError as e:
                pass

            if should_plot:
                perf.begin_section("plotting")
                plotting.plot(im_bytes, res, out_path)
                perf.end_section("plotting")
            
            out_dict = {
                "palette": palette.tolist(),
                "query_tags": query_tags,
                "query_rating": rating[0],
                "results": processed,
                "performance": perf.gen_report()
            }

            out_json = json.dumps(out_dict)

            send_path = path.abspath(out_path) if should_plot else "*"

            return ">>{}$search${}${}".format(identifier, out_json, send_path)
        else:
            return ">>{}$search$failed".format(identifier)
    
    def run(self):
        import utils.dan as dan
        from elasticsearch import Elasticsearch
        
        self.evaluate = dan.setup_dan(project_dir)

        self.es = Elasticsearch()
        cmd.setup_elastic(self.es, False)

        while True:
            identity, line = self.in_q.get()
            line_split = line.split("$")
            command, identifier, im_file = line_split[:3]

            result = None

            if command == "process":
                result = self.process(line_split)
            elif command == "index":
                result = self.index(line_split)
            elif command == "search":
                result = self.search(line_split)
            
            self.out_q.put([identity, result])
