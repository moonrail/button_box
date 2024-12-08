# SPDX-FileCopyrightText: 2018 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`Joystick`
====================================================

* Author(s): Dan Halbert, Jan Gaßner

Modified version of Dan Halberts example without joystick, with more buttons and different interfaces.

Original version: https://github.com/adafruit/Adafruit_CircuitPython_HID/blob/6.0.3/examples/hid_gamepad.py
"""

import struct
import time

from adafruit_hid import find_device
from usb_hid import Device


class Joystick:
    """
    Emulates a generic joystick with 64 buttons, numbered 1-64
    """
    MIN_REPORT_SEND_GAP_S: float = 0.02
    """
    Minimum amount of seconds between HID reports being sent to the USB host

    This solves several potential issues:
    - debounce (for e.g. buttons with a flaky signal)
    - an application not detecting button presses (potentially due to application internal debounce logic)
      - this can be checked by using e.g. a tool like jstest and showing button presses - if jstest sees them, but the application does not, the application is at "fault"
    - load on the USB host, due to e.g. too many HID reports in a short amount of time

    NOTE: Increasing this value will lead to ignored inputs, as this is used via a synchronous sleep.
    Any inputs being made and "unmade" (e.g. button press AND release) while sleeping will not be recognized.
    """

    def __init__(self, devices: list[Device] | Device):
        """
        Creates a Joystick object that will send USB joystick HID reports

        devices -- a list of devices that include a joystick device or a joystick device
        itself. A device is any object that implements `send_report()`, `usage_page` and
        `usage`.
        """
        self._device = find_device(devices, usage_page=0x1, usage=0x04)
        self._earliest_report_send_threshold: float = 0.0

        # Reuse this bytearray to send reports.
        # Typically controllers start numbering buttons at 1 rather than 0.
        # report[0] buttons 1-8 (LSB is button 1)
        # report[1] buttons 9-16
        # report[2] buttons 17-24
        # report[3] buttons 25-32
        # report[4] buttons 33-40
        # report[5] buttons 41-48
        # report[6] buttons 49-56
        # report[7] buttons 57-64
        self._report = bytearray(8)

        # Remember the last report as well, so we can avoid sending
        # duplicate reports.
        self._last_report = bytearray(8)

        # Store settings separately before putting into report. Saves code
        # especially for buttons.
        self._buttons_1_to_32_state = 0
        self._buttons_33_to_64_state = 0

        # Send an initial report to test if HID device is ready.
        # If not, wait a bit and try once more.
        try:
            self.reset_all()
        except OSError:
            time.sleep(1)
            self.reset_all()

    def _get_state_for_button(self, button: int):
        """
        button -- button number to press (starting at 1)

        returns specific button state
        """
        if button < 1:
            raise ValueError(f'Button {button} does not exist - numbering starts at `1`')
        elif button < 33:
            return bool((self._buttons_1_to_32_state >> (button - 1)) & 1)
        elif button < 65:
            return bool((self._buttons_33_to_64_state >> (button - 33)) & 1)
        else:
            raise ValueError(f'Button {button} does not exist')

    def _set_state_for_button(self, button: int, value: bool | int, send=False):
        """
        sets specific button state

        button -- button number to press (starting at 1)

        value -- value to set state to

        send -- if report should be send
        """
        if button < 1:
            raise ValueError(f'Button {button} does not exist - numbering starts at `1`')
        elif button < 33:
            if value:
                self._buttons_1_to_32_state |= 1 << (button - 1)
            else:
                self._buttons_1_to_32_state &= ~(1 << (button - 1))
        elif button < 65:
            if value:
                self._buttons_33_to_64_state |= 1 << (button - 33)
            else:
                self._buttons_33_to_64_state &= ~(1 << (button - 33))
        else:
            raise ValueError(f'Button {button} does not exist')
        if send:
            self.send()

    def set_button(self, button: int, pressed: bool | int, send=False):
        """
        releases or presses button

        button -- button number to press (starting at 1)

        pressed -- if button is pressed

        send -- if report should be send upon change
        """
        current_state = self._get_state_for_button(button)
        if current_state and not pressed:
            # print(f'Releasing button {button}')
            self._set_state_for_button(
                button=button,
                value=False,
                send=send
            )
        elif not current_state and pressed:
            # print(f'Pressing button {button}')
            self._set_state_for_button(
                button=button,
                value=True,
                send=send
            )

    def click_button(self, button: int):
        """
        presses and releases button asap and sends state to host inbetween

        NOTE: if button is already pressed, will not release beforehand

        button -- button number to press (starting at 1)
        """
        self.set_button(
            button=button,
            pressed=True,
            send=True
        )
        self.set_button(
            button=button,
            pressed=False,
            send=True
        )

    def reset_all(self):
        """
        releases all buttons and sends report
        """
        self._buttons_1_to_32_state = 0
        self._buttons_33_to_64_state = 0
        self.send(force=True)

    def send(self, force=False):
        """
        sends a report with all data (e.g. button states) to host

        force -- send even if no changes present
        """
        struct.pack_into(
            "<II",
            self._report,
            0,
            self._buttons_1_to_32_state,
            self._buttons_33_to_64_state
        )

        if force or self._last_report != self._report:
            gap = self._earliest_report_send_threshold - time.monotonic()
            if gap > 0:
                time.sleep(gap)
            self._device.send_report(self._report)
            # Remember what we sent, without allocating new storage.
            self._last_report[:] = self._report
            self._earliest_report_send_threshold = time.monotonic() + self.MIN_REPORT_SEND_GAP_S
