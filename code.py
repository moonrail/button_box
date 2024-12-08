"""
Button Box with 64 possible buttons (as defined in joystick.py & boot.py)

As per current definition of Pins below of these 64 buttons 47 are mapped:
- Buttons 1-36: button matrix (6*6)
- Button 37: "escape" button, that also enables serial, if pressed at boot time
- Buttons 38-47: encoders (CounterClockwise * 5 + Clockwise * 5)
  - encoders will therefore work in stepwise-click-mode, so no support for mapping a single position to a single button
  - a step of the encoder causes a press and release of a button
"""

import board
import supervisor
import usb_hid

from components import Encoder
from joystick import Joystick
from digitalio import DigitalInOut, Pull
from microcontroller import Pin


# disable auto reload
supervisor.runtime.autoreload = False

# pin definition, customize as required
BUTTON_PINS: list[Pin] = [
    board.GP22  # Escape Button
]
BUTTON_MATRIX_COLUMN_PINS: list[Pin] = [
    board.GP0,
    board.GP1,
    board.GP2,
    board.GP3,
    board.GP4,
    board.GP5
]
BUTTON_MATRIX_ROW_PINS: list[Pin] = [
    board.GP10,
    board.GP11,
    board.GP12,
    board.GP13,
    board.GP14,
    board.GP15
]
ENCODERS: list[Encoder] = [
    Encoder(
        pin_a=board.GP9,
        pin_b=board.GP8
    ),
    Encoder(
        pin_a=board.GP17,
        pin_b=board.GP16
    ),
    Encoder(
        pin_a=board.GP19,
        pin_b=board.GP18
    ),
    Encoder(
        pin_a=board.GP21,
        pin_b=board.GP20
    ),
    Encoder(
        pin_a=board.GP28,
        pin_b=board.GP27
    )
]


class ButtonBox:
    joystick: Joystick
    button_count: int
    button_matrix_offset: int | None
    button_matrix_columns: list[DigitalInOut] | None
    button_matrix_rows: list[DigitalInOut] | None
    gnd_buttons_offset: int | None
    gnd_buttons: list[DigitalInOut] | None
    encoder_button_offset: int | None
    encoders: list[Encoder] | None

    def __init__(
        self, button_matrix_column_pins: list[Pin] | None = None, button_matrix_row_pins: list[Pin] | None = None,
        gnd_button_pins: list[Pin] | None = None, encoders: list[Encoder] | None = None
    ):
        print('Initializing ButtonBox')
        self.button_count = 0
        self.joystick = Joystick(usb_hid.devices)
        self._setup_button_matrix(button_matrix_column_pins, button_matrix_row_pins)
        self._setup_gnd_buttons(gnd_button_pins)
        self._setup_encoders(encoders)
        print(f'ButtonBox initialized with {self.button_count} buttons')

    def _setup_button_matrix(self, button_matrix_column_pins: tuple[Pin] | None, button_matrix_row_pins: tuple[Pin] | None):
        self.button_matrix_columns = None
        self.button_matrix_rows = None
        self.button_matrix_offset = None
        if not button_matrix_column_pins and not button_matrix_row_pins:
            return

        if not button_matrix_column_pins or not button_matrix_row_pins:
            raise ValueError('Provide both button matrix arguments - columns and rows - or neither, but not one without the other')

        self.button_matrix_offset = self.button_count + 1
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
        self.button_count += len(self.button_matrix_columns) * len(self.button_matrix_rows)

    def _setup_gnd_buttons(self, gnd_buttons_pins: tuple[Pin] | None):
        self.gnd_buttons = None
        self.gnd_buttons_offset = self.button_count + 1
        if not gnd_buttons_pins:
            return

        self.gnd_buttons = list()
        for pin in gnd_buttons_pins:
            dpin = DigitalInOut(pin)
            dpin.pull = Pull.UP
            self.gnd_buttons.append(dpin)
        count = len(self.gnd_buttons)
        print(f'Initialized {count} gnd buttons')
        self.button_count += count

    def _setup_encoders(self, encoders: list[Encoder] | None):
        self.encoders = None
        self.encoder_button_offset = -1
        if not encoders:
            return

        self.encoder_button_offset = self.button_count + 1
        self.encoders = encoders
        self.button_count += len(self.encoders) * Encoder.BUTTON_COUNT
        print(f'Initialized {len(self.encoders)} encoders from button #{self.encoder_button_offset} to #{self.button_count}')

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
        if self.gnd_buttons is None:
            return
        for i, gnd_button in enumerate(self.gnd_buttons):
            self.joystick.set_button(
                button=i + self.gnd_buttons_offset,
                pressed=not gnd_button.value
            )

    def scan_encoders(self):
        if self.encoders is None:
            return
        for i, encoder in enumerate(self.encoders):
            left_button = self.encoder_button_offset + i * Encoder.BUTTON_COUNT
            right_button = left_button + 1
            click_amount = encoder.get_click_amount()
            while click_amount < 0:
                # print(f'Encoder {i}: LB {left_button_id} click')
                self.joystick.click_button(left_button)
                click_amount += 1
            while click_amount > 0:
                # print(f'Encoder {i}: RB {right_button_id} click')
                self.joystick.click_button(right_button)
                click_amount -= 1


button_box = ButtonBox(
    gnd_button_pins=BUTTON_PINS,
    button_matrix_column_pins=BUTTON_MATRIX_COLUMN_PINS,
    button_matrix_row_pins=BUTTON_MATRIX_ROW_PINS,
    encoders=ENCODERS
)
while True:
    button_box.process_inputs()
