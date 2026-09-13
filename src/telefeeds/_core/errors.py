from __future__ import annotations

from enum import Enum


class TelefeedsError(RuntimeError):
    """Base exception for errors exposed by the Telefeeds SDK."""


class GatewayErrorCode(str, Enum):
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    INTERNAL = "INTERNAL"
    UNAVAILABLE = "UNAVAILABLE"
    DATA_LOSS = "DATA_LOSS"
    UNAUTHENTICATED = "UNAUTHENTICATED"


class GatewayError(TelefeedsError):
    """A structured ClientHub error independent of grpcio types."""

    def __init__(self, code: GatewayErrorCode, details: str) -> None:
        self.code = code
        self.details = details
        super().__init__(f"[{code.value}] {details}".rstrip())


class GatewayInvokeError(TelefeedsError):
    """A request reached Telefeeds but failed before Telegram returned an RPC error."""


class SubscriptionReplacedError(TelefeedsError):
    """The update subscription was explicitly replaced through close_other."""


class TelegramRPCError(TelefeedsError):
    """A structured Telegram RPC error independent of a particular TL library."""

    def __init__(
        self,
        code: int,
        name: str,
        value: int | None = None,
        caused_by: int | None = None,
    ) -> None:
        self.code = code
        self.name = name
        self.value = value
        self.caused_by = caused_by
        super().__init__(f"[{code} {self.message}]")

    @property
    def message(self) -> str:
        if self.value is None:
            return self.name
        if self.name == "FILE_PART_MISSING":
            return f"FILE_PART_{self.value}_MISSING"
        if self.name.startswith("INTERDC_CALL"):
            return self.name.replace("INTERDC", f"INTERDC_{self.value}", 1)
        return f"{self.name}_{self.value}"
