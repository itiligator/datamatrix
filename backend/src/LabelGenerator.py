import base64
from datetime import datetime
import os
import logging

from blabel import LabelWriter

from backend.src.StatusObservable import StatusObservable
from backend.src.status import LabelGeneratorStatus

gtin_to_title_text = {
    "04680571061172": ("Салек Амбер Лагер 0,45л", "пиво светлое, непастеризованное, неосветленное, фильтрованное"),
    "04680571061219": ("Салек АПА 0,45л", "пиво светлое, непастеризованное, неосветленное, нефильтрованное"),
    "04680571061189": ("Салек Вайсбир 0,45л", "пиво светлое пшеничное непастеризованное, неосветленное, нефильтрованное"),
    "04680571061196": ("Салек Венский лагер 0,45л", "пиво светлое, непастеризованное, неосветленное, нефильтрованное"),
    "04680571061233": ("Салек Зеро 0,45л",
                    "безалкогольное пиво светлое, непастеризованное, неосветленное, нефильтрованное"),
    "04680571061226": ("Салек ИПА  0,45л", "пиво светлое, непастеризованное, неосветленное, нефильтрованное"),
    "04680571061202": ("Салек Линдерхоф 0,45л",
                    "пиво светлое пшеничное, непастеризованное, неосветленное, нефильтрованное"),
    "04680571061127": ("Салек Чешский лагер 0,45л", "пиво светлое непастеризованное, неосветленное, нефильтрованное")
}

valid_gtins = list(gtin_to_title_text.keys())


class LabelGenerator(StatusObservable):
    def __init__(self, template_path, stylesheets):
        super().__init__()
        self.status = LabelGeneratorStatus.INIT
        self.notify()
        self.label_writer = LabelWriter(template_path, default_stylesheets=(stylesheets,))
        os.makedirs(os.path.join("results", "labels"), exist_ok=True)
        self.status = LabelGeneratorStatus.READY
        logging.info("LabelGenerator инициализирован")
        logging.info("Доступные GTIN и их названия:")
        for gtin, (title, text) in gtin_to_title_text.items():
            logging.info(f"GTIN: {gtin}, Title: {title}, Text: {text}")

    def generate_label(self, group_code, seq) -> str:
        self.status = LabelGeneratorStatus.GENERATING
        self.notify()
        current_day = datetime.today().strftime('%d%m%Y')
        filename = f"{seq:04d}_{current_day}.pdf"
        filename = os.path.join("results", "labels", filename)
        gtin = self._gtin_from_group_code(group_code)
        title, text = gtin_to_title_text.get(gtin, (None, None))
        if title is None or text is None:
            self.status = LabelGeneratorStatus.UNKNOWN_GTIN
            logging.error(f"Ошибка! Неизвестный GTIN: {gtin}")
            self.notify()
            raise ValueError(f"Unknown GTIN: {gtin}")
        logging.info(f"Генерирую наклейку для GTIN: {gtin}, Название: {title}, Описание: {text}")

        records = [
            dict(code=base64.b64decode(group_code).decode('utf-8'),
                 code_text=base64.b64decode(group_code).decode('utf-8'), seq=str(seq), title=title, text=text)
        ]
        self.label_writer.write_labels(records, target=filename)
        logging.info(f"Наклейка сохранена: {filename}")
        return filename

    @staticmethod
    def _gtin_from_group_code(group_code: str) -> str:
        """
        Extracts the GTIN from a base64 encoded group code.
        :param group_code: Base64 encoded group code
        :return: GTIN
        """
        decoded = base64.b64decode(group_code).decode('utf-8')
        return decoded[2:16]
