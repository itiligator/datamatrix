import asyncio
import logging

import sys
from backend.src.BoxMarker import BoxMarker
from backend.src.FtpPublisher import FTPPublisher
from backend.src.DataMatrixDecoder import DataMatrixDecoder


async def main():
    expected_num = 3
    ftp_publisher = FTPPublisher('localhost')
    marker = BoxMarker(ftp_publisher, expected_num)
    ftp_publisher.subscribe(marker)
    ftp_publisher.connect()
    decoder = DataMatrixDecoder(url='http://192.168.1.101:8080/photoaf.jpg', max_count=3, timeout=2000, shrink=2,
                                callback=marker.process_detected_codes)
    decoder.subscribe(marker)
    await decoder.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    asyncio.run(main())
