import logging
import cups

from backend.src.StatusObservable import StatusObservable
from backend.src.status import PrinterStatus
from backend.src.LabelGenerator import LabelGenerator


class LabelPrinter(StatusObservable):
    def __init__(self, title, text):
        super().__init__()
        self.status = PrinterStatus.INIT
        self.notify()
        self.title = title
        self.text = text
        self.cups_printer = None
        self.label_generator = LabelGenerator('templates/label.html', 'styles/label.css', title, text)
        try:
            self.cups_conn = cups.Connection()
            self.cups_printer = self.cups_conn.getDefault()
            if self.cups_printer is not None:
                logging.info(f"Используемый принтер (принтер по умолчанию): {self.cups_printer}")
                self.status = PrinterStatus.READY
            else:
                self.status = PrinterStatus.PRINTER_NOT_FOUND
                logging.error("Принтер не найден или не установлен по умолчанию.")
            self.notify()
        except cups.IPPError as e:
            logging.exception(f"Ошибка подключения к CUPS", exc_info=e)
            self.status = PrinterStatus.GENERAL_FAILURE
            self.notify()



    def print_label(self, code, seq):
        if self.cups_printer is not None:
            self.status = PrinterStatus.PRINTING
            self.notify()
            label_filename = self.label_generator.generate_label(code, seq)
            logging.info(f"Отправка задания на печать на принтер {self.cups_printer}")
            self.cups_conn.printFile(self.cups_printer, label_filename, "Label", {})
            logging.info(f"Задание на печать отправлено на принтер {self.cups_printer}")
            self.status = PrinterStatus.READY
            self.notify()

    def __del__(self):
        if self.cups_conn:
            self.cups_conn.cancelAllJobs()
