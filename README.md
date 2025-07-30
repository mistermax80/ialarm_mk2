# Home Assistant custom integration for iAlarm MK

[![HACS][hacs-shield]][hacs]
[![Release][releases-shield]][releases]
[![Downloads][downloads-shield]][downloads]
[![Stars][stars-shield]][stars]
[![Forks][forks-shield]][forks]
[![Issues][issues-shield]][issues]
[![Last Commit][lastcommit-shield]][lastcommit]
[![License][license-shield]][license]
[![Maintenance][maintenance-shield]][maintenance]
[![Project Stage][projectstage-shield]][projectstage]

An advanced custom integration for Home Assistant, designed for the iAlarm MK alarm system.

The goal of this integration is to retrieve as much information as possible from the central server. For example:
- Alarm status
- Sensor status, including sensor state, battery level, bypass status, and connection loss information
- Reception of asynchronous events from the central server

All of this information is made available in Home Assistant, so it can be used in automations, for instance.

Currently, it is possible to:
- Retrieve the alarm status
- Send commands to the alarm: arm, night arm, custom by-pass arm, disarm, cancel active alarm
- View the status of sensors: open/closed for doors and windows (and others)
- Check the battery status of sensors: for all sensors
- Check the bypass status: for all sensors
- Check the connection status: for all sensors
- Listen event: ialarm_mk2_event

In the future, it will be possible to:
- Configure sensors
- Retrieve logs
- Set bypass options
- And more...

Currently, the integration uses the included `pyialarm` library, but it is planned to migrate and maintain it externally.

Special thanks to:
- https://github.com/wildstray/meian-client
- https://github.com/RyuzakiKK/pyialarm
- https://github.com/bigmoby/pymeianlike
- https://github.com/maxill1/ialarm-mqtt

[hacs-shield]: https://img.shields.io/badge/HACS-Available-brightgreen?style=for-the-badge
[hacs]: https://hacs.xyz/repository/github/mistermax80/ialarm_mk2

[releases-shield]: https://img.shields.io/github/v/release/mistermax80/ialarm_mk2?include_prereleases&style=for-the-badge
[releases]: https://github.com/mistermax80/ialarm_mk2/releases

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
[license]: https://github.com/mistermax80/ialarm_mk2/blob/main/LICENSE.md

[maintenance-shield]: https://img.shields.io/maintenance/yes/2025?style=for-the-badge
[maintenance]: https://github.com/mistermax80/ialarm_mk2

[projectstage-shield]: https://img.shields.io/badge/project%20stage-stable-brightgreen?style=for-the-badge
[projectstage]: https://github.com/mistermax80/ialarm_mk2
