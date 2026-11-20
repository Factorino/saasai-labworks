from abc import ABC
from dataclasses import dataclass, field, fields
from typing import Any, Self, dataclass_transform


@dataclass_transform(kw_only_default=True, frozen_default=True, field_specifiers=(field,))
def value_object[VoT: ValueObject](cls: type[VoT]) -> type[VoT]:
    dtcls: type[VoT] = dataclass(cls, frozen=True, kw_only=True)
    _require_fields(dtcls)
    return dtcls


class ValueObject(ABC):
    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        if cls is ValueObject:
            raise TypeError("Base Value Object cannot be instantiated directly")
        if "__dataclass_fields__" not in vars(cls):
            raise TypeError(f"{cls.__name__} is missing the @value_object decorator")
        return object.__new__(cls)

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, _memo: dict[int, Any]) -> Self:
        return self

    @property
    def _type_name(self) -> str:
        return type(self).__name__

    def _normalize(self) -> None:
        # Хук: подкласс приводит поля к каноническому виду через `_set`.
        pass

    def _validate(self) -> None:
        # Хук: подкласс проверяет инварианты уже нормализованных полей.
        pass

    def _set(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)


def _require_fields(cls: type[Any]) -> None:
    if not fields(cls):
        raise TypeError(f"{cls.__name__} must have at least one field")
