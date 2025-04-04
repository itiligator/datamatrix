from __future__ import annotations

from datetime import datetime
import threading
import logging

from backend.src.Codes2XML import generate_xml
from backend.src.Codes2TXT import generate_csv
from backend.src.DatabaseManager import DatabaseManager
from backend.src.StatusObservable import DeviceObserver
from backend.src.status import DevicesStatusesHandler
from backend.src.code_checkers import is_km_valid, is_ka_valid
from typing import ClassVar, List

from backend.src.FileSaver import FileSaver


class State:
    _box_marker: BoxMarker | None = None
    _detected_codes: List[str] = []
    _detected_group_code: str | None = None
    name: ClassVar[str] = "НЕОПРЕДЕЛЕНО"
    code: ClassVar[int] = 0

    def __init__(self, other_state: State = None) -> None:
        self._lock = threading.Lock()

        if other_state:
            self._detected_codes = other_state.detected_codes
            self._detected_group_code = other_state._detected_group_code
            self._box_marker = other_state.box_marker

    def reset(self, box_marker: BoxMarker) -> None:
        self._detected_codes = []
        self._detected_group_code = None
        self._box_marker = box_marker

    @property
    def box_marker(self):
        return self._box_marker

    @box_marker.setter
    def box_marker(self, box_marker):
        self._box_marker = box_marker

    @property
    def detected_codes(self):
        return self._detected_codes

    @property
    def detected_group_code(self):
        return self._detected_group_code

    def process_detected_codes(self, codes: List[str]) -> None:
        with self._lock:
            logging.info(f"Состояние: {self.name}.\tПрочитано кодов в кадре: {len(codes):2d}")
            # for code in codes:
            #     logging.info(code[-7:-1])
            self._process_detected_codes(codes)

    def _process_detected_codes(self, codes: List[str]) -> None:
        pass

    def do_job_once(self):
        pass


class ReadyState(State):
    name = "ГОТОВ"
    code = 1

    def do_job_once(self):
        self._detected_codes = []
        self._detected_group_code = None

    def _process_detected_codes(self, codes):
        valid_codes = [code for code in codes if is_km_valid(code)]
        logging.info(f"Состояние: {self.name}.\tВалидных кодов: {len(valid_codes)}")
        if 0 < len(valid_codes) <= self._box_marker.expected_bottles_number:
            # save only valid codes
            self._detected_codes = valid_codes
            # Check for duplicate codes in the database
            duplicates_exist = any(self._box_marker.db_manager.is_individual_code_exists(code) for code in codes)
            if duplicates_exist:
                self._box_marker.set_state(DuplicateCodeError)
                return
            if len(self._detected_codes) == self._box_marker.expected_bottles_number:
                self._box_marker.set_state(CollectSingleGroupCode)
                return
            else:
                self._box_marker.set_state(CollectingCodesState)
                return
        elif len(codes) > self._box_marker.expected_bottles_number:
            self._detected_codes = []
            self._box_marker.set_state(TooMuchCodesState)
            return


class CollectingCodesState(State):
    name = "РАСПОЗНАЮ КОДЫ С БУТЫЛОК"
    code = 2

    def __init__(self, other_state: State = None) -> None:
        super().__init__(other_state)
        self._zero_count = 0

    def _process_detected_codes(self, codes):
        if len(codes) == 0:
            self._zero_count += 1
            logging.info(
                f"Состояние: {self.name}.\tРаспознал ноль кодов, возврат на исходную через "
                f"{self.box_marker.max_failed_attempts - self._zero_count} попыток")
            if self._zero_count >= self.box_marker.max_failed_attempts:
                self._box_marker.set_state(ReadyState)
                return
        else:
            self._zero_count = 0
        valid_codes = [code for code in codes if is_km_valid(code)]
        logging.info(f"Состояние: {self.name}.\tВалидных кодов: {len(valid_codes)}")
        union_codes = set(self._detected_codes).union(set(valid_codes))
        logging.info(
            f"Состояние: {self.name}.\tНакоплено: {len(union_codes):2d}/{self.box_marker.expected_bottles_number}")
        # for code in union_codes:
        #     logging.info(code[-12:-1])
        if len(union_codes) < self._box_marker.expected_bottles_number:
            self._detected_codes = list(union_codes)
        elif len(union_codes) > self._box_marker.expected_bottles_number:
            self._box_marker.set_state(TooMuchCodesState)
            return
        elif len(union_codes) == self._box_marker.expected_bottles_number:
            # Check for duplicate codes in the database
            duplicates_exist = any(self._box_marker.db_manager.is_individual_code_exists(code) for code in union_codes)
            duplicates_exist |= any(self._box_marker.db_manager.is_group_code_exists(code) for code in union_codes)
            self._detected_codes = list(union_codes)
            if duplicates_exist:
                self._box_marker.set_state(DuplicateCodeError)
                return
            self._box_marker.set_state(CollectSingleGroupCode)
            return


class TooMuchCodesState(ReadyState):
    name = "СЛИШКОМ МНОГО КОДОВ В КАДРЕ"
    code = -1


class CollectSingleGroupCode(State):
    name = "РАСПОЗНАЮ КОД АГРЕГАЦИИ"
    code = 3

    def _process_detected_codes(self, codes):
        valid_codes = [code for code in codes if is_ka_valid(code)]
        logging.info(f"Состояние: {self.name}.\tВалидных кодов: {len(valid_codes):2d}")
        if len(valid_codes) == 1:
            self._detected_group_code = valid_codes[0]
            # Check if the group code already exists in the database
            if self._box_marker.db_manager.is_group_code_exists(self._detected_group_code):
                self._box_marker.set_state(DuplicateCodeError)
                return
            # Proceed to create XML
            self.box_marker.set_state(CreateAndPublishXML)
            return
        elif len(valid_codes) > 1:
            self.box_marker.set_state(TooMuchCodesState)
            return


class CreateAndPublishXML(State):
    name = "СОЗДАЮ И СОХРАНЯЮ XML"
    code = 4

    def do_job_once(self):
        seq = self._box_marker.db_manager.save_codes(self._detected_codes, self._detected_group_code)
        if seq == -1:
            logging.error("Ошибка сохранения кодов в базу данных")
            self._box_marker.set_state(ErrorState)
            return
        logging.info(
            f"Сохранено {len(self._detected_codes)} индивидуальных кодов и 1 групповой код в базу данных. "
            f"Номер последовательности: {seq}")
        logging.info(f"Коды бутылок:")
        for code in self._detected_codes:
            logging.info(code)
        logging.info(f"Код агрегации: {self._detected_group_code}")
        current_day = datetime.today().strftime('%d%m%Y')
        filename = f"{seq:04d}_{current_day}"
        logging.info(f"Создаю и сохраняю XML файл {filename}.xml")
        xml_file = generate_xml(self._detected_codes, self._detected_group_code)
        self._box_marker.write_file(xml_file, f"{filename}.xml", 'xml')
        logging.info(f"Создаю и сохраняю CSV файл {filename}.csv")
        csv_file = generate_csv(self._detected_codes, self._detected_group_code)
        self._box_marker.write_file(csv_file, f"{filename}.csv", 'csv')
        self._box_marker.set_state(WaitForNextBox)
        return


class ErrorState(State):
    name = "ОШИБКА"
    code = -3


class DuplicateCodeError(State):
    name = "ОШИБКА: РАНЕЕ УЧТЕННЫЙ КОД В КАДРЕ"
    code = -2

    def _process_detected_codes(self, codes: List[str]) -> None:
        # if there is no longer duplicate codes, return to the Ready state
        if not any(self._box_marker.db_manager.is_individual_code_exists(code) for code in codes) and \
                not any(self._box_marker.db_manager.is_group_code_exists(code) for code in codes):
            self._box_marker.set_state(ReadyState)
            return


class WaitForNextBox(State):
    name = "ОЖИДАНИЕ СЛЕДУЮЩЕЙ КОРОБКИ"
    code = 5

    def _process_detected_codes(self, codes: List[str]) -> None:
        if len(codes) == 0:
            self._box_marker.set_state(ReadyState)
            return


class BoxMarker(DeviceObserver):
    _state: State
    expected_bottles_number: int
    file_saver: FileSaver | None = None
    _devices_status_handler: DevicesStatusesHandler
    db_manager: DatabaseManager
    latest_codes: List[str] = []

    def __init__(self, file_saver: FileSaver, expected_bottles_number: int, max_failed_attempts: int) -> None:
        self.expected_bottles_number = expected_bottles_number
        self._file_saver = file_saver
        self.db_manager = DatabaseManager()
        self._state = ReadyState()
        self.reset()
        self._devices_status_handler = DevicesStatusesHandler()
        self.max_failed_attempts = max_failed_attempts

    def __del__(self):
        self.set_state(ReadyState)
        self.reset()

    def set_state(self, state: type[State]):
        if not issubclass(state, State):
            raise ValueError("State must be a subclass of State")
        if not isinstance(self._state, state):
            logging.info(f"Запланирован переход состояния `{self._state.name}` -> `{state.name}`")
            if not isinstance(self._state, ErrorState):
                self._state = state(self._state)
            elif not self._devices_status_handler.is_error():
                self._state = state(self._state)
            self._state.do_job_once()
            logging.info(f"Выполнен переход в состояние {self._state.name}")

    def update_devices(self, status):
        self._devices_status_handler.handle_status(status)
        if self._devices_status_handler.is_error():
            self.set_state(ErrorState)
        elif isinstance(self._state, ErrorState):
            self.reset()

    async def process_detected_codes(self, codes: List) -> None:
        self.latest_codes = codes
        self._state.process_detected_codes(codes)

    def write_file(self, xml_file_content: str, filename: str, subdir: str | None = None) -> None:
        if self._file_saver:
            self._file_saver.save_file(filename, xml_file_content, subdir)

    async def get_state(self) -> dict:
        return {"name": self._state.name, "code": self._state.code}

    async def get_devices_status(self) -> dict:
        return self._devices_status_handler.get_statuses()

    def get_detected_codes(self) -> List[str]:
        return self.latest_codes

    def get_collected_codes(self) -> List[str]:
        if isinstance(self._state, CollectingCodesState):
            return self._state.detected_codes
        else:
            return []

    def reset(self):
        self._state.reset(self)
        self.set_state(ReadyState)
