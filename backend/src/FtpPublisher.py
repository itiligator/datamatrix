import logging
import ftplib

from backend.src.status import FTPPublisherStatus
from backend.src.StatusObservable import StatusObservable


class FTPPublisher(StatusObservable):
    def __init__(self, host: str, port: int | None = None, username: str | None = None, password: str | None = None, upload_dir: str | None = 'upload'):
        super().__init__()
        self.status = FTPPublisherStatus.INIT
        logging.info(f"FTPPublisher initialized with host: {host}, port: {port}, username: {username}")
        self.notify()

    def connect(self):
        self.status = FTPPublisherStatus.CONNECTED
        self.notify()

    def upload_file(self, file_path: str, content: str):
        logging.info(f"Saving file {file_path}...")
        try:
            with open(file_path, 'w') as file:
                file.write(content)
                logging.info(f"File {file_path} saved")
        except Exception as e:
            logging.error(f"Failed to save file to FTP server: {e}")
            self.status = FTPPublisherStatus.GENERAL_FAILURE
        self.notify()

    def disconnect(self):
        self.status = FTPPublisherStatus.DISCONNECTED
        self.notify()
