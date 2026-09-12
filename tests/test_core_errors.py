from telefeeds import TelegramRPCError


def test_rpc_error_message_preserves_parameter_position() -> None:
    assert (
        TelegramRPCError(400, "FILE_PART_MISSING", 3).message == "FILE_PART_3_MISSING"
    )
    assert TelegramRPCError(303, "FILE_MIGRATE", 4).message == "FILE_MIGRATE_4"
    assert (
        TelegramRPCError(500, "INTERDC_CALL_ERROR", 2).message == "INTERDC_2_CALL_ERROR"
    )
