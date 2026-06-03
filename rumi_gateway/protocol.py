"""JSON-RPC 2.0 message types for RUMI gateway."""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class JsonRpcRequest:
    jsonrpc: str = "2.0"
    id: int | str | None = 0
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "JsonRpcRequest":
        obj = json.loads(data)
        if "method" not in obj:
            raise ValueError("Missing required field 'method' in JSON-RPC request")
        return cls(
            jsonrpc=obj.get("jsonrpc", "2.0"),
            id=obj.get("id", 0),
            method=obj["method"],
            params=obj.get("params", {}),
        )


@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    id: int | str | None = 0
    result: Any = None
    error: Optional[dict[str, Any]] = None

    def to_json(self) -> str:
        d = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error
        else:
            d["result"] = self.result
        return json.dumps(d, ensure_ascii=False)


@dataclass
class JsonRpcEvent:
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {"jsonrpc": self.jsonrpc, "method": self.method, "params": self.params},
            ensure_ascii=False,
        )


_active_websocket = None


def set_websocket(ws):
    """Set the active WebSocket connection for event delivery."""
    global _active_websocket
    _active_websocket = ws


def send_message(msg: JsonRpcResponse | JsonRpcEvent) -> None:
    """Write a JSON-RPC message to active WebSocket or stdout. Flush immediately."""
    if _active_websocket is not None:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_active_websocket.send(msg.to_json()))
        except RuntimeError:
            pass
    else:
        sys.stdout.write(msg.to_json() + "\n")
        sys.stdout.flush()


def log_error(message: str) -> None:
    """Write a log line to stderr (kept out of protocol stream)."""
    sys.stderr.write(f"[gateway] {message}\n")
    sys.stderr.flush()
