import threading
import time


class WorkerThread(threading.Thread):
    def run(self, *args, **kwargs):
        while True:
            print('Hello')
            time.sleep(1)