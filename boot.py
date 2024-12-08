import storage
import supervisor
import usb_cdc
import usb_hid
import usb_midi

from board import GP22
from digitalio import DigitalInOut, Pull


supervisor.set_usb_identification(
    manufacturer='Example',
    product='Button Box v1',
    vid=0xF055,  # inofficial vendor id for FOSS projects
    pid=0x0000   # choose a distinctive product id of your own
)

# Joystick with 64 digital buttons
JOYSTICK_REPORT_DESCRIPTOR = bytes((
    0x05, 0x01,  # Usage Page (Generic Desktop Ctrls)
    0x09, 0x04,  # Usage (Joystick)
    0xA1, 0x01,  # Collection (Application)
    0x85, 0x01,  #   Report ID (1)
    0x05, 0x09,  #   Usage Page (Button)
    0x19, 0x01,  #   Usage Minimum (Button 1)
    0x29, 0x40,  #   Usage Maximum (Button 64)
    0x15, 0x00,  #   Logical Minimum (0), buttons are binary after all
    0x25, 0x01,  #   Logical Maximum (1), buttons are binary after all
    0x75, 0x01,  #   Report Size (1), each button is 1 bit
    0x95, 0x40,  #   Report Count (64), so 64 buttons * 1 bit
    0x81, 0x02,  #   Input (Data,Var,Abs)
    0xC0,        # End Collection
))

joystick = usb_hid.Device(
    report_descriptor=JOYSTICK_REPORT_DESCRIPTOR,
    usage_page=0x01,           # Generic Desktop Control
    usage=0x04,                # Joystick
    report_ids=(1,),           # Descriptor uses report ID 1.
    in_report_lengths=(8,),    # This joystick sends 8 bytes in its report.
    out_report_lengths=(0,),   # It does not receive any reports.
)

usb_hid.enable(
    (joystick,)
)

ESCAPE_BUTTON = DigitalInOut(GP22)
ESCAPE_BUTTON.pull = Pull.UP
# Uncomment the following lines to disable serial by default
# Make sure you've changed the pin of the escape button to your setup and connected a button to it against GND
# Otherwise you'll not be able to enable serial anymore and have to reflash your board
# See for more info: https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/circuitpy-midi-serial
"""
if ESCAPE_BUTTON.value:
    # Disables serial & co. if escape button is not pressed.
    storage.disable_usb_drive()
    usb_cdc.disable()
    usb_midi.disable()
"""
