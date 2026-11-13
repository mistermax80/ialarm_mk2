"""Test command socket cleanup offline without creating real sockets."""

import errno
import logging
import socket
import unittest
from unittest.mock import MagicMock

from custom_components.ialarm_mk2.libpyialarmmk import pyialarmmk

SECRET = "private-password-token-payload-sentinel"


class TestSocketCleanup(unittest.TestCase):
    """Classify cleanup errors while preserving transport failures."""

    def setUp(self):
        """The client constructor stores configuration but does not connect."""
        self.client = pyialarmmk.iAlarmMkClient("offline.invalid", 18034, SECRET, SECRET)
        self.sock = MagicMock()
        self.sock.fileno.return_value = 7
        self.client.sock = self.sock
        self.client.token = SECRET
        self.addCleanup(self.client.logout)

    def assert_clean(self):
        self.assertIsNone(self.client.sock)
        self.assertIsNone(self.client.token)
        self.sock.close.assert_called_once_with()

    def assert_private(self, captured):
        for record in captured.records:
            self.assertNotIn(SECRET, record.getMessage())
            self.assertNotIn(SECRET, repr(record.args))
            self.assertIsNone(record.exc_info)

    def test_absent_socket(self):
        self.client.sock = None
        self.client.token = None
        with self.assertNoLogs(pyialarmmk._LOGGER, level=logging.ERROR):
            self.client.close_socket()
            self.client.logout()
        self.sock.shutdown.assert_not_called()
        self.sock.close.assert_not_called()

    def test_already_closed_socket(self):
        self.sock.fileno.return_value = -1
        with self.assertNoLogs(pyialarmmk._LOGGER, level=logging.WARNING):
            self.client.close_socket()
        self.sock.shutdown.assert_not_called()
        self.assert_clean()

    def test_connected_socket_detached_before_shutdown(self):
        def shutdown(how):
            self.assertIsNone(self.client.sock)
        self.sock.shutdown.side_effect = shutdown
        self.client.close_socket()
        self.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        self.assert_clean()

    def test_shutdown_error_levels_and_privacy(self):
        cases = (
            (errno.ENOTCONN, logging.DEBUG),
            (errno.EBADF, logging.WARNING),
            (errno.EIO, logging.ERROR),
            (errno.ECONNRESET, logging.ERROR),
            (None, logging.ERROR),
        )
        for number, level in cases:
            with self.subTest(errno=number):
                self.sock.reset_mock()
                self.client.sock = self.sock
                self.client.token = SECRET
                self.sock.shutdown.side_effect = OSError(number, SECRET)
                with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as logs:
                    self.client.close_socket()
                errors = [r for r in logs.records if "shutdown" in r.getMessage()]
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].levelno, level)
                self.assertIn(f"errno={number}", errors[0].getMessage())
                self.assertIn(
                    type(self.sock.shutdown.side_effect).__name__, errors[0].getMessage()
                )
                self.assert_private(logs)
                self.assert_clean()

    def test_close_error_levels_and_privacy(self):
        cases = (
            (7, errno.EBADF, logging.WARNING),
            (-1, errno.EBADF, logging.DEBUG),
            (7, errno.EIO, logging.ERROR),
            (-1, errno.EIO, logging.ERROR),
            (7, errno.ENOTCONN, logging.ERROR),
        )
        for descriptor, number, level in cases:
            with self.subTest(descriptor=descriptor, errno=number):
                self.sock.reset_mock()
                self.sock.fileno.return_value = descriptor
                self.client.sock = self.sock
                self.client.token = SECRET
                self.sock.close.side_effect = OSError(number, SECRET)
                with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as logs:
                    self.client.close_socket()
                self.assertEqual(len(logs.records), 1)
                self.assertEqual(logs.records[0].levelno, level)
                self.assertIn(f"errno={number}", logs.records[0].getMessage())
                self.assertNotIn("Socket closed.", "\n".join(logs.output))
                self.assert_private(logs)
                self.assert_clean()

    def test_repeated_cleanup(self):
        self.sock.shutdown.side_effect = OSError(errno.ENOTCONN, SECRET)
        self.client.close_socket()
        self.client.logout()
        self.client.safe_shutdown()
        self.client.close_socket()
        self.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        self.assert_clean()

    def test_fileno_failure_still_closes(self):
        self.sock.fileno.side_effect = OSError(errno.EBADF, SECRET)
        with self.assertLogs(pyialarmmk._LOGGER, level=logging.WARNING) as logs:
            self.client.close_socket()
        self.sock.shutdown.assert_not_called()
        self.assert_private(logs)
        self.assert_clean()

    def test_unexpected_exception_still_closes(self):
        self.sock.shutdown.side_effect = RuntimeError("Unexpected mock failure")
        with self.assertRaises(RuntimeError):
            self.client.close_socket()
        self.assert_clean()

    def test_transport_error_is_preserved_after_cleanup_errors(self):
        cases = (
            ("timeout", TimeoutError(SECRET)),
            ("reset", OSError(errno.ECONNRESET, SECRET)),
            ("eof", None),
        )
        for name, transport_error in cases:
            with self.subTest(transport=name):
                self.sock.reset_mock()
                self.client.sock = self.sock
                self.client.token = SECRET
                self.sock.recv.side_effect = transport_error
                self.sock.recv.return_value = b""
                self.sock.shutdown.side_effect = OSError(errno.ENOTCONN, SECRET)
                self.sock.close.side_effect = OSError(errno.EIO, SECRET)
                with self.assertLogs(pyialarmmk._LOGGER, level=logging.DEBUG) as logs:
                    with self.assertRaises(pyialarmmk.ConnectionError) as caught:
                        self.client._receive()
                if transport_error is not None:
                    self.assertIs(caught.exception.__cause__, transport_error)
                self.assertTrue(any(r.levelno == logging.ERROR for r in logs.records))
                self.assert_private(logs)
                self.assert_clean()


if __name__ == "__main__":
    unittest.main()
