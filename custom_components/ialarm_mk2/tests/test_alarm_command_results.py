"""Test alarm command acknowledgements offline with a mocked panel client."""

import asyncio
from concurrent.futures import Future
import logging
from types import SimpleNamespace
import traceback
import unittest
from unittest.mock import MagicMock, patch

from homeassistant.exceptions import HomeAssistantError

from custom_components.ialarm_mk2.alarm_control_panel import iAlarmMkPanel
from custom_components.ialarm_mk2.libpyialarmmk import ipyialarmmk
from custom_components.ialarm_mk2.libpyialarmmk.pyialarmmk import ConnectionError

SECRET = "private-password-and-token-sentinel"
I = ipyialarmmk.iAlarmMkInterface
COMMANDS = (
    ("arm_away", "alarm_arm_away", I.ARMED_AWAY, I.ALARM_ARMING),
    ("arm_stay", "alarm_arm_home", I.ARMED_STAY, I.ARMED_STAY),
    ("arm_partial", "alarm_arm_custom_bypass", I.ARMED_PARTIAL, I.ALARM_ARMING),
    ("disarm", "alarm_disarm", I.DISARMED, I.ALARM_DISARMING),
)


class TestAlarmCommandResults(unittest.TestCase):
    """Exercise all four real command methods and the HA error boundary."""

    def setUp(self):
        """Bypass the interface constructor, which normally contacts the panel."""
        self.interface = I.__new__(I)
        self.interface.ialarmmkClient = self.client = MagicMock()
        self.interface.status = I.DISARMED
        self.interface.hass = SimpleNamespace(
            config=SimpleNamespace(time_zone="Europe/Rome"), loop=MagicMock()
        )
        self.interface.callback_only_status = self.callback = MagicMock()
        self.client.SetAlarmStatus.return_value = {"Err": 0}

        def schedule(coroutine, loop):
            # Run the actual notification coroutine without threads or sockets.
            future = Future()
            try:
                future.set_result(asyncio.run(coroutine))
            except Exception as err:
                future.set_exception(err)
            return future

        self.enterContext(patch.object(
            ipyialarmmk.asyncio, "run_coroutine_threadsafe", side_effect=schedule
        ))
        coordinator = MagicMock()
        coordinator.hub.ialarmmk = self.interface
        self.panel = iAlarmMkPanel(coordinator)
        self.enterContext(patch.object(self.panel, "_retrive_user_id", return_value="user"))

    def reset_calls(self):
        self.client.reset_mock()
        self.callback.reset_mock()

    def assert_safe_error(self, error, text):
        self.assertIn(text, str(error))
        self.assertNotIn(SECRET, "".join(traceback.format_exception(error)))

    def test_accepted_commands_preserve_notifications(self):
        for method, _, requested, local in COMMANDS:
            with self.subTest(command=method):
                self.reset_calls()
                getattr(self.interface, method)("user")
                self.client.login.assert_called_once_with()
                self.client.SetAlarmStatus.assert_called_once_with(requested)
                self.client.logout.assert_called_once_with()
                self.callback.assert_called_once()
                data = self.callback.call_args.args[0]
                self.assertEqual(data["Status"], local)
                self.assertEqual(data["user_id"], "user")
                # State synchronization is intentionally outside this change.
                self.assertEqual(self.interface.status, I.DISARMED)

    def test_rejected_commands(self):
        self.client.SetAlarmStatus.return_value = {"Err": 7, "Pwd": SECRET}
        for method, _, requested, _ in COMMANDS:
            with self.subTest(command=method):
                self.reset_calls()
                with self.assertRaises(ipyialarmmk.AlarmCommandError) as caught:
                    getattr(self.interface, method)("user")
                self.assert_safe_error(caught.exception, "rejected")
                self.client.SetAlarmStatus.assert_called_once_with(requested)
                self.client.logout.assert_called_once_with()
                self.callback.assert_not_called()

    def test_null_incomplete_and_invalid_responses(self):
        for response in (None, {}, {"Pwd": SECRET}, {"Err": None},
                         {"Err": "0"}, {"Err": False}, [], {"Err": SECRET}):
            self.client.SetAlarmStatus.return_value = response
            for method, _, _, _ in COMMANDS:
                with self.subTest(command=method, response=response):
                    self.reset_calls()
                    with self.assertRaises(ipyialarmmk.AlarmCommandError) as caught:
                        getattr(self.interface, method)("user")
                    self.assert_safe_error(caught.exception, "not confirmed")
                    self.client.SetAlarmStatus.assert_called_once()
                    self.client.logout.assert_called_once_with()
                    self.callback.assert_not_called()

    def test_timeout_outcome_is_unconfirmed_without_retry(self):
        # The TCP client wraps socket timeouts in its own ConnectionError.
        for error in (TimeoutError(SECRET), ConnectionError(SECRET)):
            self.client.SetAlarmStatus.side_effect = error
            for method, _, _, _ in COMMANDS:
                with self.subTest(command=method, error=type(error).__name__):
                    self.reset_calls()
                    with self.assertRaises(ipyialarmmk.AlarmCommandError) as caught:
                        getattr(self.interface, method)("user")
                    self.assert_safe_error(caught.exception, "may have been executed")
                    self.client.SetAlarmStatus.assert_called_once()
                    self.client.logout.assert_called_once_with()
                    self.callback.assert_not_called()

    def test_login_failure_does_not_send_command(self):
        self.client.login.side_effect = RuntimeError(SECRET)
        for method, _, _, _ in COMMANDS:
            with self.subTest(command=method):
                self.reset_calls()
                with self.assertRaises(ipyialarmmk.AlarmCommandError) as caught:
                    getattr(self.interface, method)("user")
                self.assert_safe_error(caught.exception, "command not sent")
                self.client.SetAlarmStatus.assert_not_called()
                self.client.logout.assert_called_once_with()
                self.callback.assert_not_called()

    def test_callback_failure_is_distinct_from_rejection(self):
        self.callback.side_effect = RuntimeError(SECRET)
        for method, _, _, _ in COMMANDS:
            with self.subTest(command=method):
                self.reset_calls()
                with self.assertRaises(ipyialarmmk.AlarmCommandUpdateError) as caught:
                    getattr(self.interface, method)("user")
                self.assert_safe_error(caught.exception, "panel accepted")
                self.client.SetAlarmStatus.assert_called_once()
                self.client.logout.assert_called_once_with()
                self.callback.assert_called_once()

    def test_logout_failure_does_not_mask_outcome(self):
        self.client.logout.side_effect = RuntimeError(SECRET)
        for method, _, _, _ in COMMANDS:
            for outcome in ("accepted", "rejected", "timeout", "invalid", "callback"):
                with self.subTest(command=method, outcome=outcome):
                    self.reset_calls()
                    self.client.SetAlarmStatus.side_effect = (
                        TimeoutError(SECRET) if outcome == "timeout" else None
                    )
                    self.client.SetAlarmStatus.return_value = (
                        None if outcome == "invalid" else {"Err": 7 if outcome == "rejected" else 0}
                    )
                    self.callback.side_effect = (
                        RuntimeError(SECRET) if outcome == "callback" else None
                    )
                    with self.assertLogs(ipyialarmmk._LOGGER, level=logging.WARNING) as logs:
                        if outcome == "accepted":
                            getattr(self.interface, method)("user")
                        else:
                            error_type = (ipyialarmmk.AlarmCommandUpdateError
                                          if outcome == "callback" else ipyialarmmk.AlarmCommandError)
                            with self.assertRaises(error_type) as caught:
                                getattr(self.interface, method)("user")
                            expected = {"rejected": "rejected", "timeout": "not confirmed",
                                        "invalid": "not confirmed", "callback": "panel accepted"}[outcome]
                            self.assert_safe_error(caught.exception, expected)
                    self.assertNotIn(SECRET, "\n".join(logs.output))
                    self.client.logout.assert_called_once_with()
                    self.client.SetAlarmStatus.assert_called_once()
                    if outcome in ("rejected", "timeout", "invalid"):
                        self.callback.assert_not_called()

    def test_home_assistant_errors_for_all_commands(self):
        for _, service, _, _ in COMMANDS:
            for outcome in ("rejected", "invalid", "timeout", "callback"):
                with self.subTest(service=service, outcome=outcome):
                    self.reset_calls()
                    self.client.SetAlarmStatus.return_value = (
                        None if outcome == "invalid" else {"Err": 7 if outcome == "rejected" else 0}
                    )
                    self.client.SetAlarmStatus.side_effect = (
                        TimeoutError(SECRET) if outcome == "timeout" else None
                    )
                    self.callback.side_effect = (
                        RuntimeError(SECRET) if outcome == "callback" else None
                    )
                    with self.assertRaises(HomeAssistantError) as caught:
                        getattr(self.panel, service)()
                    self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))
                    self.client.SetAlarmStatus.assert_called_once()
                    self.client.logout.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
