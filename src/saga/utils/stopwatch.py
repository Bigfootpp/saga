import time
from typing import Self


class Stopwatch:
    def __init__(self) -> None:
        self.paused = False
        self.accumulated_time = 0.0
        self.start_time = time.perf_counter()

    def pause(self):
        if self.paused:
            return
        self.accumulated_time += time.perf_counter() - self.start_time
        self.paused = True

    def resume(self):
        if not self.paused:
            return
        self.start_time = time.perf_counter()
        self.paused = False

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pause()

    @property
    def time(self) -> float:
        if self.paused:
            return self.accumulated_time
        else:
            return self.accumulated_time + (time.perf_counter() - self.start_time)
