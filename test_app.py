import asyncio
import logging
import sys
import threading

from flask import Flask, jsonify, render_template
from backend.src.BoxMarker import BoxMarker
from backend.src.FtpPublisher import FTPPublisher
from backend.src.DataMatrixDecoder import DataMatrixDecoder

app = Flask(__name__)
box_marker: BoxMarker | None = None

async def run_marker():
    global box_marker
    expected_num = 3
    ftp_publisher = FTPPublisher('localhost')
    box_marker = BoxMarker(ftp_publisher, expected_num)
    ftp_publisher.subscribe(box_marker)
    ftp_publisher.connect()
    decoder = DataMatrixDecoder(url='http://192.168.1.101:8080/photoaf.jpg', max_count=3, timeout=2000, shrink=2,
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

def start_flask():
    app.run(host='0.0.0.0', port=8001)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    asyncio.run(run_marker())