"""Test iAlarm-MK push failure recovery."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from custom_components.ialarm_mk2.libpyialarmmk.pyialarmmk import (
    PushClientError,
    iAlarmMkPushClient,
)


class TestPushFailure(unittest.IsolatedAsyncioTestCase):
    """Test push protocol error handling."""

    async def test_subscription_error(self):
        """A rejected subscription must close the connection."""

        loop = asyncio.get_running_loop()
        disconnected = loop.create_future()

        client = iAlarmMkPushClient(
            host="127.0.0.1",
            port=18034,
            uid="TEST_DEVICE",
            handler=lambda event: None,
            loop=loop,
            on_con_lost=disconnected,
        )

        # No real TCP connection is created.
        transport = MagicMock()
        transport.is_closing.return_value = False
        client.transport = transport

        # Simulate a rejected push subscription.
        with patch.object(
            client,
            "handle_read",
            side_effect=PushClientError("Push subscription error."),
        ):
            client.data_received(b"SIMULATED_ERROR")

        # Verify the transport is closed.
        transport.close.assert_called()

        # Verify that subscribe() can detect disconnection.
        self.assertTrue(disconnected.done())

        print("PASS: Push error handled without crashing.")
        print("PASS: TCP transport closed.")
        print("PASS: Disconnect future completed.")


if __name__ == "__main__":
    unittest.main()
