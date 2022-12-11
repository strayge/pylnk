from abc import abstractmethod


class IDListEntry:
    @property
    @abstractmethod
    def bytes(self) -> bytes:
        ...
