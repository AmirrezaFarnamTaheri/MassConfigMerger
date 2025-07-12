from typing import Any

class Message:
    message: str
    async def respond(self, text: str) -> Any: ...
