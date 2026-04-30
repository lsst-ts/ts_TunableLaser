from enum import StrEnum

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .wizardry import MOCK_FCU_PORT, REAL_FCU_PORT


class Output(StrEnum):
    """The output values accepted by the server."""

    out1 = "Out1"
    out2 = "Out2"
    out3 = "Out3"


class FCUClient:
    """Implement the FCU Client.

    Parameters
    ----------
    simulation_mode : `int`
        Use ``0`` for the real FCU and any nonzero value for the simulator.
    """

    def __init__(self, simulation_mode: int = 0):
        self.simulation_mode = simulation_mode
        self.output = None
        match self.simulation_mode:
            case 0:
                self.host = "laser-fcu.cp.lsst.org"
                self.port = REAL_FCU_PORT
            case _:
                self.host = "localhost"
                self.port = MOCK_FCU_PORT

    @property
    def base_url(self) -> str:
        """Base URL for REST/HTTP_CMD requests.

        Returns
        -------
        url : `str`
            URL prefix used by the FCU HTTP API.
        """
        return f"http://{self.host}:{self.port}/REST/HTTP_CMD/"

    @staticmethod
    def make_soup(text) -> BeautifulSoup:
        """Make the BeautifulSoup parser.

        Parameters
        ----------
        text : `str`
            HTML response body to parse.

        Returns
        -------
        soup : `bs4.BeautifulSoup`
            The parser.
        """
        return BeautifulSoup(text, features="lxml")

    async def set_output(self, out: Output) -> str:
        """Set the FCU output.

        Parameters
        ----------
        out : `Output` or `str`
            Output channel to select.

        Returns
        -------
        result : `str`
            FCU command result string.

        Raises
        ------
        ValueError
            Raised if ``out`` is not a valid `Output`.
        """
        out = Output(out)
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get(f"?EXE/SetOutput/{out}") as resp:
                text = await resp.text()
        self.output = out
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        return parts[1]

    async def get_state(self) -> str:
        """Get the FCU state.

        Returns
        -------
        state : `str`
            Current FCU state string.
        """
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get("?RDVAR/State") as resp:
                text = await resp.text()
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        return parts[1].strip('" ')

    async def get_output(self) -> str:
        """Get the selected FCU output.

        Returns
        -------
        output : `str`
            Current output channel name.

        Raises
        ------
        ValueError
            Raised if the FCU returns an output string that is not a valid
            `Output`.
        """
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get("?RDVAR/Output") as resp:
                text = await resp.text()
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        output = parts[1].strip("' ")
        self.output = Output(output)
        return output
