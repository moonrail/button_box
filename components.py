from microcontroller import Pin
from rotaryio import IncrementalEncoder


class Encoder:
    BUTTON_COUNT = 2  # only rotary click buttons are counted

    def __init__(self, pin_a: Pin, pin_b: Pin, divisor: int = 4):
        self.encoder = IncrementalEncoder(
            pin_a=pin_a,
            pin_b=pin_b,
            divisor=divisor
        )
        self.last_position = self.encoder.position

    def get_click_amount(self):
        """
        returns amount of clicks made with encoder since last position check
        - negative values describe left turn direction
        - positive values describe right turn direction
        """
        position = self.encoder.position
        if position == self.last_position:
            return 0

        click_amount: int = abs(position - self.last_position)
        if position < self.last_position:
            click_amount *= -1
        self.last_position = position
        return click_amount
