from __future__ import annotations

import threading
import logging

from backend.src.Codes2XML import generate_xml
from backend.src.StatusObservable import DeviceObserver
from backend.src.status import DevicesStatusesHandler

from typing import ClassVar, List

from backend.src.FtpPublisher import FTPPublisher


class State:
    _box_marker: BoxMarker | None = None
    _detected_codes: List[str] = []
    _detected_group_code: str | None = None
    name: ClassVar[str] = "UNDEFINED"
    devices_status_handler: DevicesStatusesHandler

    def __init__(self, other_state: State = None) -> None:
        self._lock = threading.Lock()
        self.devices_status_handler = DevicesStatusesHandler()
        if other_state:
            self._detected_codes = other_state.detected_codes
            self._detected_group_code = other_state._detected_group_code
            self._box_marker = other_state.box_marker
            self.devices_status_handler = other_state.devices_status_handler

    def reset(self, box_marker: BoxMarker) -> None:
        self.devices_status_handler = DevicesStatusesHandler()
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
            logging.info(f"Processing detected codes: {codes}")
            logging.info(f"Current collected codes: {self._detected_codes}")
            self._process_detected_codes(codes)

    def _process_detected_codes(self, codes: List[str]) -> None:
        pass

    def do_job_once(self):
        pass

    def handle_additional_devices_status(self, status):
        with self._lock:
            self.devices_status_handler.handle_status(status)
            if self.devices_status_handler.is_error():
                self._box_marker.set_state(ErrorState)
            elif isinstance(self, ErrorState):
                self.reset(self._box_marker)
                self._box_marker.set_state(ReadyState)


class ReadyState(State):
    name = "READY"

    def do_job_once(self):
        self._detected_codes = []
        self._detected_group_code = None

    def _process_detected_codes(self, codes):
        if 0 < len(codes) < self._box_marker.expected_bottles_number:
            self._detected_codes = codes
            self._box_marker.set_state(CollectingCodesState)
        elif len(codes) == self._box_marker.expected_bottles_number:
            self._detected_codes = codes
            self._box_marker.set_state(CollectSingleGroupCode)
        elif len(codes) > self._box_marker.expected_bottles_number:
            self._detected_codes = []
            self._box_marker.set_state(TooMuchCodesState)


class CollectingCodesState(State):
    name = "COLLECTING_CODES"

    def _process_detected_codes(self, codes):
        union_codes = set(self._detected_codes).union(set(codes))
        if len(codes) == 0:
            self._box_marker.set_state(ReadyState)
        elif len(union_codes) > self._box_marker.expected_bottles_number:
            self._box_marker.set_state(TooMuchCodesState)
        elif len(union_codes) == self._box_marker.expected_bottles_number:
            self._detected_codes = list(union_codes)
            self._box_marker.set_state(CollectSingleGroupCode)


class TooMuchCodesState(ReadyState):
    name = "TOO_MUCH_CODES"


class CollectSingleGroupCode(State):
    name = "DETECTING_GROUP_CODE"

    def _process_detected_codes(self, codes):
        if len(codes) == 1 and codes[0] not in self._detected_codes:
            self._detected_group_code = codes[0]
            self.box_marker.set_state(CreateAndPublishXML)


class CreateAndPublishXML(State):
    name = "CREATE_AND_PUBLISH_XML"

    def do_job_once(self):
        logging.info("Creating and publishing XML")
        xml_file = generate_xml(self._detected_codes, self._detected_group_code)
        self._box_marker.publish_xml(xml_file, f"{self._detected_group_code}.xml")
        self._box_marker.set_state(ReadyState)


class ErrorState(State):
    name = "ERROR"


class BoxMarker(DeviceObserver):
    _state: State
    expected_bottles_number: int
    ftp_publisher: FTPPublisher | None = None

    def __init__(self, ftp_publisher: FTPPublisher, expected_bottles_number: int) -> None:
        self.expected_bottles_number = expected_bottles_number
        self._ftp_publisher = ftp_publisher
        self._state = ReadyState()
        self.reset()

    def __del__(self):
        self.set_state(ReadyState)
        self.reset()

    def set_state(self, state: type[State]):
        if not issubclass(state, State):
            raise ValueError("State must be a subclass of State")
        if not isinstance(self._state, state):
            if not isinstance(self._state, ErrorState):
                self._state = state(self._state)
            elif not self._state.devices_status_handler.is_error():
                self._state = state(self._state)
            logging.info(f"State changed to {self._state.name}")
        self._state.do_job_once()

    def update_devices(self, value):
        self._state.handle_additional_devices_status(value)

    async def process_detected_codes(self, codes: List) -> None:
        self._state.process_detected_codes(codes)

    def publish_xml(self, xml_file_content: str, filename: str):
        logging.info(f"Publishing XML file {filename}")
        if self._ftp_publisher:
            self._ftp_publisher.upload_file(filename, xml_file_content)

    async def get_state(self) -> str:
        return self._state.name

    async def get_devices_status(self) -> dict:
        return self._state.devices_status_handler.get_statuses()

    async def get_status(self) -> str:
        if isinstance(self._state, ErrorState):
            return "ERROR"
        elif isinstance(self._state, TooMuchCodesState):
            return "WARNING"
        else:
            return "OK"

    def get_detected_codes(self) -> List[str]:
        return self._state.detected_codes

    def reset(self):
        self._state.reset(self)
        self.set_state(ReadyState)
