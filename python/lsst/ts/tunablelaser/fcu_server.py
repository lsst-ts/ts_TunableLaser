import asyncio
from enum import StrEnum

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from .fcu_client import Output
from .wizardry import FCU_SERVER_START_ITERATIONS, FCU_SERVER_START_SLEEP


class State(StrEnum):
    """The states sent by the server."""

    idle = "Idle"
    running = "Running"
    not_initialized = "NotInitialized"
    unsuccessful = "unsuccessful"


class CommandHandler:
    """Handle REST/HTTP_CMD requests for the FCU simulator."""

    async def get_state(self, request: Request) -> HTMLResponse:
        """Return the simulated FCU state.

        Parameters
        ----------
        request : `fastapi.Request`
            Incoming request carrying application state.

        Returns
        -------
        response : `fastapi.responses.HTMLResponse`
            FCU-compatible state response.
        """
        return HTMLResponse(
            content=f"""0<br>"{request.app.state.state}" <br> string""",
            media_type="text/html",
        )

    async def get_output(self, request: Request) -> HTMLResponse:
        """Return the simulated FCU output.

        Parameters
        ----------
        request : `fastapi.Request`
            Incoming request carrying application state.

        Returns
        -------
        response : `fastapi.responses.HTMLResponse`
            FCU-compatible output response.
        """
        return HTMLResponse(
            content=f"0<br>'{request.app.state.output.value}' <br> string",
            media_type="text/html",
        )

    async def set_output(self, request: Request, output: str) -> HTMLResponse:
        """Set the simulated FCU output.

        Parameters
        ----------
        request : `fastapi.Request`
            Incoming request carrying application state.
        output : `str`
            Output channel requested by the command.

        Returns
        -------
        response : `fastapi.responses.HTMLResponse`
            FCU-compatible command response.
        """
        response = HTMLResponse(
            content="0<br><a href=''>Check status</a>",
            media_type="text/html",
        )

        try:
            request.app.state.output = Output(output)
        except ValueError:
            return response

        return response

    async def dispatch(self, request: Request) -> HTMLResponse:
        """Dispatch an FCU REST/HTTP_CMD request.

        Parameters
        ----------
        request : `fastapi.Request`
            Incoming REST/HTTP_CMD request.

        Returns
        -------
        response : `fastapi.responses.HTMLResponse` or
                `fastapi.responses.PlainTextResponse`
            Response for the requested FCU command.
        """
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
    """Small HTTP server that emulates the FCU REST interface.

    Parameters
    ----------
    host : `str`, optional
        Host interface to bind.
    port : `int`, optional
        TCP port to bind. Use ``0`` to request an ephemeral port.
    """

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
            """Dispatch one FCU REST command.

            Parameters
            ----------
            request : `fastapi.Request`
                Incoming HTTP request.

            Returns
            -------
            response : `fastapi.responses.HTMLResponse`
                FCU-compatible response.
            """
            return await self.handler.dispatch(request)

        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start the FCU simulator server."""
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
        for _ in range(FCU_SERVER_START_ITERATIONS):
            if getattr(self._server, "started", False):
                self.port = self._server.servers[0].sockets[0].getsockname()[1]
                break
            await asyncio.sleep(FCU_SERVER_START_SLEEP)

    async def stop(self):
        """Stop the FCU simulator server."""
        if not self._server:
            return

        self._server.should_exit = True

        if self._task:
            await self._task

        self._server = None
        self._task = None


def create_app(**kwargs):
    """Create a FastAPI application for the FCU simulator.

    Parameters
    ----------
    **kwargs
        Keyword arguments forwarded to `RestHttpCmdServer`.

    Returns
    -------
    app : `fastapi.FastAPI`
        Configured application instance.
    """
    server = RestHttpCmdServer(**kwargs)
    return server.app
