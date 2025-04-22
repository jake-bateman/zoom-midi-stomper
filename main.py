#!/usr/bin/env python3

import subprocess
import time
import re
from datetime import datetime

# increment switch
GPIO_INCREMENT = 24

# decrement switch
GPIO_DECREMENT = 23

# poll rate
sleep_time = 0.01


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
    subprocess.run(["amidi", "-p", midi_dev, "-S", "f0 52 00 58 50 f7"])
    time.sleep(0.1)


def get_patch_number(midi_dev):
    print("saw a switch event. getting patch number.")
    try:
        response = subprocess.check_output(
            ["amidi", "-p", midi_dev, "-S", "f0 52 00 58 33 f7", "-d", "-t", "0.01"],
            stderr=subprocess.DEVNULL,
        ).decode()

        # lower case, repalce newlines with spaces
        response = response.replace("\n", " ").lower().strip()

        if "c0" not in response:
            print("didn't get any useful data")
            return get_patch_number(recover())

        # match something like "c0 2b"
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
    subprocess.run(["amidi", "-p", midi_dev, "-S", f"c0 {hex_val}"])


# to be called when things have gone tits up
def recover():

    while True:
        print("Lost the midi device. Trying to reacquire...")
        try:
            recovered_midi_dev = find_midi_device()
        except:
            sleep(0.3)
            coninue

        enable_parameter_editing(recovered_midi_dev)
        return recovered_midi_dev


def set_led(bool):
    
    if bool:
        subprocess.run(["pinctrl", "set", "25", "op", "dh"])
    else:
        subprocess.run(["pinctrl", "set", "25", "op", "dl"])

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
    
    # poorly named variables. "last known value of the pin connected to the increment switch"
    # and "last known value of the pin connected to the decrement switch" is what they are.
    last_increment = get_pin_state(GPIO_INCREMENT)
    last_decrement = get_pin_state(GPIO_DECREMENT)
    
    tick = 0
    print("watching for switch presses...")
    while True:
        val_increment = get_pin_state(GPIO_INCREMENT)
        val_decrement = get_pin_state(GPIO_DECREMENT)
        
        # MIDI connection status check every 30 ticks and set LED accordingly 
        if tick % 30:
            if find_midi_device() == None:
                set_led(0)
            else:
                set_led(1)

        if val_increment == "lo" and last_increment == "hi":
            patch = get_patch_number(midi_dev)

            # increment, wrapping at 49
            if patch is not None:
                new_patch = (patch + 1) % 50
                set_patch_number(midi_dev, new_patch)
                print(f"incremented patch to {new_patch}")

        if val_decrement == "lo" and last_decrement == "hi":
            patch = get_patch_number(midi_dev)

            # decrement, wrapping at 49
            if patch is not None:
                new_patch = (patch - 1) % 50
                set_patch_number(midi_dev, new_patch)
                print(f"decremented patch to {new_patch}")

        last_increment = val_increment
        last_decrement = val_decrement
        
        tick+=1
        
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

