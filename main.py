#!/usr/bin/env python3

import subprocess
import time
import re
from datetime import datetime

# =========================
# pin assignments
# =========================
GPIO_INCREMENT = 24
GPIO_DECREMENT = 23
GPIO_LED       = 16

# =========================
# intervals, seconds
# =========================
# polling rate for the main loop
POLL_INTERVAL = 0.025

# hold this long before auto-scroll begins
SCROLL_START_DELAY = 0.5

# time between auto-scroll steps while the button is held
SCROLL_INTERVAL = 0.3

# timeout for the amidi command asking the pedal for patch number
AMIDI_TIMEOUT = 0.06

# =========================
# device functions
# =========================
def get_pin_state(pin):
    try:
        output = subprocess.check_output(["pinctrl", "get", str(pin)], text=True)
        match = re.search(r'\|\s*(hi|lo)', output)
        if match:
            return match.group(1)
        else:
            return "unknown"
    except subprocess.CalledProcessError:
        return "error"

def find_midi_device():
    try:
        output = subprocess.check_output(["amidi", "-l"], text=True)
        for line in output.splitlines():
            if "ZOOM MS Series MIDI" in line:
                return line.split()[1]  # e.g., "hw:1,0,0"
    except subprocess.CalledProcessError:
        pass
    return None

def enable_parameter_editing(midi_dev):
    try:
        subprocess.run(["amidi", "-p", midi_dev, "-S", "f0 52 00 58 50 f7"], check=False)
    except Exception:
        print("No device for MIDI comms initially, waiting 5s and trying again")
        time.sleep(5)
    time.sleep(0.1)

def get_patch_number(midi_dev):
    print("saw a switch event. getting patch number.")
    try:
        response = subprocess.check_output(
            ["amidi", "-p", midi_dev, "-S", "f0 52 00 58 33 f7", "-d", "-t", str(AMIDI_TIMEOUT)],
            stderr=subprocess.DEVNULL,
        ).decode()

        response = response.replace("\n", " ").lower().strip()

        if "c0" not in response:
            print("didn't get any useful data")
            return get_patch_number(recover())

        match = re.search(r'c0\s*([0-9a-f]{2})', response)
        if match:
            patch_hex = match.group(1)
            patch_dec = int(patch_hex, 16)
            return patch_dec
    except subprocess.CalledProcessError as e:
        print("prang!", e)
        return get_patch_number(recover())
    except Exception as e:
        print("prang!", e)
        return get_patch_number(recover())
    return None

def set_patch_number(midi_dev, patch_num):
    hex_val = f"{patch_num:02x}"
    subprocess.run(["amidi", "-p", midi_dev, "-S", f"c0 {hex_val}"], check=False)

def recover():
    while True:
        print("Lost the MIDI device. Trying to reacquire...")
        try:
            recovered_midi_dev = find_midi_device()
            if recovered_midi_dev:
                enable_parameter_editing(recovered_midi_dev)
                return recovered_midi_dev
        except Exception:
            pass
        time.sleep(0.3)

def set_led(on):
    if on:
        subprocess.run(["pinctrl", "set", str(GPIO_LED), "op", "dh"], check=False)
    else:
        subprocess.run(["pinctrl", "set", str(GPIO_LED), "op", "dl"], check=False)

# =========================
# buttons and scrolling
# =========================
def button_is_held_low(pin):
    return get_pin_state(pin) == "lo"

def single_step(midi_dev, delta):
    patch = get_patch_number(midi_dev)
    if patch is None:
        return
    new_patch = (patch + delta) % 50
    set_patch_number(midi_dev, new_patch)
    if delta > 0:
        print(f"incremented patch to {new_patch}")
    else:
        print(f"decremented patch to {new_patch}")

def handle_press_and_scroll(pin, delta, midi_dev):
    """
    called immediately upon detecting a HI->LO edge.
    performs one immediate step, then if the button remains held
    waits SCROLL_START_DELAY repeats steps every SCROLL_INTERVAL
    until button is released
    """
    # one immediate step on edge
    single_step(midi_dev, delta)

    # if hold, start timer for auto-scroll
    t0 = time.monotonic()
    # wait for the duration of the scroll start delay (exit early if released)
    while button_is_held_low(pin):
        if time.monotonic() - t0 >= SCROLL_START_DELAY:
            break
        time.sleep(0.002)

    # auto-scroll loop
    next_step_at = time.monotonic()
    while button_is_held_low(pin):
        now = time.monotonic()
        if now >= next_step_at:
            single_step(midi_dev, delta)
            next_step_at = now + SCROLL_INTERVAL
        time.sleep(0.002)

def main():
    set_led(0)
    print("~~~ Starting ZOOM Patch Switcher ~~~")
    midi_dev = find_midi_device()
    if not midi_dev:
        set_led(0)
        print("PRANG: No ZOOM pedal found on the MIDI bus.")
        midi_dev = recover()

    # assume that at this point all is well and set the LED on
    set_led(1)
    enable_parameter_editing(midi_dev)

    # track last known states for edge detection
    last_increment = get_pin_state(GPIO_INCREMENT)
    last_decrement = get_pin_state(GPIO_DECREMENT)

    print("watching for switch presses...")
    heartbeat_next = time.monotonic()  # for periodic LED/device check

    while True:
        val_increment = get_pin_state(GPIO_INCREMENT)
        val_decrement = get_pin_state(GPIO_DECREMENT)

        # periodically confirm device presence & LED
        now = time.monotonic()
        if now >= heartbeat_next:
            if find_midi_device() is None:
                set_led(0)
            else:
                set_led(1)
            heartbeat_next = now + 3.0

        # decrement button: detect HI->LO edge, handle
        if val_decrement == "lo" and last_decrement == "hi":
            handle_press_and_scroll(GPIO_DECREMENT, delta=-1, midi_dev=midi_dev)

        # increment button: detect HI->LO edge, handle
        if val_increment == "lo" and last_increment == "hi":
            handle_press_and_scroll(GPIO_INCREMENT, delta=+1, midi_dev=midi_dev)

        last_increment = val_increment
        last_decrement = val_decrement

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

