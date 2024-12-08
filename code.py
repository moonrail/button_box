"""
Button Box with 64 possible buttons (as defined in joystick.py & boot.py)

As per current definition of Pins below, 47 of 64 buttons are mapped:
- Buttons 1-36: button matrix (6*6)
- Button 37: "escape" button, that also enables serial, if pressed at boot time
- Buttons 38-47: encoders (CounterClockwise * 5 + Clockwise * 5)
  - encoders will therefore work in stepwise-click-mode, so no support for mapping a single position to a single button
  - a step of the encoder causes a press and release of a button
"""

import board
import supervisor
import usb_hid

from joystick import Joystick
from digitalio import DigitalInOut, Pull
from microcontroller import Pin
from rotaryio import IncrementalEncoder


# disable auto reload
supervisor.runtime.autoreload = False

# pin definition, customize as required
ESCAPE_BUTTON_PIN: Pin = board.GP22
BUTTON_MATRIX_COLUMN_PINS: tuple[Pin] = (board.GP0, board.GP1, board.GP2, board.GP3, board.GP4, board.GP5)
BUTTON_MATRIX_ROW_PINS: tuple[Pin] = (board.GP10, board.GP11, board.GP12, board.GP13, board.GP14, board.GP15)
ENCODER_PINS: tuple[tuple[Pin]] = (
    (board.GP8, board.GP9),
    (board.GP16, board.GP17),
    (board.GP18, board.GP19),
    (board.GP20, board.GP21),
    (board.GP27, board.GP28)
)


class ButtonBox:
    joystick: Joystick
    buttons_count: int
    button_matrix_offset: int | None
    button_matrix_columns: list[DigitalInOut] | None
    button_matrix_rows: list[DigitalInOut] | None
    gnd_buttons_offset: int | None
    gnd_buttons: list[DigitalInOut] | None
    encoder_button_offset: int | None
    encoders: dict[int, IncrementalEncoder] | None

    def __init__(
        self, button_matrix_column_pins: tuple[Pin] = None, button_matrix_row_pins: tuple[Pin] = None,
        gnd_buttons_pins: tuple[Pin] = None, encoder_pins: tuple[tuple[Pin]] = None
    ):
        print('Initializing ButtonBox')
        self.buttons_count = 0
        self.joystick = Joystick(usb_hid.devices)
        self._setup_button_matrix(button_matrix_column_pins, button_matrix_row_pins)
        self._setup_gnd_buttons(gnd_buttons_pins)
        self._setup_encoders(encoder_pins)
        print(f'ButtonBox initialized with {self.buttons_count} buttons')

    def _setup_button_matrix(self, button_matrix_column_pins: tuple[Pin] | None, button_matrix_row_pins: tuple[Pin] | None):
        self.button_matrix_columns = None
        self.button_matrix_rows = None
        self.button_matrix_offset = None
        if not button_matrix_column_pins and not button_matrix_row_pins:
            return
        assert button_matrix_column_pins and button_matrix_row_pins, 'Provide both button matrix arguments - columns and rows - or neither, but not one without the other'

        self.button_matrix_offset = self.buttons_count + 1
        self.button_matrix_columns = {
            i: DigitalInOut(pin_id)
            for i, pin_id in enumerate(button_matrix_column_pins)
        }
        for col in self.button_matrix_columns.values():
            col.pull = Pull.UP
        self.button_matrix_rows = {
            i: DigitalInOut(pin_id)
            for i, pin_id in enumerate(button_matrix_row_pins)
        }
        count = len(self.button_matrix_columns) * len(self.button_matrix_rows)
        print(f'Initialized {count} button matrix buttons')
        self.buttons_count += len(self.button_matrix_columns) * len(self.button_matrix_rows)

    def _setup_gnd_buttons(self, gnd_buttons_pins: tuple[Pin] | None):
        self.gnd_buttons = None
        self.gnd_buttons_offset = self.buttons_count + 1
        if not gnd_buttons_pins:
            return

        self.gnd_buttons = list()
        for pin in gnd_buttons_pins:
            dpin = DigitalInOut(pin)
            dpin.pull = Pull.UP
            self.gnd_buttons.append(dpin)
        count = len(self.gnd_buttons)
        print(f'Initialized {count} gnd buttons')
        self.buttons_count += count

    def _setup_encoders(self, encoder_pins: tuple[tuple[Pin]] | None):
        self.encoders = None
        self.encoder_button_offset = None
        if not encoder_pins:
            return

        self.encoder_button_offset = self.buttons_count + 1
        self.encoders = {
            i: IncrementalEncoder(
                pin_a=pins[0],
                pin_b=pins[1],
                divisor=4  # 1 detent per increment
            ) for i, pins in enumerate(encoder_pins)
        }
        count = len(self.encoders)
        print(f'Initialized {count} encoders')
        self.buttons_count += count * 2

    def process_inputs(self):
        self.scan_button_matrix()
        self.scan_gnd_buttons()
        self.scan_encoders()
        self.joystick.send()

    def scan_button_matrix(self):
        """
        NOTE: Does not trigger sending joystick reports
        """
        if self.button_matrix_columns is None:
            return
        for rid, row in self.button_matrix_rows.items():
            row.switch_to_output(value=False)
            for cid, col in self.button_matrix_columns.items():
                button = (rid * 6) + cid + self.button_matrix_offset
                self.joystick.set_button(
                    button=button,
                    pressed=not col.value  # inverted - 1 is released, 0 is pressed
                )
            row.switch_to_input()

    def scan_gnd_buttons(self):
        """
        NOTE: Does not trigger sending joystick reports
        """
        if self.gnd_buttons is None:
            return
        for i, gnd_button in enumerate(self.gnd_buttons):
            self.joystick.set_button(
                button=i + self.gnd_buttons_offset,
                pressed=not gnd_button.value  # inverted - 1 is released, 0 is pressed
            )

    def scan_encoders(self):
        if self.encoders is None:
            return
        for i, encoder in self.encoders.items():
            left_button = self.encoder_button_offset + i*2
            right_button = left_button + 1  # pins have to be in ascending order, so we do the same with button ids
            pos = encoder.position
            if pos == 0:
                continue
            encoder.position = 0
            if pos < 0:
                self.joystick.click_button(left_button)
            elif pos > 0:
                self.joystick.click_button(right_button)


button_box = ButtonBox(
    gnd_buttons_pins=(ESCAPE_BUTTON_PIN,),
    button_matrix_column_pins=BUTTON_MATRIX_COLUMN_PINS,
    button_matrix_row_pins=BUTTON_MATRIX_ROW_PINS,
    encoder_pins=ENCODER_PINS
)
while True:
    button_box.process_inputs()
