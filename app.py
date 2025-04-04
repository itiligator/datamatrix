import asyncio
import logging
import sys
import argparse
import threading
from datetime import datetime

from flask import Flask, jsonify, send_file
from backend.src.BoxMarker import BoxMarker
from backend.src.DataMatrixDecoderMock import DataMatrixDecoderMock
from backend.src.FileSaver import FileSaver
from backend.src.DataMatrixDecoder import DataMatrixDecoder

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)
box_marker: BoxMarker | None = None
http_port: int = 8001


async def run_marker(url: str, timeout: int, expected_num: int, max_failures: int, test: bool = False):
    global box_marker
    file_saver = FileSaver()
    box_marker = BoxMarker(file_saver=file_saver, expected_bottles_number=expected_num,
                           max_failed_attempts=max_failures)
    file_saver.subscribe(box_marker)
    if not test:
        decoder = DataMatrixDecoder(url=url, max_count=expected_num, timeout=timeout,
                                    callback=box_marker.process_detected_codes)
    else:
        decoder = DataMatrixDecoderMock(url=url, max_count=expected_num, timeout=timeout,
                                        callback=box_marker.process_detected_codes)
    decoder.subscribe(box_marker)
    await decoder.run()


@app.route('/')
def index():
    return send_file('templates/index.html')


@app.route('/region_image')
def get_region_image():
    return send_file('region.jpg', mimetype='image/jpeg')


@app.route('/devices_status')
async def get_devices_status():
    devices_status = await box_marker.get_devices_status()
    return jsonify(devices_status)


@app.route('/state')
async def get_state():
    state = await box_marker.get_state()
    return jsonify(state)


@app.route('/detected_codes')
async def get_detected_codes():
    detected_codes = box_marker.get_detected_codes()
    return jsonify(detected_codes=detected_codes, detected_count=len(detected_codes))


@app.route('/collected_codes')
async def get_collected_codes():
    collected_codes = box_marker.get_collected_codes()
    return jsonify(collected_codes=collected_codes, collected_count=len(collected_codes))


@app.route('/reset', methods=['POST'])
def reset():
    global box_marker
    box_marker.reset()
    return '', 204


def start_flask():
    app.run(host='0.0.0.0', port=http_port)


def parse_args():
    parser = argparse.ArgumentParser(description='Запуск приложения с параметрами.')
    parser.add_argument('--url', type=str, required=True, help='URL для получения изображения')
    parser.add_argument('--timeout', type=int, required=False, default=2, help='Таймаут для декодирования DataMatrix')
    parser.add_argument('--expected_num', type=int, required=True, help='Ожидаемое количество бутылок')
    parser.add_argument('--http_port', type=str, required=False, default=8001, help='Порт для запуска бэка')
    parser.add_argument('--log_level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Уровень логирования')
    parser.add_argument('--test', action='store_true', help='Тестовый режим')
    parser.add_argument('--max_failed_attempts', type=int, default=2,
                        help='Максимальное количество попыток распознавания кодов на изображении')
    return parser.parse_args()


def main():
    global http_port
    args = parse_args()

    # also save logs to file with filename as current date and time in results folder
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"results/{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.log")
        ]
    )

    http_port = args.http_port
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    asyncio.run(
        run_marker(url=args.url, timeout=args.timeout * 1000, expected_num=args.expected_num, max_failures=args.max_failed_attempts, test=args.test))


if __name__ == "__main__":
    main()
