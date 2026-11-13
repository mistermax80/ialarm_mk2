# iAlarm MK2 for Home Assistant

[English](README.md) | [Italiano](README.it.md)

[![HACS][hacs-custom-shield]][hacs]
[![Stable Release][stable-shield]][stable]
[![Latest Pre-Release][prerelease-shield]][prerelease]
[![Downloads][downloads-shield]][downloads]
[![Stars][stars-shield]][stars]
[![Forks][forks-shield]][forks]
[![Issues][issues-shield]][issues]
[![Last Commit][lastcommit-shield]][lastcommit]
[![License][license-shield]][license]
[![Maintenance][maintenance-shield]][maintenance]


Custom Home Assistant integration for Meian / iAlarm MK alarm panels, using an internal modified copy of `pyialarmmk`.

The documented version is **[2.3.0-alpha.8](https://github.com/mistermax80/ialarm_mk2/releases/tag/2.3.0-alpha.8)**, published as a pre-release. The HACS metadata declares Home Assistant **2026.9.0** as the minimum version.

## Features

| Area | Available functionality |
| --- | --- |
| Alarm panel | Arm away, arm home, arm custom bypass/partial and disarm; display alarm and transition states. |
| Zones | Binary sensors for zone states, with low-battery, connection-loss, bypass and last-check attributes. |
| Zone bypass | One configuration switch per discovered zone; changes require a successful coordinator update and a disarmed alarm. The integration refreshes and verifies the requested state. |
| Batteries | Estimated battery percentage based on the last replacement date, configurable for each sensor. |
| Diagnostics | Read-only network, mobile APN and system configuration values. |
| Push | Alarm events on `ialarm_mk2_event` and a push connectivity binary sensor. |
| Maintenance | Optional reboot button, disabled by default; reboot requires the alarm to be disarmed. |

### Battery estimates

The percentage is estimated linearly over two years from the replacement date. It is not a measured charge level. Without a saved date, the value is unknown unless the panel reports a low battery; that report sets the displayed value to 5%. Disabling the estimate does not suppress the low-battery report.

### Diagnostics

Diagnostic entities expose configured IP, gateway, DNS servers, DHCP, mobile APN, entry/exit delays, siren duration, loss settings and system flags. These are **configuration values**, not live AC, wireless or communication fault indicators.

They are read once during integration setup and remain cached until the integration is reloaded. Settings cannot be edited through these entities.

### State updates and events

Zone states are polled at the configured interval (60 seconds by default). Alarm status is initially read from the panel and then maintained from push events and local command updates; zone polling does not reread `GetAlarmStatus`.

The connectivity entity indicates whether a push pairing/keepalive was received within approximately two minutes. It does not independently verify the command connection.

Listen for `ialarm_mk2_event` in Home Assistant to use push events in automations. Event data includes `Cid`, `Status`, `Zone`, `ZoneName`, `Content` and `LastRealUpdateStatus`. Available information depends on the received event.

## Installation

### HACS

Add this repository as a custom **Integration** repository in HACS:

```text
https://github.com/mistermax80/ialarm_mk2
```

Install the integration and restart Home Assistant. To install `2.3.0-alpha.8`, enable pre-release versions when choosing the version to download in HACS.

### Manual installation

1. Download the desired release from [GitHub releases](https://github.com/mistermax80/ialarm_mk2/releases).
2. Copy the release's `custom_components/ialarm_mk2` directory into `<config>/custom_components/ialarm_mk2`, preserving its contents.
3. Restart Home Assistant.

## Configuration

In **Settings → Devices & services → Add integration**, search for **iAlarm-MK Integration 2**. Enter the host (IP address or hostname), port, panel ID/username, password and zone polling interval. The default host is the server address configured by the integration.

Use **Reconfigure** to change connection settings or the polling interval. In the integration's options, expand a sensor section to set its last battery replacement date. Turn off `disable_battery_estimate` when enabling an estimate; leaving it on clears the saved date. Future dates are rejected.

Entity names are available in English and Italian. Existing user-defined entity names are preserved. Battery-option sections currently use dynamic sensor names and raw field identifiers (`battery_replacement_date`, `disable_battery_estimate`).

## Current limits and planned work

- `GetLog` and `GetEvents` exist in the internal library but are not exposed as history retrieval features in Home Assistant. Push events are already supported.
- System settings are read-only; `SetSys` is not exposed.
- Zone configuration and a separate cancel-active-alarm action are not exposed.
- SOS/emergency activation is not exposed.

## Logging and offline tests

The integration no longer dumps the full configuration entry into diagnostic logs or includes authentication tokens in login/logout/socket-close messages. Those error logs retain the operation and exception type while omitting raw exception text. This does not remove existing log files or constitute redaction of every possible log emitted by other code.

Nine automated tests cover push failure/backoff and sensitive logging. From the repository root, with Home Assistant, `lxml` and `xmltodict` available in the Python environment, run:

```sh
python -B -m unittest discover -s custom_components/ialarm_mk2/tests -v
```

The tests mock communication and do not connect to a real alarm panel.

## Thanks

- [meian-client](https://github.com/wildstray/meian-client)
- [pyialarm](https://github.com/RyuzakiKK/pyialarm)
- [pymeianlike](https://github.com/bigmoby/pymeianlike)
- [ialarm-mqtt](https://github.com/maxill1/ialarm-mqtt)

[hacs-custom-shield]: https://img.shields.io/badge/HACS-Custom%20Repository-blue?style=for-the-badge
[hacs]: https://hacs.xyz/repository/github/mistermax80/ialarm_mk2

[stable-shield]: https://img.shields.io/github/v/release/mistermax80/ialarm_mk2?label=Stable&sort=semver&style=for-the-badge
[stable]: https://github.com/mistermax80/ialarm_mk2/releases/latest

[prerelease-shield]: https://img.shields.io/github/v/release/mistermax80/ialarm_mk2?include_prereleases&label=Pre-Release&sort=semver&style=for-the-badge
[prerelease]: https://github.com/mistermax80/ialarm_mk2/releases

[downloads-shield]: https://img.shields.io/github/downloads/mistermax80/ialarm_mk2/total?style=for-the-badge
[downloads]: https://github.com/mistermax80/ialarm_mk2/releases

[stars-shield]: https://img.shields.io/github/stars/mistermax80/ialarm_mk2?style=for-the-badge
[stars]: https://github.com/mistermax80/ialarm_mk2/stargazers

[forks-shield]: https://img.shields.io/github/forks/mistermax80/ialarm_mk2?style=for-the-badge
[forks]: https://github.com/mistermax80/ialarm_mk2/network/members

[issues-shield]: https://img.shields.io/github/issues/mistermax80/ialarm_mk2?style=for-the-badge
[issues]: https://github.com/mistermax80/ialarm_mk2/issues

[lastcommit-shield]: https://img.shields.io/github/last-commit/mistermax80/ialarm_mk2?style=for-the-badge
[lastcommit]: https://github.com/mistermax80/ialarm_mk2/commits/main

[license-shield]: https://img.shields.io/github/license/mistermax80/ialarm_mk2?style=for-the-badge
[license]: https://github.com/mistermax80/ialarm_mk2/blob/main/LICENSE

[maintenance-shield]: https://img.shields.io/maintenance/yes/2026?style=for-the-badge
[maintenance]: https://github.com/mistermax80/ialarm_mk2
