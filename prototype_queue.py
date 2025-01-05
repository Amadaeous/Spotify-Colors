from time import sleep
import random
import concurrent.futures
from queue import Queue
import threading

class APIExecutor:
    def __init__(self, n_ms):
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.task_queue = Queue()
        self.n_ms = n_ms / 1000  # Convert milliseconds to seconds
        self.running = False
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.daemon = True
        self.futures = set()

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def submit(self, func, *args, **kwargs):
        self.task_queue.put((func, args, kwargs))

    def _process_queue(self):
        while self.running:
            try:
                func, args, kwargs = self.task_queue.get(timeout=1)  # Adjust timeout as needed
                future = self.executor.submit(func, *args, **kwargs)
                self.futures.add(future)
                time.sleep(self.n_ms)
            except Queue.Empty:
                continue

    def get_futures(self):
        return self.futures


def example_task(x, kwargs):
    sleep(random.randint(500,2500)/1000)
    return x * x, kwargs


class DummyStorage:
    def store(self, anything, userid):
        sleep(0.1)
        print(f"stored {anything} for {userid}")


class DummyYanker:
    def __init__(self, userid):
        self.executor = APIExecutor(n_ms=500)
        self.storage = DummyStorage()
        self.userid = userid

    def yank(self):
        for i in range(5):
            self.executor.submit(example_task, i, self.userid)

        for future in concurrent.futures.as_completed(self.executor.get_futures()):
            self.storage.store(future.result(), self.userid)

        while not all(future.done() for future in self.executor.get_futures()):
            pass
        print("All tasks in api_executor completed.")


if __name__ == "__main__":
    n_users = 10
    users = [DummyYanker(i) for i in range(n_users)]
    [user.yank() for user in users]

    #user1 = DummyYanker(1)
    #user2 = DummyYanker(2)
    #user1.yank()
    #user2.yank()
