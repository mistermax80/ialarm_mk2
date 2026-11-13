"""Verify sensitive values stay out of diagnostic and client logs offline."""

import logging
import socket
import unittest
from unittest.mock import MagicMock, patch

from custom_components.ialarm_mk2 import diagnostics
from custom_components.ialarm_mk2.libpyialarmmk import pyialarmmk

PASSWORD = "private-password-sentinel"
TOKEN = "private-token-sentinel"
USERNAME = "private-username-sentinel"


class TestLoggingPrivacy(unittest.IsolatedAsyncioTestCase):
    """Exercise real logging paths with all panel communication mocked."""

    def setUp(self):
        """Replace sockets and protocol requests before constructing a client."""
        socket_factory = self.enterContext(patch.object(pyialarmmk.socket, "socket"))
        self.sock = socket_factory.return_value
        self.sock.fileno.return_value = 42
        self.client = pyialarmmk.iAlarmMkClient(
            "offline.invalid", 18034, USERNAME, PASSWORD
        )
        self.addCleanup(self.client.logout)
        self.socket_check = self.client.is_socket_connected
        self.request = self.enterContext(
            patch.object(self.client, "_", return_value={"Err": 0})
        )
        self.enterContext(
            patch.object(self.client, "is_socket_connected", return_value=False)
        )
        self.enterContext(patch.object(pyialarmmk.uuid, "uuid4", return_value=TOKEN))

    def assert_private(self, captured):
        """Check formatted logs and the original logging records."""
        rendered = "\n".join(captured.output)
        for secret in (PASSWORD, TOKEN, USERNAME):
            self.assertNotIn(secret, rendered)
            for record in captured.records:
                self.assertNotIn(secret, repr(record.msg))
                self.assertNotIn(secret, repr(record.args))
        return rendered

    async def test_config_entry_diagnostics(self):
        """The config entry is redacted for export and never dumped to logs."""
        entry = MagicMock()
        entry.as_dict.return_value = {
            "title": USERNAME,
            "data": {"username": USERNAME, "password": PASSWORD, "token": TOKEN},
        }

        with self.assertLogs(diagnostics._LOGGER, level=logging.DEBUG) as captured:
            result = await diagnostics.async_get_config_entry_diagnostics(
                MagicMock(), entry
            )

        self.assert_private(captured)
        self.assertNotEqual(result["entry"]["data"]["password"], PASSWORD)
        entry.as_dict.assert_called_once_with()

    def test_successful_login_and_logout(self):
        """Authentication payload stays intact while logs omit its secrets."""
        with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as captured:
            self.client.login()
            self.assertEqual(self.client.token, TOKEN)
            self.client.logout()

        rendered = self.assert_private(captured)
        self.assertIn("Login successful", rendered)
        self.assertIn("Socket closed", rendered)
        self.sock.connect.assert_called_once_with(("offline.invalid", 18034))
        self.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        self.sock.close.assert_called_once_with()
        self.assertIsNone(self.client.sock)
        self.assertIsNone(self.client.token)
        path, command = self.request.call_args.args
        self.assertEqual(path, "/Root/Pair/Client")
        self.assertEqual(command["Pwd"], pyialarmmk.PWD(PASSWORD))
        self.assertEqual(command["Token"], pyialarmmk.STR(TOKEN))
        self.assertEqual(command["Id"], pyialarmmk.STR(USERNAME))

    def test_rejected_login(self):
        """Keep the panel error code without disclosing the generated token."""
        self.request.return_value = {"Err": 7}

        with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as captured:
            with self.assertRaises(pyialarmmk.ClientError):
                self.client.login()

        rendered = self.assert_private(captured)
        self.assertIn("Error during login to the server: 7", rendered)
        self.sock.close.assert_called_once_with()

    def test_socket_check_error_during_login(self):
        """The connection check must not log raw socket exception messages."""
        self.client.sock = self.sock
        self.client.token = TOKEN
        self.sock.getpeername.side_effect = OSError(
            f"{PASSWORD} {TOKEN} {USERNAME}"
        )

        with (
            patch.object(
                self.client, "is_socket_connected", side_effect=self.socket_check
            ),
            self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as captured,
        ):
            self.client.login()
            self.client.logout()

        rendered = self.assert_private(captured)
        self.assertIn("Socket not connected (OSError)", rendered)
        self.assertIn("Login successful", rendered)

    def test_connection_errors(self):
        """Exception text and tracebacks must not leak authentication data."""
        cases = (
            (TimeoutError, "Connection timeout"),
            (ConnectionRefusedError, "Connection refused"),
            (OSError, "Network error"),
        )
        for error_type, expected_log in cases:
            with self.subTest(error_type=error_type):
                self.client.sock = None
                self.sock.connect.side_effect = error_type(
                    f"{PASSWORD} {TOKEN} {USERNAME}"
                )
                with self.assertLogs(
                    pyialarmmk._LOGGER, level=logging.DEBUG
                ) as captured:
                    with self.assertRaises(pyialarmmk.ConnectionError):
                        self.client.login()
                rendered = self.assert_private(captured)
                self.assertIn(expected_log, rendered)
                self.assertIn(error_type.__name__, rendered)
                self.assertTrue(any(r.levelno == logging.ERROR for r in captured.records))

    def test_unexpected_login_error(self):
        """Protocol exceptions may contain credentials and must not be logged."""
        self.request.side_effect = ValueError(f"{PASSWORD} {TOKEN} {USERNAME}")

        with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as captured:
            with self.assertRaises(pyialarmmk.ClientError):
                self.client.login()

        rendered = self.assert_private(captured)
        self.assertIn("Unexpected error during login (ValueError)", rendered)
        self.sock.close.assert_called_once_with()

    def test_socket_close_errors(self):
        """Shutdown and close errors remain identifiable without raw messages."""
        self.client.sock = self.sock
        self.client.token = TOKEN
        self.sock.shutdown.side_effect = OSError(f"{PASSWORD} {TOKEN} {USERNAME}")
        self.sock.close.side_effect = OSError(f"{PASSWORD} {TOKEN} {USERNAME}")

        with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as captured:
            self.client.logout()

        rendered = self.assert_private(captured)
        self.assertIn("Error during socket shutdown (OSError)", rendered)
        self.assertIn("Error closing socket (OSError)", rendered)
        self.assertIsNone(self.client.sock)
        self.assertIsNone(self.client.token)


if __name__ == "__main__":
    unittest.main()
