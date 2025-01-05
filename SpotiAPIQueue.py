import threading
from concurrent.futures import ThreadPoolExecutor
import ratelimitqueue
from queue import Empty


class SpotiAPIQueue:
    class APIError(Exception):
        ERROR_MESSAGES = {
            401: "Bad or expired token",  # Refresh auth
            403: "Bad OAuth request",  # Reauth will not help
            429: "The app has exceeded its rate limits",  # Slow down
        }

        def __init__(self, status_code: int):
            self.status_code = status_code
            self.message = self.ERROR_MESSAGES.get(
                status_code, f"An error occurred with status code: {status_code}")
            super().__init__(self.message)

    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def get_instance():
        if SpotiAPIQueue._instance is None:
            with SpotiAPIQueue._lock:
                if SpotiAPIQueue._instance is None:
                    SpotiAPIQueue._instance = SpotiAPIQueue()
        return SpotiAPIQueue._instance

    @staticmethod
    def reset_instance():
        with SpotiAPIQueue._lock:
            if SpotiAPIQueue._instance is not None:
                SpotiAPIQueue._instance.shutdown()
                SpotiAPIQueue._instance = None

    def __init__(self, calls: int = 2, per: float = .5, num_workers: int = 4):
        if SpotiAPIQueue._instance is not None:
            raise Exception("Es un Singleton bro")

        self.queue = ratelimitqueue.RateLimitQueue(calls=calls, per=per)
        self.num_workers = num_workers
        self.shutdown_flag = False
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)
        self.start_workers()

    def start_workers(self):
        for _ in range(self.num_workers):
            self.executor.submit(self.worker, self.queue)

    def worker(self, rlq: ratelimitqueue.RateLimitQueue):
        """Processes items from the queue until it is empty."""
        while True:
            try:
                user_id, func, args, kwargs, callback = rlq.get(timeout=1)
                if func is None:  # Shutdown signal
                    print(
                        f"Worker {threading.current_thread().name} received shutdown signal")
                    rlq.task_done()
                    break
                print(
                    f"Worker {threading.current_thread().name} processing request for user {user_id}")
                try:
                    response = func(*args, **kwargs)
                    if callback:
                        callback(user_id, response)
                except Exception as e:
                    print(f"Error processing request for user {user_id}: {e}")
                    rlq.task_done()
                finally:
                    rlq.task_done()
                    print(
                        f"Worker {threading.current_thread().name} finished request for user {user_id}")
            except Empty:
                if self.shutdown_flag:
                    break

    def enqueue_request(self, user_id: str, func, args: tuple, kwargs: dict, callback=None):
        print(f"Enqueuing request for user {user_id}")
        self.queue.put((user_id, func, args, kwargs, callback))

    def is_queue_empty(self):
        return self.queue.empty()

    def shutdown(self):
        if not self.shutdown_flag:
            print("Initiating shutdown")
            self.shutdown_flag = True
            # Send shutdown signals to all worker threads
            for _ in range(self.num_workers):
                self.queue.put((None, None, None, None, None))
            # Wait for all tasks to be completed
            self.queue.join()
            # Shut down the thread pool
            self.executor.shutdown(wait=True)
            print("All worker threads have been shut down and cleared")
