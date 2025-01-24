import logging
from typing import List

from backend.src.custom_types import BarcodeInfo


class BaseBarcodeIssuer:
    def issue_barcode(self, codes: List[str]) -> BarcodeInfo:
        raise NotImplementedError

class DummyBarcodeIssuer(BaseBarcodeIssuer):
    def __init__(self):
        self._storage = {}
        self._sequence = 0


    def issue_barcode(self, codes: List[str]) -> BarcodeInfo:
        codes.sort()
        code_string = "".join(codes)
        logging.info(f"Issuing barcode for {codes}")
        if code_string in self._storage:
             return self._storage[code_string]
        self._sequence += 1
        barcode = abs(hash(code_string)) % 100000
        barcode_info = BarcodeInfo(str(barcode), self._sequence)
        self._storage[code_string] = barcode_info
        return barcode_info

