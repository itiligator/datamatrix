import asyncio
import base64
import shutil
import string
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
        self.country_code = 5

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

    def generate_km_code(self, iteration, k):
        # current_milliseconds = int((time.time() * 1000) % 1000)
        # gtin = f'{iteration:03}000{k:02}000{current_milliseconds:03}'
        gtin = "04680571061172"
        serial_number = ''.join(
            random.choices(string.ascii_letters + string.digits + "!@#$%^&*()_+={}\[\]:;\"'<>,.?/\\|`~\-", k=6))
        additional_code = ''.join(
            random.choices(string.ascii_letters + string.digits + "!@#$%^&*()_+={}\[\]:;\"'<>,.?/\\|`~\-", k=4))
        return base64.b64encode(
            f"01{gtin}21{self.country_code}{serial_number}\x1d93{additional_code}".encode('utf-8')).decode('utf-8')

    async def run(self):
        iteration = 0
        while True:
            iteration += 1
            codes = [self.generate_km_code(iteration, k) for k in range(1, self.max_count + 1)]
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
                        [self.max_count - 1, self.max_count - 2, self.max_count - 3, 0, 0, 0, 0])
                    subset = random.sample(codes, subset_length)
                elif i == self.total_codes_num:
                    subset = codes
                self.create_image(subset)
                await self.callback(subset)
