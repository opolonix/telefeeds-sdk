try:
    import pyrogram as pyrogram
except ImportError as error:
    raise ImportError(
        "telefeeds.pyrogram uses the installed package that provides the 'pyrogram' namespace. "
        "Install the implementation you want, for example: pip install kurigram"
    ) from error

from .app import Telefeeds
from .registrar import HandlerRegistrar, Router

__all__ = ["HandlerRegistrar", "Router", "Telefeeds"]
