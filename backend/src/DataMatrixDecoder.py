import cv2
import numpy as np
import requests
import asyncio
from pylibdmtx import pylibdmtx
import logging

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
        self.status = DatamatrixDecoderStatus.INIT
        self.notify()

    async def fetch_image(self):
        try:
            response = requests.get(self.url, timeout=2)
            response.raise_for_status()
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
            self.status = DatamatrixDecoderStatus.OK
            return image
        except (requests.RequestException, cv2.error) as e:
            logging.error(f"Failed to fetch image: {e}")
            self.status = DatamatrixDecoderStatus.IMAGE_UNAVAILABLE
            self.notify()
            await asyncio.sleep(2)
            return None

    async def decode_datamatrix(self, image):
        return pylibdmtx.decode(image, shrink=self.shrink, timeout=self.timeout, max_count=self.max_count)

    async def run(self):
        while True:
            image = await self.fetch_image()
            if image is not None:
                self.status = DatamatrixDecoderStatus.DECODING
                self.notify()
                decoded_messages = await self.decode_datamatrix(image)
                codes = [msg.data.decode('utf-8') for msg in decoded_messages]
                await self.callback(codes)
                self.status = DatamatrixDecoderStatus.INIT
                self.notify()
            else:
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()