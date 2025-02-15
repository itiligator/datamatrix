import logging
import os

from backend.src.status import FileSaverStatus
from backend.src.StatusObservable import StatusObservable


class FileSaver(StatusObservable):
    def __init__(self, result_dir: str | None = 'upload'):
        super().__init__()
        self.status = FileSaverStatus.INIT
        self.notify()
        self.results_dir = result_dir
        try:
            os.makedirs(self.results_dir, exist_ok=True)
            logging.info(f"Директория для сохранения файлов: {result_dir}")
            self.status = FileSaverStatus.READY
            self.notify()
        except Exception as e:
            logging.error(f"Невозможно создать директорию для сохранения файлов {result_dir}: {e}")
            self.status = FileSaverStatus.FOLDER_CREATION_FAILED
            self.notify()

    def save_file(self, file_path: str, content: str) -> int:
        if self.status != FileSaverStatus.READY:
            logging.error("Хранитель файлов не готов")
            return -1
        logging.info(f"Сохраняю файл {file_path}...")
        self.status = FileSaverStatus.SAVING
        try:
            with open(os.path.join(self.results_dir, file_path), 'w') as file:
                file.write(content)
                logging.info(f"Файл {file_path} успешно сохранён")
                self.status = FileSaverStatus.READY
        except Exception as e:
            logging.error(f"Ошибка сохранения файла: {e}")
            self.status = FileSaverStatus.SAVING_FAILED
            return -1
        self.notify()
        return 0
