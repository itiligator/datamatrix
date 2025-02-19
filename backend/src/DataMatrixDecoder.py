import base64
from asyncio import Queue

import cv2
import numpy as np
import requests
import asyncio
import logging

from pylibdmtx import pylibdmtx
from pylibdmtx.wrapper import DmtxSymbolSize
from requests.auth import HTTPDigestAuth

from backend.src.StatusObservable import StatusObservable
from backend.src.status import DatamatrixDecoderStatus


class DataMatrixDecoder(StatusObservable):
    def __init__(self, url: str, max_count: int, timeout: int, shrink: int, callback):
        super().__init__()
        self.url = url
        self.max_count = max_count
        self.timeout = timeout
        self.shrink = shrink
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
                decoded_messages = self.decode_datamatrix(image)
                codes = [base64.b64encode(msg.data).decode('utf-8') for msg in decoded_messages]
                await self.callback(codes)
                await asyncio.sleep(0.01)
                self.queue.task_done()
            except Exception as e:
                logging.error(f"Ошибка распознавания кодов: {e}")
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                await asyncio.sleep(0.1)

    def decode_datamatrix(self, image):
        # TODO: make it configurable
        return pylibdmtx.decode(image, timeout=self.timeout, max_count=self.max_count,
                                shape=DmtxSymbolSize.DmtxSymbol22x22, deviation=5, threshold=40, min_edge=95,
                                max_edge=125)

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
