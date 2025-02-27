import base64
from asyncio import Queue

import cv2
import numpy as np
import requests
import asyncio
import logging

from .pylibdmtx import pylibdmtx
from requests.auth import HTTPDigestAuth

from backend.src.StatusObservable import StatusObservable
from backend.src.status import DatamatrixDecoderStatus


class DataMatrixDecoder(StatusObservable):
    def __init__(self, url: str, max_count: int, timeout: int, callback):
        super().__init__()
        self.url = url
        self.max_count = max_count
        self.timeout = timeout
        self.callback = callback
        self.queue = Queue()  # Limit queue size to prevent memory issues
        self.status = DatamatrixDecoderStatus.INIT
        self.notify()
        self.session = requests.Session()

    def fetch_image(self):
        try:
            # TODO: make it configurable
            response = self.session.get(self.url, timeout=2, auth=HTTPDigestAuth('admin', 'salek2025'))
            response.raise_for_status()
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
            self.status = DatamatrixDecoderStatus.OK
            return image
        except (requests.RequestException, cv2.error) as e:
            logging.error(f"Кадр недоступен по сети: {e}")
            self.status = DatamatrixDecoderStatus.IMAGE_UNAVAILABLE
            self.notify()
            return None

    async def image_producer(self):
        """Continuously fetch images and put them in the queue"""
        while True:
            try:
                if self.status != DatamatrixDecoderStatus.IMAGE_UNAVAILABLE:
                    self.status = DatamatrixDecoderStatus.FETCHING_IMAGE
                    self.notify()
                await asyncio.sleep(0.01)
                image = self.fetch_image()
                if image is not None:
                    self.status = DatamatrixDecoderStatus.OK
                    self.notify()
                    await self.queue.put(image)
                    await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(1.0)
            except Exception as e:
                logging.error(f"Ошибка получения картинки: {e}")
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                await asyncio.sleep(0.1)

    async def image_consumer(self):
        """Process images from the queue"""
        while True:
            try:
                await asyncio.sleep(0.01)
                image = await self.queue.get()
                self.status = DatamatrixDecoderStatus.DECODING
                self.notify()
                decoded_messages_with_regions = self.decode_datamatrix(image)
                codes = [base64.b64encode(msg[0].data).decode('utf-8') for msg in decoded_messages_with_regions]
                image_size = image.shape[:2]
                for region in decoded_messages_with_regions:
                    coords = ()
                    for i in range(4):
                        coords += ((region[1][i][0], image_size[0] - region[1][i][1]),)
                    cv2.polylines(image, [np.array(coords)], True, (0, 255, 0), max(image_size)//100)
                    cv2.imwrite('region.jpg', cv2.resize(image, (image_size[1]//3, image_size[0]//3), interpolation=cv2.INTER_AREA), [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                await self.callback(codes)
                await asyncio.sleep(0.01)
                self.queue.task_done()
            except Exception as e:
                logging.error(f"Ошибка распознавания кодов: {e}")
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                await asyncio.sleep(0.1)

    def decode_datamatrix(self, image):
        return pylibdmtx.decode_with_regions(image, timeout=self.timeout, max_count=self.max_count, max_edge=200)

    async def run(self):
        """Start both producer and consumer coroutines"""
        while True:
            try:
                await asyncio.gather(
                    self.image_producer(),
                    self.image_consumer()
                )
            except Exception as e:
                logging.error(f"Общая ошибка главного цикла: {e}")
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                await asyncio.sleep(2)
