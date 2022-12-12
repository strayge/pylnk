from abc import ABC, abstractmethod
from typing import Union


class Serializable(ABC):
    """Force subclasses to implement the serializable methods."""

    @abstractmethod
    def json(self) -> Union[dict, list]:
        """Return a JSON representation of the object."""
        raise NotImplementedError

    def text(self) -> str:
        """Return a text representation of the object."""
        return str(self)
