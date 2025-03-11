import asyncio
import shutil
import time
from datetime import datetime
import random
import cv2

from backend.src.StatusObservable import StatusObservable
from backend.src.status import DatamatrixDecoderStatus


class DataMatrixDecoderMock(StatusObservable):
    def __init__(self, url: str, max_count: int, timeout: int, callback):
        super().__init__()
        self.max_count = max_count
        self.callback = callback
        self.status = DatamatrixDecoderStatus.INIT
        self.notify()
        self.empty_codes_num = 4
        self.total_codes_num = 10

    async def run(self):
        iteration = 0
        while True:
            iteration += 1
            current_time_string = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
            codes = [f"{iteration}_{k}_{current_time_string}" for k in range(1, self.max_count + 1)]
            for i in range(self.total_codes_num + 1):
                self.status = DatamatrixDecoderStatus.FETCHING_IMAGE
                self.notify()
                await asyncio.sleep(0.5)
                self.status = DatamatrixDecoderStatus.DECODING
                self.notify()
                await asyncio.sleep(0.2)
                subset = []
                if self.empty_codes_num < i < self.total_codes_num:
                    subset_length = random.choice(
                        [self.max_count, self.max_count - 1, self.max_count - 2, self.max_count - 3, 0])
                    subset = random.sample(codes, subset_length)
                elif i == self.total_codes_num:
                    subset = codes
                self.create_image(subset)
                await self.callback(subset)

            for i in range(self.total_codes_num + 1):
                self.status = DatamatrixDecoderStatus.FETCHING_IMAGE
                self.notify()
                await asyncio.sleep(0.5)
                self.status = DatamatrixDecoderStatus.DECODING
                self.notify()
                await asyncio.sleep(0.2)
                subset = []
                if self.empty_codes_num < i <= self.total_codes_num:
                    subset = [f"{iteration}_agg_{current_time_string}"]
                self.create_image(subset)
                await self.callback(subset)
