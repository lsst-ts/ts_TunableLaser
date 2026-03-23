import asyncio
from enum import StrEnum

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from .fcu_client import Output


class State(StrEnum):
    """The states sent by the server."""

    idle = "Idle"
    running = "Running"
    not_initialized = "NotInitialized"
    unsuccessful = "unsuccessful"


class CommandHandler:
    async def get_state(self, request: Request) -> HTMLResponse:
        """Return the state."""
        return HTMLResponse(
            content=f"""<p>0<br>"{request.app.state.state}" <br> string</p>""",
            media_type="text/html",
        )

    async def get_output(self, request: Request) -> HTMLResponse:
        """Return the output."""
        return HTMLResponse(
            content=f"<p>0<br>'{request.app.state.output.value}' <br> string</p>",
            media_type="text/html",
        )

    async def set_output(self, request: Request, output: str) -> HTMLResponse:
        """Set the output."""
        response = HTMLResponse(
            content="<p>0<br><a href=''>Check status</a></p>",
            media_type="text/html",
        )

        try:
            request.app.state.output = Output(output)
        except ValueError:
            return response

        return response

    async def dispatch(self, request: Request) -> HTMLResponse:
        """Use the query string to determine which command has been sent."""
        cmd = (request.url.query or "").strip()
        parts = cmd.split("/") if cmd else []

        match parts:
            case ["RDVAR", subcommand]:
                match subcommand:
                    case "State":
                        return await self.get_state(request)

                    case "Output":
                        return await self.get_output(request)

                    case _:
                        return HTMLResponse(
                            content="510<br>There is no such variable",
                            media_type="text/html",
                        )

            case ["EXE", "SetOutput", value]:
                return await self.set_output(request, value)

            case _:
                return PlainTextResponse(
                    content=f"Unknown command: {cmd!r}",
                    status_code=404,
                )


class RestHttpCmdServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port

        self.app = FastAPI()
        self.handler = CommandHandler()

        # emulate aiohttp request.app state storage
        self.app.state.state = State.idle
        self.app.state.output = Output.out1

        @self.app.get("/REST/HTTP_CMD/", response_class=HTMLResponse)
        async def rest_http_cmd(request: Request):
            return await self.handler.dispatch(request)

        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    async def start(self):
        if self._task and not self._task.done():
            return

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())

        # wait for startup
        for _ in range(100):
            if getattr(self._server, "started", False):
                break
            await asyncio.sleep(0.01)

    async def stop(self):
        if not self._server:
            return

        self._server.should_exit = True

        if self._task:
            await self._task

        self._server = None
        self._task = None


def create_app(**kwargs):
    server = RestHttpCmdServer(**kwargs)
    return server.app
