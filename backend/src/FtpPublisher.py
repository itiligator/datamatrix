import logging
import ftplib

from backend.src.status import FTPPublisherStatus
from backend.src.StatusObservable import StatusObservable


class FTPPublisher(StatusObservable):
    def __init__(self, host: str, port: int | None = None, username: str | None = None, password: str | None = None, upload_dir: str | None = 'upload'):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.upload_dir = upload_dir
        self.ftp = ftplib.FTP()
        self.status = FTPPublisherStatus.INIT
        logging.info(f"FTPPublisher initialized with host: {host}, port: {port}, username: {username}")
        self.notify()

    def connect(self):
        logging.info("Connecting to FTP server...")
        try:
            if self.port is None:
                self.ftp.connect(self.host)
            else:
                self.ftp.connect(self.host, port=self.port)
            logging.info(f"Connected to FTP server at {self.host}:{self.port}")
            if self.username and self.password:
                self.ftp.login(self.username, self.password)
                logging.info(f"Logged in as {self.username}")
            else:
                self.ftp.login()
                logging.info("Logged in anonymously")
            self.status = FTPPublisherStatus.CONNECTED
        except Exception as e:
            logging.error(f"Failed to connect to FTP server: {e}")
            self.status = FTPPublisherStatus.GENERAL_FAILURE
        self.notify()

    def upload_file(self, file_path: str, content: str):
        if self.ftp.sock is None:
            logging.error("FTP connection is not established.")
            self.status = FTPPublisherStatus.GENERAL_FAILURE
            self.notify()
            raise ConnectionError("FTP connection is not established.")

        logging.info(f"Uploading file {file_path} to FTP server...")
        try:
            with open(file_path, 'w') as file:
                file.write(content)
                logging.info(f"File {file_path} written with content")
            with open(file_path, 'rb') as file:
                self.status = FTPPublisherStatus.PUBLISHING
                self.notify()
                self.ftp.storbinary(f'STOR {self.upload_dir}/{file_path}', file)
                logging.info(f"File {file_path} uploaded to FTP server")
                self.status = FTPPublisherStatus.CONNECTED
        except Exception as e:
            logging.error(f"Failed to upload file to FTP server: {e}")
            self.status = FTPPublisherStatus.GENERAL_FAILURE
        self.notify()

    def disconnect(self):
        logging.info("Disconnecting from FTP server...")
        try:
            self.ftp.quit()
            logging.info("Disconnected from FTP server")
            self.status = FTPPublisherStatus.DISCONNECTED
        except Exception as e:
            logging.error(f"Failed to disconnect from FTP server: {e}")
            self.status = FTPPublisherStatus.GENERAL_FAILURE
        self.notify()
