import asyncio
import logging
from backend.src.StatusObservable import StatusObservable
from backend.src.status import BarcodePrinterStatus


class BaseBarcodePrinter(StatusObservable):
    _status: BarcodePrinterStatus = BarcodePrinterStatus.UNDEFINED

    def __init__(self) -> None:
        super().__init__()
        self._status = BarcodePrinterStatus.INIT

    async def print_barcode(self, barcode: str, seq: int | None = None, total_bottles: int | None = None,
                            date: str | None = None) -> None:
        logging.info(f"Printing barcode {barcode} with seq {seq} on {date}; {total_bottles} bottles")
        self._status = BarcodePrinterStatus.PRINTING
        await self._print_barcode(barcode, seq, total_bottles, date)
        if self._status not in (BarcodePrinterStatus.OK, BarcodePrinterStatus.PRINTING):
            logging.error(f"Printing barcode {barcode} with seq {seq} failed. Status: {self._status}")
        elif self._status == BarcodePrinterStatus.PRINTING:
            self._status = BarcodePrinterStatus.OK

    async def _print_barcode(self, barcode: str, seq: int | None = None, total_bottles: int | None = None,
                             date: str | None = None) -> None:
        raise NotImplementedError

    def status(self) -> BarcodePrinterStatus:
        return self._status


class DummyBaseBarcodePrinter(BaseBarcodePrinter):
    def __init__(self) -> None:
        super().__init__()
        logging.info("DummyBarcodePrinter initialized")

    async def _print_barcode(self, barcode: str, seq: int | None = None, total_bottles: int | None = None,
                             date: str | None = None) -> None:
        # simulate printing for 5 seconds
        logging.info(f"Starting DUMMY printing barcode {barcode} with seq {seq} on {date}; {total_bottles} bottles")
        await asyncio.sleep(5)
        logging.info(f"Finished DUMMY printing barcode {barcode} with seq {seq} on {date}; {total_bottles} bottles")
