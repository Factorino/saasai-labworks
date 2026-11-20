import secrets
import time
from typing import ClassVar, cast, override
from uuid import UUID

from anamnesis.application.interfaces.common.id_generator import IIdGenerator


class UUIDv7Generator[IdT: UUID](IIdGenerator[IdT]):
    _VERSION: ClassVar[int] = 7
    _VARIANT: ClassVar[int] = 0b10

    _TIMESTAMP_BITS: ClassVar[int] = 48
    _VERSION_BITS: ClassVar[int] = 4
    _RAND_A_BITS: ClassVar[int] = 12
    _VARIANT_BITS: ClassVar[int] = 2
    _RAND_B_BITS: ClassVar[int] = 62

    _VARIANT_SHIFT: ClassVar[int] = _RAND_B_BITS
    _RAND_A_SHIFT: ClassVar[int] = _VARIANT_SHIFT + _VARIANT_BITS
    _VERSION_SHIFT: ClassVar[int] = _RAND_A_SHIFT + _RAND_A_BITS
    _TIMESTAMP_SHIFT: ClassVar[int] = _VERSION_SHIFT + _VERSION_BITS

    _NS_IN_MS: ClassVar[int] = 1_000_000

    @classmethod
    def _uuid7(cls) -> UUID:
        timestamp_ms: int = time.time_ns() // cls._NS_IN_MS
        value: int = (timestamp_ms & ((1 << cls._TIMESTAMP_BITS) - 1)) << cls._TIMESTAMP_SHIFT
        value |= cls._VERSION << cls._VERSION_SHIFT
        value |= secrets.randbits(cls._RAND_A_BITS) << cls._RAND_A_SHIFT
        value |= cls._VARIANT << cls._VARIANT_SHIFT
        value |= secrets.randbits(cls._RAND_B_BITS)
        return UUID(int=value)

    @override
    def generate(self) -> IdT:
        return cast("IdT", self._uuid7())
