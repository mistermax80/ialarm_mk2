"""Test iAlarm-MK push reconnection backoff."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from custom_components.ialarm_mk2.libpyialarmmk import (
    ipyialarmmk,
)


class TestPushBackoff(unittest.IsolatedAsyncioTestCase):
    """Test retry delays without real network connections."""

    async def test_reconnection_backoff(self):
        """Failed connections must respect the backoff delay."""

        interface = ipyialarmmk.iAlarmMkInterface.__new__(ipyialarmmk.iAlarmMkInterface)

        # Avoid __init__ because it connects to the real server.
        interface.host = "127.0.0.1"
        interface.port = 18034
        interface.uid = "TEST_DEVICE"
        interface.pwd = "TEST_PASSWORD"
        interface._cancelled = False
        interface.push_client = None
        interface.keepalive_callback = None

        delays = []
        attempts = 0

        async def fake_create_connection(*args, **kwargs):
            """Simulate an unreachable push server."""
            nonlocal attempts

            attempts += 1

            # Stop after six failed connection attempts.
            if attempts >= 6:
                interface._cancelled = True

            raise OSError("Simulated connection failure")

        async def fake_sleep(delay):
            """Record requested delays without waiting."""
            delays.append(delay)

        fake_client = MagicMock()

        loop = asyncio.get_running_loop()

        with (
            patch.object(
                loop,
                "create_connection",
                side_effect=fake_create_connection,
            ),
            patch.object(
                ipyialarmmk,
                "iAlarmMkPushClient",
                return_value=fake_client,
            ),
            patch.object(
                ipyialarmmk.asyncio,
                "sleep",
                side_effect=fake_sleep,
            ),
        ):
            await interface.subscribe("TEST_BACKOFF")

        expected_delays = [2, 4, 8, 16, 30]

        print(f"Connection attempts: {attempts}")
        print(f"Observed delays: {delays}")
        print(f"Expected delays: {expected_delays}")

        self.assertEqual(attempts, 6)
        self.assertEqual(delays, expected_delays)

        self.assertIsNone(interface.push_client)
        self.assertTrue(interface._cancelled)


if __name__ == "__main__":
    unittest.main()
