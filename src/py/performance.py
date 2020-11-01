import time

# basic timer
class Performance:
    def __init__(self, should_print = True):
        self.should_print = should_print
        self.performance_times = {}
        self.elapsed_times = {}

    def begin_section(self, section):
        self.performance_times[section] = time.perf_counter()
        if self.should_print:
            print("==== {} ====".format(section), flush=True)

    def end_section(self, section):
        elapsed = time.perf_counter() - self.performance_times.pop(section)
        self.elapsed_times[section] = elapsed
        if self.should_print:
            print("{} took {} seconds".format(section, elapsed), flush=True)
            print("=" * (len(section) + 10), flush=True)
    
    def gen_report(self):
        report = []
        for key in self.elapsed_times:
            report.append("{} - {} seconds".format(key, self.elapsed_times[key]))
        
        self.elapsed_times = {}
        
        return "\n".join(report)