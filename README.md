# Home Assistant custom integration for iAlarm MK

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
