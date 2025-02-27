import asyncio
import logging
import os
import sys
import argparse
import threading

from flask import Flask, jsonify, render_template, send_file
from backend.src.BoxMarker import BoxMarker
from backend.src.FileSaver import FileSaver
from backend.src.DataMatrixDecoder import DataMatrixDecoder

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)
box_marker: BoxMarker | None = None
http_port: int = 8001


async def run_marker(url: str, timeout: int, expected_num: int):
    global box_marker
    file_saver = FileSaver()
    box_marker = BoxMarker(file_saver, expected_num)
    file_saver.subscribe(box_marker)
    decoder = DataMatrixDecoder(url=url, max_count=expected_num, timeout=timeout,
                                callback=box_marker.process_detected_codes)
    decoder.subscribe(box_marker)
    await decoder.run()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status')
async def get_status():
    status = await box_marker.get_status()
    return jsonify(status=status)


@app.route('/devices_status')
async def get_devices_status():
    devices_status = await box_marker.get_devices_status()
    return jsonify(devices_status)


@app.route('/state')
async def get_state():
    state = await box_marker.get_state()
    return jsonify(state=state)


@app.route('/detected_codes')
async def get_detected_codes():
    detected_codes = box_marker.get_detected_codes()
    return jsonify(detected_codes=detected_codes)


@app.route('/files')
async def list_files():
    files = os.listdir('results')
    return jsonify(files)


@app.route('/files/<filename>')
async def download_file(filename):
    return send_file(os.path.join('results', filename), as_attachment=True)


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
    return parser.parse_args()


def main():
    global http_port
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    http_port = args.http_port
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    asyncio.run(
        run_marker(url=args.url, timeout=args.timeout * 1000, expected_num=args.expected_num))


if __name__ == "__main__":
    main()
