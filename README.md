# ZOOM MIDI Stomper

This is a Python program intended to run on a Raspberry Pi Zero or equivalent GPIO-equipped SBC, for the purpose of externalising the MIDI patch switching of a ZOOM MultiStomp device to a homebrew switch/pedal. Pins 23 and 24 are used for a momentary stomp switch. Pin 25 is used for a status LED indicating the presence/absence of a ZOOM pedal on the Pi's USB MIDI bus. `alsa` and it's midi i/o binary `amidi` are dependencies, as is `pinctrl`.

## Why?
This is being written as a Linux/RPi alternative to [maestun's much more impressive Arduino-based solution](https://github.com/maestun/zoom-multistomp-patch-changer) for which we could not easily source the required parts.

## How?
With a systemd service set to restart always. This should cause the Pi to run the program in a fairly fault-tolerant way as soon as it boots. A Pi Zero 2 with some optimisations should boot and begin Pythoning fairly quickly.
