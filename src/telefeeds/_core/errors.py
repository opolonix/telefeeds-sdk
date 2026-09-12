from __future__ import annotations


class GatewayInvokeError(RuntimeError):
    """A request reached Telefeeds but failed before Telegram returned an RPC error."""


class SubscriptionReplacedError(RuntimeError):
    """The update subscription was explicitly replaced through close_other."""


class TelegramRPCError(RuntimeError):
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
