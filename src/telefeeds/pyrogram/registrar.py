from __future__ import annotations

import asyncio
import inspect
import logging
from collections import OrderedDict
from collections.abc import Callable, Iterator
from typing import Any

import pyrogram
from pyrogram import handlers

log = logging.getLogger(__name__)
ErrorHandlerType = getattr(handlers, "ErrorHandler", type(None))


class HandlerRegistrar:
    """Stores Pyrogram handlers and can include reusable child routers."""

    def __init__(self, *, name: str | None = None) -> None:
        self.name = name or type(self).__name__
        self.groups: OrderedDict[int, list[Any]] = OrderedDict()
        self.routers: list[Router] = []
        self.parent: HandlerRegistrar | None = None

    def add_handler(self, handler: Any, group: int = 0) -> Any:
        self.groups.setdefault(group, []).append(handler)
        self.groups = OrderedDict(sorted(self.groups.items()))
        return handler

    def remove_handler(self, handler: Any, group: int = 0) -> None:
        group_handlers = self.groups.get(group)
        if group_handlers is None:
            return
        group_handlers.remove(handler)
        if not group_handlers:
            del self.groups[group]

    def include_router(self, router: Router) -> HandlerRegistrar:
        if router is self:
            raise ValueError("a registrar cannot include itself")
        parent = self
        while parent is not None:
            if parent is router:
                raise ValueError("router inclusion would create a cycle")
            parent = parent.parent
        if router.parent is not None:
            raise ValueError(f"router {router.name!r} is already included")
        router.parent = self
        self.routers.append(router)
        return self

    def include_routers(self, *routers: Router) -> HandlerRegistrar:
        for router in routers:
            self.include_router(router)
        return self

    def iter_registrars(self) -> Iterator[HandlerRegistrar]:
        yield self
        for router in self.routers:
            yield from router.iter_registrars()

    def grouped_handlers(self) -> OrderedDict[int, list[Any]]:
        grouped: dict[int, list[Any]] = {}
        for registrar in self.iter_registrars():
            for group, group_handlers in registrar.groups.items():
                grouped.setdefault(group, []).extend(group_handlers)
        return OrderedDict(sorted(grouped.items()))

    def decorator(self, handler_type: type, filters: Any, group: int) -> Callable:
        def register(callback: Callable) -> Callable:
            handler = (
                handler_type(callback)
                if filters is None
                else handler_type(callback, filters)
            )
            self.add_handler(handler, group)
            return callback

        return register

    def lifecycle_decorator(self, handler_type: type, group: int) -> Callable:
        def register(callback: Callable) -> Callable:
            self.add_handler(handler_type(callback), group)
            return callback

        return register

    def on_message(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.MessageHandler, filters, group)

    def on_edited_message(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.EditedMessageHandler, filters, group)

    def on_deleted_messages(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.DeletedMessagesHandler, filters, group)

    def on_callback_query(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.CallbackQueryHandler, filters, group)

    def on_user_status(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.UserStatusHandler, filters, group)

    def on_inline_query(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.InlineQueryHandler, filters, group)

    def on_poll(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.PollHandler, filters, group)

    def on_chosen_inline_result(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ChosenInlineResultHandler, filters, group)

    def on_chat_member_updated(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ChatMemberUpdatedHandler, filters, group)

    def on_chat_join_request(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ChatJoinRequestHandler, filters, group)

    def on_story(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.StoryHandler, filters, group)

    def on_pre_checkout_query(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.PreCheckoutQueryHandler, filters, group)

    def on_shipping_query(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ShippingQueryHandler, filters, group)

    def on_message_reaction(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.MessageReactionHandler, filters, group)

    def on_message_reaction_count(
        self, filters: Any = None, group: int = 0
    ) -> Callable:
        return self.decorator(handlers.MessageReactionCountHandler, filters, group)

    def on_chat_boost(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ChatBoostHandler, filters, group)

    def on_purchased_paid_media(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.PurchasedPaidMediaHandler, filters, group)

    def on_business_connection(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.BusinessConnectionHandler, filters, group)

    def on_business_message(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.BusinessMessageHandler, filters, group)

    def on_edited_business_message(
        self, filters: Any = None, group: int = 0
    ) -> Callable:
        return self.decorator(handlers.EditedBusinessMessageHandler, filters, group)

    def on_deleted_business_messages(
        self, filters: Any = None, group: int = 0
    ) -> Callable:
        return self.decorator(handlers.DeletedBusinessMessagesHandler, filters, group)

    def on_managed_bot(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.ManagedBotUpdatedHandler, filters, group)

    def on_guest_message(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.GuestMessageHandler, filters, group)

    def on_raw_update(self, filters: Any = None, group: int = 0) -> Callable:
        return self.decorator(handlers.RawUpdateHandler, filters, group)

    def on_error(
        self,
        exceptions: Exception
        | tuple[type[Exception], ...]
        | type[Exception]
        | None = None,
        filters: Any = None,
        group: int = 0,
    ) -> Callable:
        if not hasattr(handlers, "ErrorHandler"):
            raise NotImplementedError(
                "the installed pyrogram package has no ErrorHandler"
            )

        def register(callback: Callable) -> Callable:
            self.add_handler(
                handlers.ErrorHandler(callback, exceptions, filters), group
            )
            return callback

        return register

    def on_start(self, group: int = 0) -> Callable:
        handler_type = getattr(handlers, "StartHandler", None)
        if handler_type is None:
            raise NotImplementedError(
                "the installed pyrogram package has no StartHandler"
            )
        return self.lifecycle_decorator(handler_type, group)

    def on_stop(self, group: int = 0) -> Callable:
        handler_type = getattr(handlers, "StopHandler", None)
        if handler_type is None:
            raise NotImplementedError(
                "the installed pyrogram package has no StopHandler"
            )
        return self.lifecycle_decorator(handler_type, group)

    def on_connect(self, group: int = 0) -> Callable:
        handler_type = getattr(handlers, "ConnectHandler", None)
        if handler_type is None:
            raise NotImplementedError(
                "the installed pyrogram package has no ConnectHandler"
            )
        return self.lifecycle_decorator(handler_type, group)

    def on_disconnect(self, group: int = 0) -> Callable:
        handler_type = getattr(handlers, "DisconnectHandler", None)
        if handler_type is None:
            raise NotImplementedError(
                "the installed pyrogram package has no DisconnectHandler"
            )
        return self.lifecycle_decorator(handler_type, group)

    async def resolve(
        self,
        client: pyrogram.Client,
        update: Any,
        users: dict[int, Any] | None = None,
        chats: dict[int, Any] | None = None,
    ) -> None:
        users = users or {}
        chats = chats or {}
        parser = client.dispatcher.update_parsers.get(type(update))
        if parser is None:
            parsed_update, handler_type = None, type(None)
        else:
            parsed_update, handler_type = await parser(update, users, chats)

        for group_handlers in self.grouped_handlers().values():
            for handler in group_handlers:
                if isinstance(handler, ErrorHandlerType):
                    continue
                args: tuple[Any, ...] | None = None
                try:
                    if isinstance(handler, handler_type):
                        if await handler.check(client, parsed_update):
                            args = (parsed_update,)
                    elif isinstance(
                        handler, handlers.RawUpdateHandler
                    ) and await handler.check(client, update):
                        args = (update, users, chats)
                except Exception:
                    log.exception("Telefeeds handler filter failed")
                    continue
                if args is None:
                    continue
                try:
                    if inspect.iscoroutinefunction(handler.callback):
                        await handler.callback(client, *args)
                    else:
                        await asyncio.to_thread(handler.callback, client, *args)
                except pyrogram.StopPropagation:
                    return
                except pyrogram.ContinuePropagation:
                    continue
                except Exception as error:  # noqa: BLE001
                    await self.resolve_error(
                        error, handler, client, update, users, chats
                    )
                break

    async def resolve_error(
        self,
        error: Exception,
        source_handler: Any,
        client: pyrogram.Client,
        update: Any,
        users: dict[int, Any],
        chats: dict[int, Any],
    ) -> None:
        handled = False
        for group_handlers in self.grouped_handlers().values():
            for handler in group_handlers:
                if not isinstance(handler, ErrorHandlerType):
                    continue
                if not isinstance(error, handler.exceptions):
                    continue
                handled = True
                try:
                    if inspect.iscoroutinefunction(handler.callback):
                        await handler.callback(
                            client, error, source_handler, update, users, chats
                        )
                    else:
                        await asyncio.to_thread(
                            handler.callback,
                            client,
                            error,
                            source_handler,
                            update,
                            users,
                            chats,
                        )
                except pyrogram.StopPropagation:
                    return
                except pyrogram.ContinuePropagation:
                    continue
                except Exception:
                    log.exception("Telefeeds error handler failed")
                break
        if not handled:
            log.error(
                "Unhandled exception in %s",
                type(source_handler).__name__,
                exc_info=(type(error), error, error.__traceback__),
            )

    async def emit_lifecycle(
        self,
        client: pyrogram.Client,
        handler_type: type,
        *args: Any,
    ) -> None:
        for group_handlers in self.grouped_handlers().values():
            for handler in group_handlers:
                if not isinstance(handler, handler_type):
                    continue
                if inspect.iscoroutinefunction(handler.callback):
                    await handler.callback(client, *args)
                else:
                    await asyncio.to_thread(handler.callback, client, *args)
                break


class Router(HandlerRegistrar):
    pass
