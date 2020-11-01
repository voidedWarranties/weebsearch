import argparse
from elasticsearch import Elasticsearch
from performance import Performance
from threads_procs import Processor, ResponseThread
import zmq
import signal
import utils.fs as fs
import utils.plotting as plotting
import commands as cmd

# disable logs
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

fs.ensure_dir("library")
fs.ensure_dir("data")

# globals
project_dir = "dan-model"
perf = Performance()

# initialize model and tag list
def setup_dan():
    import utils.dan as dan
    perf.begin_section("dan/tf init")
    evaluate = dan.setup_dan(project_dir)
    perf.end_section("dan/tf init")

    return evaluate

# elasticsearch
def setup_elastic():
    es = Elasticsearch()
    cmd.setup_elastic(es, args.clear)
    return es

# commands
def handle_process(res):
    evaluate = setup_dan()

    perf.begin_section("processing")
    for im_file in fs.iterate_library():
        cmd.process_file(evaluate, im_file)
        print(im_file)
    perf.end_section("processing")

def handle_index(res):
    es = setup_elastic()

    perf.begin_section("elastic indexing")
    for im_file in fs.iterate_library():
        cmd.index_file(es, im_file)
        print(im_file)
    perf.end_section("elastic indexing")

def handle_search(res):
    evaluate = setup_dan()
    es = setup_elastic()
    
    im_path = res.image
    res = cmd.search(perf, es, evaluate, im_path)

    if res:
        plotting.plot(im_path, res)

def handle_zmq(res):
    fs.ensure_dir("out")

    context = zmq.Context()
    socket = context.socket(zmq.ROUTER)
    socket.bind("tcp://*:6969")

    stdin_thread = Processor()
    stdin_thread.start()

    res_thread = ResponseThread(stdin_thread.out_q, socket)
    res_thread.start()

    while True:
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        identity = socket.recv()
        msg = socket.recv_string()
        stdin_thread.in_q.put([identity, msg])

if __name__ == "__main__":
    # parse args
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()

    process_parser = subs.add_parser("process")
    process_parser.set_defaults(func=handle_process)

    index_parser = subs.add_parser("index")
    index_parser.set_defaults(func=handle_index)

    search_parser = subs.add_parser("search")
    search_parser.add_argument("-i", "--image")
    search_parser.set_defaults(func=handle_search)

    zmq_parser = subs.add_parser("zmq")
    zmq_parser.set_defaults(func=handle_zmq)

    parser.add_argument("-c", "--clear", action="store_true")

    parser.add_argument("-p", "--path")

    args = parser.parse_args()

    args.func(args)
    