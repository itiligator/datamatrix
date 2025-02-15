from enum import Enum


class FileSaverStatus(Enum):
    UNDEFINED = "UNDEFINED"
    INIT = "INIT"
    READY = "READY"
    FOLDER_CREATION_FAILED = "FOLDER_CREATION_FAILED"
    SAVING = "SAVING"
    SAVING_FAILED = "SAVING_FAILED"
    GENERAL_FAILURE = "GENERAL_FAILURE"
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
    FETCHING_IMAGE = "FETCHING_IMAGE"
    OK = "OK"

    def __str__(self):
        return self.value


class DevicesStatusesHandler:
    def __init__(self):
        self._devices_status = {"file_saver": FileSaverStatus.UNDEFINED,
                                "datamatrix_decoder": DatamatrixDecoderStatus.UNDEFINED}

    def handle_status(self, status):
        self._update_device_status(status)

    def _update_device_status(self, status):
        if isinstance(status, FileSaverStatus):
            self._devices_status["file_saver"] = status
        if isinstance(status, DatamatrixDecoderStatus):
            self._devices_status["datamatrix_decoder"] = status

    def is_error(self):
        return (self._devices_status["file_saver"] in (
            FileSaverStatus.GENERAL_FAILURE,
            FileSaverStatus.UNKNOWN_ERROR) or
                self._devices_status["datamatrix_decoder"] in (
                    DatamatrixDecoderStatus.GENERAL_FAILURE,
                    DatamatrixDecoderStatus.UNKNOWN_ERROR,
                    DatamatrixDecoderStatus.IMAGE_UNAVAILABLE))

    def get_statuses(self):
        return {k: str(v) for k, v in self._devices_status.items()}
