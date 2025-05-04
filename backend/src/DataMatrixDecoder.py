import base64
from asyncio import Queue
import shutil

import cv2
import numpy
import numpy as np
import asyncio
import logging
import logging.config

from .pylibdmtx import pylibdmtx

from backend.src.StatusObservable import StatusObservable
from backend.src.status import DatamatrixDecoderStatus

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "http",
            "stream": "ext://sys.stderr"
        }
    },
    "formatters": {
        "http": {
            "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    'loggers': {
        'httpx': {
            'handlers': ['default'],
            'level': 'ERROR',
        },
        'httpcore': {
            'handlers': ['default'],
            'level': 'ERROR',
        },
    }
}

logging.config.dictConfig(LOGGING_CONFIG)


class DataMatrixDecoder(StatusObservable):
    def __init__(self, url: str, max_count: int, timeout: int, callback):
        self.set_no_image_available_picture()
        super().__init__()
        self.max_count = max_count
        self.timeout = timeout
        self.callback = callback
        self.queue = Queue()
        self.status = DatamatrixDecoderStatus.INIT
        self.notify()
        self.max_errors_count = 3
        self.error_count = 0

        self.rtsp_url = url

        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    @staticmethod
    def set_no_image_available_picture():
        # copy no_image_available.jpg to region.jpg
        shutil.copyfile('no_image_available.jpg', 'region.jpg')

    @staticmethod
    def preprocess_frame(frame):
        """Улучшает контраст и удаляет блики перед декодированием."""
        # 1. Конвертация в grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Удаление бликов (adaptive thresholding)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Увеличение контраста (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        contrast = clahe.apply(thresh)

        # 4. Морфологическое закрытие для устранения шума
        kernel = np.ones((3, 3), np.uint8)
        processed = cv2.morphologyEx(contrast, cv2.MORPH_CLOSE, kernel)

        return processed

    def fetch_image(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                print("[Reconnecting] RTSP stream...")
                self.cap.release()
                self.cap = cv2.VideoCapture(self.rtsp_url)
            return frame
        except Exception as e:
            logging.error(f"Ошибка получения кадра: {e}")
            if self.error_count < self.max_errors_count:
                self.error_count += 1
            else:
                self.status = DatamatrixDecoderStatus.IMAGE_UNAVAILABLE
                self.notify()
                self.set_no_image_available_picture()
            return None

    async def image_producer(self):
        """Continuously fetch images and put them in the queue"""
        while True:
            try:
                if self.status not in (
                DatamatrixDecoderStatus.IMAGE_UNAVAILABLE, DatamatrixDecoderStatus.GENERAL_FAILURE):
                    self.status = DatamatrixDecoderStatus.FETCHING_IMAGE
                    self.notify()
                await asyncio.sleep(0.1)
                image = self.fetch_image()
                if image is not None:
                    self.status = DatamatrixDecoderStatus.OK
                    self.notify()
                    await self.queue.put(image)
                else:
                    await asyncio.sleep(1.0)
            except Exception as e:
                logging.exception(f"Ошибка получения картинки", exc_info=e)
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                self.set_no_image_available_picture()

    async def image_consumer(self):
        """Process images from the queue"""
        while True:
            try:
                image = await self.queue.get()
                # image = self.preprocess_frame(image)
                self.status = DatamatrixDecoderStatus.DECODING
                self.notify()
                decoded_messages_with_regions = self.decode_datamatrix(image)
                codes = [base64.b64encode(msg[0].data).decode('utf-8') for msg in decoded_messages_with_regions]
                image_size = image.shape[:2]
                for region in decoded_messages_with_regions:
                    coords = ()
                    for i in range(4):
                        coords += ((region[1][i][0], image_size[0] - region[1][i][1]),)
                    cv2.polylines(image, [numpy.array(coords)], True, (0, 255, 0), max(image_size) // 100)
                cv2.imwrite('region.jpg',
                            cv2.resize(image, (image_size[1] // 3, image_size[0] // 3), interpolation=cv2.INTER_AREA),
                            [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                await self.callback(codes)
                self.queue.task_done()
            except Exception as e:
                logging.error(f"Ошибка распознавания кодов: {e}")
                self.status = DatamatrixDecoderStatus.GENERAL_FAILURE
                self.notify()
                self.set_no_image_available_picture()
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
                self.set_no_image_available_picture()
                await asyncio.sleep(2)
