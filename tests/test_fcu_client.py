import socket
import unittest

from lsst.ts.tunablelaser.fcu_client import FCUClient, Output
from lsst.ts.tunablelaser.fcu_server import RestHttpCmdServer, State


def get_unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestFCUClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.port = get_unused_port()
        self.server = RestHttpCmdServer(host="127.0.0.1", port=self.port)
        await self.server.start()

        self.client = FCUClient(simulation_mode=1)
        self.client.base_url = f"http://127.0.0.1:{self.port}/REST/HTTP_CMD/"

    async def asyncTearDown(self) -> None:
        await self.server.stop()

    async def test_get_state(self) -> None:
        state = await self.client.get_state()

        self.assertEqual(state, State.idle.value)

    async def test_get_output(self) -> None:
        output = await self.client.get_output()

        self.assertEqual(output, Output.out1.value)

    async def test_set_output_updates_server_state(self) -> None:
        result = await self.client.set_output(Output.out2)

        self.assertEqual(result, "Check status")
        self.assertEqual(await self.client.get_output(), Output.out2.value)

    async def test_set_output_rejects_invalid_enum_value(self) -> None:
        with self.assertRaises(ValueError):
            await self.client.set_output("invalid")
