import grpc

from telefeeds import (
    AuthorizationConcurrentLimitError,
    AuthorizationError,
    AuthorizationErrorCode,
    GatewayError,
    GatewayErrorCode,
    InvalidAuthorizationCodeError,
    InvalidAuthorizationPasswordError,
    RateLimitExceededError,
    TelefeedsError,
    TelegramRPCError,
)
from telefeeds._core.client import gateway_error


def test_rpc_error_message_preserves_parameter_position() -> None:
    assert (
        TelegramRPCError(400, "FILE_PART_MISSING", 3).message == "FILE_PART_3_MISSING"
    )
    assert TelegramRPCError(303, "FILE_MIGRATE", 4).message == "FILE_MIGRATE_4"
    assert (
        TelegramRPCError(500, "INTERDC_CALL_ERROR", 2).message == "INTERDC_2_CALL_ERROR"
    )


def test_gateway_error_does_not_expose_grpc_types() -> None:
    error = gateway_error(
        grpc.aio.AioRpcError(
            grpc.StatusCode.INVALID_ARGUMENT,
            details="code is invalid",
        )
    )

    assert isinstance(error, GatewayError)
    assert isinstance(error, TelefeedsError)
    assert error.code == GatewayErrorCode.INVALID_ARGUMENT
    assert error.details == "code is invalid"


def test_gateway_error_maps_authorization_machine_codes_to_specific_errors() -> None:
    password_error = gateway_error(
        grpc.aio.AioRpcError(
            grpc.StatusCode.INVALID_ARGUMENT,
            trailing_metadata=grpc.aio.Metadata(
                (
                    "telefeeds-error-code",
                    "AUTHORIZATION_ERROR_CODE_PASSWORD_INVALID",
                )
            ),
            details="invalid Telegram 2FA password",
        )
    )
    code_error = gateway_error(
        grpc.aio.AioRpcError(
            grpc.StatusCode.INVALID_ARGUMENT,
            trailing_metadata=grpc.aio.Metadata(
                (
                    "telefeeds-error-code",
                    "AUTHORIZATION_ERROR_CODE_CODE_INVALID",
                )
            ),
            details="invalid Telegram authorization code",
        )
    )

    assert type(password_error) is InvalidAuthorizationPasswordError
    assert isinstance(password_error, AuthorizationError)
    assert password_error.reason is AuthorizationErrorCode.PASSWORD_INVALID
    assert type(code_error) is InvalidAuthorizationCodeError
    assert code_error.reason is AuthorizationErrorCode.CODE_INVALID


def test_gateway_error_maps_service_and_authorization_limits() -> None:
    authorization_error = gateway_error(
        grpc.aio.AioRpcError(
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            trailing_metadata=grpc.aio.Metadata(
                (
                    "telefeeds-error-code",
                    "AUTHORIZATION_ERROR_CODE_CONCURRENT_LIMIT",
                )
            ),
            details="too many authorization attempts",
        )
    )
    rate_error = gateway_error(
        grpc.aio.AioRpcError(
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            trailing_metadata=grpc.aio.Metadata(
                ("telefeeds-error-code", "RATE_LIMIT_ERROR_CODE_EXCEEDED")
            ),
            details="request rate limit exceeded",
        )
    )

    assert type(authorization_error) is AuthorizationConcurrentLimitError
    assert type(rate_error) is RateLimitExceededError
