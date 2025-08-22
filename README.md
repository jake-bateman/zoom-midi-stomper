# ZOOM MIDI Stomper

This is a Python program intended to run on a Raspberry Pi Zero or equivalent GPIO-equipped SBC, for the purpose of externalising the MIDI patch switching of a ZOOM MultiStomp device to a homebrew switch/pedal. Pins 23 and 24 are used for a momentary stomp switch. Pin 16 is used for a status LED indicating the presence/absence of a ZOOM pedal on the Pi's USB MIDI bus. `alsa` and it's midi i/o binary `amidi` are dependencies, as is `pinctrl`.

## Why?
This is being written as a Linux/RPi alternative to [maestun's much more impressive Arduino-based solution](https://github.com/maestun/zoom-multistomp-patch-changer) for which we could not easily source the required parts.

## How?
With a systemd service set to restart always. This should cause the Pi to run the program in a fairly fault-tolerant way as soon as it boots. A Pi Zero 2 with some optimisations should boot and begin Pythoning fairly quickly. Something like:

```
# /etc/systemd/system/zoom.service
[Unit]
Description=Zoom MIDI Stomper
After=local-fs.target
# No network dependencies; starts as soon as basic filesystems are up.

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/home/user/git/zoom-midi-stomper
ExecStart=/usr/bin/env python3 /home/user/git/zoom-midi-stomper/main.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=2s
StartLimitIntervalSec=0
TimeoutStopSec=5s
KillMode=process

[Install]
WantedBy=multi-user.target

```
## Where do these MIDI System Exclusive values come from?
Other people's hard reverse engineering work 🫡

https://github.com/g200kg/zoom-ms-utility/blob/master/midimessage.md

This program currently looks for/communicates correctly with the MS-50G only.
TODO: parameterise other models' SysEx values.

## Schematic?

![zoom](https://github.com/user-attachments/assets/71c08dc9-72c0-4d82-b873-b6f740b901d9)

