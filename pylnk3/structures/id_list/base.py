from abc import abstractmethod

from pylnk3.structures.base import Serializable


class IDListEntry(Serializable):
    @property
    @abstractmethod
    def bytes(self) -> bytes:
        ...
