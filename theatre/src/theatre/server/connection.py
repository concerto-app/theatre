from asyncio import AbstractEventLoop
from typing import List, Optional, Union

from aiortc import (
    InvalidStateError,
    RTCDataChannel,
    RTCPeerConnection,
    RTCSessionDescription,
)
from pyee.asyncio import AsyncIOEventEmitter

from theatre.models.data import Session


class Connection(AsyncIOEventEmitter):
    _peer_connection: RTCPeerConnection
    _channels: List[RTCDataChannel] = []

    def __init__(
        self,
        peer_connection: RTCPeerConnection,
        loop: Optional[AbstractEventLoop] = None,
    ):
        super().__init__(loop)
        self._peer_connection = peer_connection

        @self._peer_connection.on("datachannel")
        def on_datachannel(channel: RTCDataChannel) -> None:
            self._channels.append(channel)

            if channel.readyState == "open":
                self.emit("connected")

            @channel.on("open")
            def on_open() -> None:
                self.emit("connected")

            @channel.on("close")
            def on_closing() -> None:
                self.emit("disconnected")

            @channel.on("message")
            def on_message(message: Union[bytes, str]) -> None:
                self.emit("data", message)

    @classmethod
    async def new(
        cls, session: Session, loop: Optional[AbstractEventLoop] = None
    ) -> "Connection":
        peer_connection = RTCPeerConnection()
        await peer_connection.setRemoteDescription(
            RTCSessionDescription(sdp=session.description, type="offer")
        )
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)
        return cls(peer_connection, loop)

    @property
    def session(self) -> Session:
        return Session(description=self._peer_connection.localDescription.sdp)

    def send(self, data: Union[str, bytes]) -> None:
        for channel in self._channels:
            try:
                channel.send(data)
            except (InvalidStateError, ConnectionError):
                pass

    async def close(self) -> None:
        await self._peer_connection.close()
