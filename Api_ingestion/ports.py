from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Sequence


class ReadingStorage(ABC):
    @abstractmethod
    def append(
        self,
        readings: Sequence[Any],
        transform: Optional[Callable[[dict], dict]] = None,
    ) -> None:
        raise NotImplementedError


class AlertNotifier(ABC):
    @abstractmethod
    def notify(self, payload: Any, routing_key: str = "default") -> None:
        raise NotImplementedError