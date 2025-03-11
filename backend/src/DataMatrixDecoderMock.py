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
        self.empty_codes_num = 2
        self.total_codes_num = 8
        self.set_no_image_available_picture()
        # wait for 1 second without asyncio
        time.sleep(3)

    @staticmethod
    def set_no_image_available_picture():
        # copy no_image_available.jpg to region.jpg
        shutil.copyfile('no_image_available.jpg', 'region.jpg')

    @staticmethod
    def create_image(codes):
        image = cv2.imread("no_image_available.jpg")
        for idx, code in enumerate(codes):
            cv2.putText(image, code, (10, 100 + idx * 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)
        cv2.imwrite('region.jpg', image)

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
                # random choice between 0 and 1 with 1 probability of 0.7
                if self.empty_codes_num < i <= self.total_codes_num and random.random() < 0.7:
                    subset = [f"{iteration}_agg_{current_time_string}"]
                self.create_image(subset)
                await self.callback(subset)
