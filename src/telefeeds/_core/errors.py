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


class AuthorizationErrorCode(str, Enum):
    CREDENTIALS_REQUIRED = "AUTHORIZATION_ERROR_CODE_CREDENTIALS_REQUIRED"
    CREDENTIALS_INVALID = "AUTHORIZATION_ERROR_CODE_CREDENTIALS_INVALID"
    ATTEMPT_INVALID = "AUTHORIZATION_ERROR_CODE_ATTEMPT_INVALID"
    ATTEMPT_NOT_FOUND = "AUTHORIZATION_ERROR_CODE_ATTEMPT_NOT_FOUND"
    ATTEMPT_FORBIDDEN = "AUTHORIZATION_ERROR_CODE_ATTEMPT_FORBIDDEN"
    ATTEMPT_EXPIRED = "AUTHORIZATION_ERROR_CODE_ATTEMPT_EXPIRED"
    PHONE_INVALID = "AUTHORIZATION_ERROR_CODE_PHONE_INVALID"
    PHONE_BANNED = "AUTHORIZATION_ERROR_CODE_PHONE_BANNED"
    CODE_INVALID = "AUTHORIZATION_ERROR_CODE_CODE_INVALID"
    CODE_EXPIRED = "AUTHORIZATION_ERROR_CODE_CODE_EXPIRED"
    PASSWORD_INVALID = "AUTHORIZATION_ERROR_CODE_PASSWORD_INVALID"
    PASSWORD_NOT_EXPECTED = "AUTHORIZATION_ERROR_CODE_PASSWORD_NOT_EXPECTED"
    SIGN_UP_REQUIRED = "AUTHORIZATION_ERROR_CODE_SIGN_UP_REQUIRED"
    SESSION_ACCESS_DISABLED = "AUTHORIZATION_ERROR_CODE_SESSION_ACCESS_DISABLED"
    PROVIDER_UNAVAILABLE = "AUTHORIZATION_ERROR_CODE_PROVIDER_UNAVAILABLE"
    PERMISSION_DENIED = "AUTHORIZATION_ERROR_CODE_PERMISSION_DENIED"
    RATE_LIMITED = "AUTHORIZATION_ERROR_CODE_RATE_LIMITED"
    CONCURRENT_LIMIT = "AUTHORIZATION_ERROR_CODE_CONCURRENT_LIMIT"


class GatewayError(TelefeedsError):
    """A structured ClientHub error independent of grpcio types."""

    def __init__(
        self,
        code: GatewayErrorCode,
        details: str,
        retry_after: float | None = None,
    ) -> None:
        self.code = code
        self.details = details
        self.retry_after = retry_after
        super().__init__(f"[{code.value}] {details}".rstrip())


class AuthorizationError(GatewayError):
    """Base exception for expected user-session authorization failures."""

    reason: AuthorizationErrorCode


class AuthorizationCredentialsRequiredError(AuthorizationError):
    reason = AuthorizationErrorCode.CREDENTIALS_REQUIRED


class InvalidAuthorizationCredentialsError(AuthorizationError):
    reason = AuthorizationErrorCode.CREDENTIALS_INVALID


class InvalidAuthorizationAttemptError(AuthorizationError):
    reason = AuthorizationErrorCode.ATTEMPT_INVALID


class AuthorizationAttemptNotFoundError(AuthorizationError):
    reason = AuthorizationErrorCode.ATTEMPT_NOT_FOUND


class AuthorizationAttemptForbiddenError(AuthorizationError):
    reason = AuthorizationErrorCode.ATTEMPT_FORBIDDEN


class AuthorizationAttemptExpiredError(AuthorizationError):
    reason = AuthorizationErrorCode.ATTEMPT_EXPIRED


class InvalidAuthorizationPhoneError(AuthorizationError):
    reason = AuthorizationErrorCode.PHONE_INVALID


class BannedAuthorizationPhoneError(AuthorizationError):
    reason = AuthorizationErrorCode.PHONE_BANNED


class InvalidAuthorizationCodeError(AuthorizationError):
    reason = AuthorizationErrorCode.CODE_INVALID


class ExpiredAuthorizationCodeError(AuthorizationError):
    reason = AuthorizationErrorCode.CODE_EXPIRED


class InvalidAuthorizationPasswordError(AuthorizationError):
    reason = AuthorizationErrorCode.PASSWORD_INVALID


class AuthorizationPasswordNotExpectedError(AuthorizationError):
    reason = AuthorizationErrorCode.PASSWORD_NOT_EXPECTED


class AuthorizationSignUpRequiredError(AuthorizationError):
    reason = AuthorizationErrorCode.SIGN_UP_REQUIRED


class UserSessionAccessDisabledError(AuthorizationError):
    reason = AuthorizationErrorCode.SESSION_ACCESS_DISABLED


class AuthorizationProviderUnavailableError(AuthorizationError):
    reason = AuthorizationErrorCode.PROVIDER_UNAVAILABLE


class AuthorizationPermissionDeniedError(AuthorizationError):
    reason = AuthorizationErrorCode.PERMISSION_DENIED


class AuthorizationRateLimitedError(AuthorizationError):
    reason = AuthorizationErrorCode.RATE_LIMITED


class AuthorizationConcurrentLimitError(AuthorizationError):
    reason = AuthorizationErrorCode.CONCURRENT_LIMIT


class RateLimitExceededError(GatewayError):
    """A ClientHub request or concurrency limit has been reached."""


AUTHORIZATION_ERROR_TYPES: dict[str, type[AuthorizationError]] = {
    error_type.reason.value: error_type
    for error_type in (
        AuthorizationCredentialsRequiredError,
        InvalidAuthorizationCredentialsError,
        InvalidAuthorizationAttemptError,
        AuthorizationAttemptNotFoundError,
        AuthorizationAttemptForbiddenError,
        AuthorizationAttemptExpiredError,
        InvalidAuthorizationPhoneError,
        BannedAuthorizationPhoneError,
        InvalidAuthorizationCodeError,
        ExpiredAuthorizationCodeError,
        InvalidAuthorizationPasswordError,
        AuthorizationPasswordNotExpectedError,
        AuthorizationSignUpRequiredError,
        UserSessionAccessDisabledError,
        AuthorizationProviderUnavailableError,
        AuthorizationPermissionDeniedError,
        AuthorizationRateLimitedError,
        AuthorizationConcurrentLimitError,
    )
}

GATEWAY_ERROR_TYPES: dict[str, type[GatewayError]] = {
    **AUTHORIZATION_ERROR_TYPES,
    "RATE_LIMIT_ERROR_CODE_EXCEEDED": RateLimitExceededError,
}


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
