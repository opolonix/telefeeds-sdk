import asyncio
import os
from getpass import getpass

from telefeeds import AuthorizationState, TelefeedsClient


async def main() -> None:
    client = TelefeedsClient(
        token=os.environ["TELEFEEDS_TOKEN"],
        endpoint=os.getenv("TELEFEEDS_ENDPOINT", "telegram.telefeeds.ru:443"),
    )
    async with client:
        phone_number = input("Номер телефона в международном формате: ").strip()
        challenge = await client.begin_phone_authorization(phone_number)
        print(f"Код отправлен, запрос действует до {challenge.expires_at}")

        code = input("Код из Telegram: ").strip()
        result = await client.complete_phone_authorization(
            challenge.authorization_id,
            code,
        )

        if result.state == AuthorizationState.PASSWORD_REQUIRED:
            if result.password_hint:
                print(f"Подсказка пароля: {result.password_hint}")
            session = await client.complete_password_authorization(
                challenge.authorization_id,
                getpass("Пароль двухэтапной аутентификации: "),
            )
        elif result.state == AuthorizationState.AUTHORIZED and result.session:
            session = result.session
        else:
            raise RuntimeError(
                f"Неожиданное состояние авторизации: {result.state.name}"
            )

        print(
            f"Сессия зарегистрирована: peer_id={session.session_peer_id}, "
            f"state={session.state}"
        )


if __name__ == "__main__":
    asyncio.run(main())
