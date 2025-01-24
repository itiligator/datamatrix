import asyncio
import logging
import sys
import argparse
from backend.src.BoxMarker import BoxMarker
from backend.src.FtpPublisher import FTPPublisher
from backend.src.DataMatrixDecoder import DataMatrixDecoder


def parse_args():
    parser = argparse.ArgumentParser(description='Запуск приложения с параметрами.')
    parser.add_argument('--url', type=str, required=True, help='URL для получения изображения')
    parser.add_argument('--timeout', type=int, required=True, help='Таймаут для декодирования DataMatrix')
    parser.add_argument('--shrink', type=int, required=True,
                        help='Коэффициент уменьшения изображения для декодирования DataMatrix')
    parser.add_argument('--expected_num', type=int, required=True, help='Ожидаемое количество бутылок')
    parser.add_argument('--ftp_host', type=str, required=True, help='Хост FTP сервера')
    parser.add_argument('--log_level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Уровень логирования')
    return parser.parse_args()


async def main():
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    ftp_publisher = FTPPublisher(args.ftp_host)
    marker = BoxMarker(ftp_publisher, args.expected_num)
    ftp_publisher.subscribe(marker)
    ftp_publisher.connect()
    decoder = DataMatrixDecoder(url=args.url, max_count=args.expected_num, timeout=args.timeout, shrink=args.shrink,
                                callback=marker.process_detected_codes)
    decoder.subscribe(marker)
    await decoder.run()


if __name__ == "__main__":
    asyncio.run(main())