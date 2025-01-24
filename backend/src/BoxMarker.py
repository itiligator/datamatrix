from __future__ import annotations

import asyncio
import threading
import time
import logging

from backend.src.BarcodePrinter import BaseBarcodePrinter
from backend.src.BarcodeIssuer import BaseBarcodeIssuer
from backend.src.Codes2XML import generate_xml
from backend.src.StatusObservable import DeviceObserver
from backend.src.custom_types import BarcodeInfo
from backend.src.status import DevicesStatusesHandler

from typing import ClassVar, List

from backend.src.FtpPublisher import FTPPublisher


class State:
    _box_marker: BoxMarker | None = None
    _detected_codes: List[str] = []
    _issued_barcode_info: BarcodeInfo | None = None
    name: ClassVar[str] = "UNDEFINED"
    devices_status_handler: DevicesStatusesHandler

    def __init__(self, other_state: State = None) -> None:
        self._lock = threading.Lock()
        self.devices_status_handler = DevicesStatusesHandler()
        if other_state:
            self._detected_codes = other_state.detected_codes
            self._issued_barcode_info = other_state._issued_barcode_info
            self._box_marker = other_state.box_marker
            self.devices_status_handler = other_state.devices_status_handler

    def reset(self, box_marker: BoxMarker) -> None:
        self.devices_status_handler = DevicesStatusesHandler()
        self._detected_codes = []
        self._issued_barcode_info = None
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
    def issued_barcode(self):
        if self._issued_barcode_info:
            return self._issued_barcode_info.barcode

    @property
    def sequence(self):
        return self._issued_barcode_info.sequence

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
        self._issued_barcode_info = None

    def _process_detected_codes(self, codes):
        if 0 < len(codes) < self._box_marker.expected_bottles_number:
            self._detected_codes = codes
            self._box_marker.set_state(CollectingCodesState)
        elif len(codes) == self._box_marker.expected_bottles_number:
            self._detected_codes = codes
            self._box_marker.set_state(IssueBarcodeState)
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
            self._box_marker.set_state(IssueBarcodeState)


class TooMuchCodesState(ReadyState):
    name = "TOO_MUCH_CODES"


class IssueBarcodeState(State):
    name = "ISSUE_BARCODE"

    def do_job_once(self):
        self._issued_barcode_info = self._box_marker.barcode_issuer.issue_barcode(self._detected_codes)
        self._box_marker.set_state(CreateAndPublishXML)


class CreateAndPublishXML(State):
    name = "CREATE_AND_PUBLISH_XML"

    def do_job_once(self):
        logging.info("Creating and publishing XML")
        xml_file = generate_xml(self._detected_codes, self._issued_barcode_info.barcode)
        self._box_marker.publish_xml(xml_file, f"{self._issued_barcode_info.barcode}.xml")
        self._box_marker.set_state(PrintingBarcodeState)


class PrintingBarcodeState(State):
    name = "PRINTING_BARCODE"

    def do_job_once(self):
        self._box_marker.print_barcode_job()
        self._box_marker.set_state(WaitForPrintRequestState)


class WaitForPrintRequestState(State):
    name = "WAIT_FOR_PRINT_REQUEST"

    def _process_detected_codes(self, codes: List[str]) -> None:
        if not codes:
            self._box_marker.set_state(ReadyState)
            return

        prev_detected_set = set(self._detected_codes)
        new_detected_set = set(codes)
        old_codes_present = bool(prev_detected_set & new_detected_set)
        new_codes_present = bool(new_detected_set - prev_detected_set)

        if old_codes_present and new_codes_present:
            self._box_marker.set_state(TooMuchCodesState)
        elif not old_codes_present:
            self._detected_codes = codes
            self._box_marker.set_state(CollectingCodesState)


class ErrorState(State):
    name = "ERROR"



class BoxMarker(DeviceObserver):
    _state: State
    _barcode_printer: BaseBarcodePrinter | None = None
    barcode_issuer: BaseBarcodeIssuer | None = None
    expected_bottles_number: int
    ftp_publisher: FTPPublisher | None = None

    def __init__(self, barcode_printer: BaseBarcodePrinter, barcode_issuer: BaseBarcodeIssuer,
                 ftp_publisher: FTPPublisher,
                 expected_bottles_number: int) -> None:
        self.expected_bottles_number = expected_bottles_number
        self._barcode_printer = barcode_printer
        self.barcode_issuer = barcode_issuer
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

    def print_barcode_job(self):
        logging.info("Printing barcode")
        barcode = self._state.issued_barcode
        seq = self._state.sequence
        total_bottles = len(self._state.detected_codes)
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        asyncio.create_task(self._barcode_printer.print_barcode(barcode, seq, total_bottles, date))

    async def print_barcode(self):
        if isinstance(self._state, WaitForPrintRequestState):
            self.set_state(PrintingBarcodeState)

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

    def reset(self):
        self._state.reset(self)
        self.set_state(ReadyState)
