import time
import sys
import argparse
import logging
import RPi.GPIO as GPIO
from threading import Timer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

PIN_D0 = 11
PIN_D1 = 15
PIN_D2 = 16
PIN_D3 = 13

PIN_ENABLE_MODULATOR = 22
PIN_MODULATOR_MODE_SELECT = 18


# Set the pins numbering mode
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)


# Signal bits map
#
# [All On] [1 On]  [2 On]  [3 On]  [4 On]
# 1011     1111    1110    1101    1100
POWER_ON = 1
POWER_OFF = 0
SIGNALS_BITMAP = {
    POWER_ON: ['1011', '1111', '1110', '1101', '1100'],
    POWER_OFF: ['0011', '0111', '0110', '0101', '0100']
}


# Tell the GPIO what pins are going to be used as outputs
# - the pins that are going to the encoder on the Energenie board: d0-d3
# - the pin used to enable the modulator
# - the pin used for mode selection on the modulator (OOK/FSK)
GPIO.setup(PIN_D0, GPIO.OUT)
GPIO.setup(PIN_D1, GPIO.OUT)
GPIO.setup(PIN_D2, GPIO.OUT)
GPIO.setup(PIN_D3, GPIO.OUT)
GPIO.setup(PIN_ENABLE_MODULATOR, GPIO.OUT)
GPIO.setup(PIN_MODULATOR_MODE_SELECT, GPIO.OUT)

# Disable the modulator and reset the pins
GPIO.output(PIN_ENABLE_MODULATOR, False)
GPIO.output(PIN_MODULATOR_MODE_SELECT, False)
GPIO.output(PIN_D0, False)
GPIO.output(PIN_D1, False)
GPIO.output(PIN_D2, False)
GPIO.output(PIN_D3, False)

timer = None


def _set_encoder_pins(mode, socket):
    bits = SIGNALS_BITMAP[mode][socket]
    GPIO.output(PIN_D3, int(bits[0]))
    GPIO.output(PIN_D2, int(bits[1]))
    GPIO.output(PIN_D1, int(bits[2]))
    GPIO.output(PIN_D0, int(bits[3]))


def _toggle_modulator():
    time.sleep(0.1)
    GPIO.output(PIN_ENABLE_MODULATOR, True)
    time.sleep(0.25)
    GPIO.output(PIN_ENABLE_MODULATOR, False)


def _switch(mode, socket):
    global timer
    if timer:
        timer.cancel()
        timer = None
    _set_encoder_pins(mode, socket)
    _toggle_modulator()


def status(socket=0):
    state = "{}{}{}{}".format(
        GPIO.input(PIN_D3),
        GPIO.input(PIN_D2),
        GPIO.input(PIN_D1),
        GPIO.input(PIN_D0))
    if state == SIGNALS_BITMAP[POWER_ON][socket]:
        return POWER_ON
    if state == SIGNALS_BITMAP[POWER_OFF][socket]:
        return POWER_OFF
    return -1


def on(socket=0, seconds=None):
    if seconds:
        global timer
        if not timer:
            def callback():
                _switch(POWER_OFF, socket)
                return
            _switch(POWER_ON, socket)
            timer = Timer(seconds, callback)
            timer.start()
    else:
        _switch(POWER_ON, socket)


def off(socket=0):
    _switch(POWER_OFF, socket)


def switch_number(value):
    if not int(value) in [0, 1, 2, 3, 4]:
        raise argparse.ArgumentTypeError("%s must be an integer between 0 and 4" % value)
    return int(value)


def command(value):
    if value not in ['on', 'off', 'status']:
        raise argparse.ArgumentTypeError("%s must be 'on', 'off' or 'status'" % value)
    return value


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description='Configure or control a remote Energenie power switch',
        epilog="""To initially configure a switch, hold the button down until the red light starts flashing. Then run the command 'switch.py on N' where N is the number between 1-4 you want to assign to that switch""")
    arg_parser.add_argument('cmd', type=command, help="The command ('config', 'on', 'off', 'status')")
    arg_parser.add_argument('num', type=switch_number, help="The remote power switch to control (between 0 and 4)", default=0)
    args = arg_parser.parse_args()
    globals()[args.cmd](socket=args.num)
