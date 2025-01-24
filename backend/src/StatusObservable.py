import logging
from typing import Any
import threading


class StatusObservable:
    status: Any = None

    def __init__(self):
        self._observers = []
        # take a derived class name as a default name
        self._name = self.__class__.__name__
        threading.Thread(target=self._notify_loop, daemon=True, name=f"{self._name}_notify_loop").start()

    def subscribe(self, observer):
        logging.debug(f"Subscribing {observer} to {self._name}")
        self._observers.append(observer)

    def unsubscribe(self, observer):
        logging.debug(f"Unsubscribing {observer} from {self._name}")
        self._observers.remove(observer)

    def notify(self):
        logging.debug(f"Notify {self._name} observers with value {self.status}")
        for observer in self._observers:
            observer.update_devices(self.status)

    def _notify_loop(self):
        while True:
            threading.Event().wait(0.1)
            self.notify()


class DeviceObserver:
    def update_devices(self, value):
        raise NotImplementedError
