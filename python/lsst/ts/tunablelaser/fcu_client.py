from enum import StrEnum

from aiohttp import ClientSession
from bs4 import BeautifulSoup


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
        Connect to the real server?
    """

    def __init__(self, simulation_mode: int = 0):
        self.simulation_mode = simulation_mode
        self.output = None
        match self.simulation_mode:
            case 0:
                self.host = "laser-fcu.cp.lsst.org"
                self.port = 8081
            case _:
                self.host = "localhost"
                self.port = 17000

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/REST/HTTP_CMD/"

    @staticmethod
    def make_soup(text) -> BeautifulSoup:
        """Make the BeautifulSoup parser.

        Returns
        -------
        BeautifulSoup
            The parser.
        """
        return BeautifulSoup(text, features="lxml")

    async def set_output(self, out: Output) -> str:
        """Set the output and return the result."""
        out = Output(out)
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get(f"?EXE/SetOutput/{out}") as resp:
                text = await resp.text()
        self.output = out
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        return parts[1]

    async def get_state(self) -> str:
        """Get the state."""
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get("?RDVAR/State") as resp:
                text = await resp.text()
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        return parts[1].strip('" ')

    async def get_output(self) -> str:
        """Get the output."""
        async with ClientSession(base_url=self.base_url) as session:
            async with session.get("?RDVAR/Output") as resp:
                text = await resp.text()
        soup = self.make_soup(text)
        parts = list(soup.stripped_strings)
        output = parts[1].strip("' ")
        self.output = Output(output)
        return output
