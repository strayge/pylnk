from pprint import pformat
from typing import Any, Dict, Tuple

_MODIFIER_KEYS = ('SHIFT', 'CONTROL', 'ALT')


class Flags:

    def __init__(self, flag_names: Tuple[str, ...], flags_bytes: int = 0) -> None:
        self._flag_names = flag_names
        self._flags: Dict[str, bool] = dict([(name, False) for name in flag_names])
        self.set_flags(flags_bytes)

    def set_flags(self, flags_bytes: int) -> None:
        for pos, flag_name in enumerate(self._flag_names):
            self._flags[flag_name] = bool(flags_bytes >> pos & 0x1)

    @property
    def bytes(self) -> int:
        result = 0
        for pos in range(len(self._flag_names)):
            result = (self._flags[self._flag_names[pos]] and 1 or 0) << pos | result
        return result

    def __getitem__(self, key: str) -> Any:
        if key in self._flags:
            return object.__getattribute__(self, '_flags')[key]
        return object.__getattribute__(self, key)

    def __setitem__(self, key: str, value: bool) -> None:
        if key not in self._flags:
            raise KeyError("The key '%s' is not defined for those flags." % key)
        self._flags[key] = value

    def __getattr__(self, key: str) -> Any:
        if key in self._flags:
            return object.__getattribute__(self, '_flags')[key]
        return object.__getattribute__(self, key)

    def __setattr__(self, key: str, value: Any) -> None:
        if ('_flags' not in self.__dict__) or (key in self.__dict__):
            object.__setattr__(self, key, value)
        else:
            self.__setitem__(key, value)

    def __str__(self) -> str:
        return pformat(self._flags, indent=2)


class ModifierKeys(Flags):

    def __init__(self, flags_bytes: int = 0) -> None:
        Flags.__init__(self, _MODIFIER_KEYS, flags_bytes)

    def __str__(self) -> str:
        s = ""
        s += self.CONTROL and "CONTROL+" or ""
        s += self.SHIFT and "SHIFT+" or ""
        s += self.ALT and "ALT+" or ""
        return s
