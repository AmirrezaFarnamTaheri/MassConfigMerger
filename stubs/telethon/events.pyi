from typing import Any

class NewMessage:
    class Event:
        message: str
        sender_id: int
        async def respond(self, message: str) -> Any: ...
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
