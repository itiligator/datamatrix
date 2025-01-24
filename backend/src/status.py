from enum import Enum


class BarcodePrinterStatus(Enum):
    UNDEFINED = "UNDEFINED"
    INIT = "INIT"
    OK = "OK"
    PRINTING = "PRINTING"
    GENERAL_FAILURE = "GENERAL_FAILURE"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_ERROR = "DEVICE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    def __str__(self):
        return self.value


class FTPPublisherStatus(Enum):
    UNDEFINED = "UNDEFINED"
    INIT = "INIT"
    CONNECTED = "CONNECTED"
    PUBLISHING = "PUBLISHING"
    GENERAL_FAILURE = "GENERAL_FAILURE"
    DISCONNECTED = "DISCONNECTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    def __str__(self):
        return self.value


class DatamatrixDecoderStatus(Enum):
    UNDEFINED = "UNDEFINED"
    INIT = "INIT"
    DECODING = "DECODING"
    GENERAL_FAILURE = "GENERAL_FAILURE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    IMAGE_UNAVAILABLE = "IMAGE_UNAVAILABLE"
    OK = "OK"

    def __str__(self):
        return self.value


class DevicesStatusesHandler:
    def __init__(self):
        self._devices_status = {"printer": BarcodePrinterStatus.UNDEFINED,
                                "ftp_publisher": FTPPublisherStatus.UNDEFINED,
                                "datamatrix_decoder": DatamatrixDecoderStatus.UNDEFINED}

    def handle_status(self, status):
        self._update_device_status(status)

    def _update_device_status(self, status):
        if isinstance(status, BarcodePrinterStatus):
            self._devices_status["printer"] = status
        if isinstance(status, FTPPublisherStatus):
            self._devices_status["ftp_publisher"] = status
        if isinstance(status, DatamatrixDecoderStatus):
            self._devices_status["datamatrix_decoder"] = status

    def is_error(self):
        return self._devices_status["printer"] in (
            BarcodePrinterStatus.GENERAL_FAILURE, BarcodePrinterStatus.DEVICE_NOT_FOUND,
            BarcodePrinterStatus.DEVICE_ERROR,
            BarcodePrinterStatus.UNKNOWN_ERROR) or self._devices_status["ftp_publisher"] in (
            FTPPublisherStatus.GENERAL_FAILURE, FTPPublisherStatus.UNKNOWN_ERROR) or self._devices_status[
            "datamatrix_decoder"] in (DatamatrixDecoderStatus.GENERAL_FAILURE, DatamatrixDecoderStatus.UNKNOWN_ERROR,
                                      DatamatrixDecoderStatus.IMAGE_UNAVAILABLE)

    def get_statuses(self):
        return {k: str(v) for k, v in self._devices_status.items()}
