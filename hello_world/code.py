from time import sleep
from typing import Optional

import board
import digitalio
import displayio
from adafruit_debouncer import Debouncer
from adafruit_display_text import label
from adafruit_displayio_ssd1306 import SSD1306
from adafruit_pn532.i2c import PN532_I2C
from i2cdisplaybus import I2CDisplayBus
from terminalio import FONT

"""
breakdown of dumped code.py:
- StateMachine handles different states of the board independently,
- and consumes different states to update generic classes for buttons, etc.
- each state is a different screen

StateMachine:
- self.ctx holds the display group (initalised as displayio.Group() in InitState)

State:
- all states inherit the superclass State
- subclasses call super().enter(machine, self.tag) to set tag
- subclasses call super().update(machine) to sample input states every tick
    - e.g. [subclass] -> State -> StateMachine -> btn_a.update(), btn_b [...]
    - e.g. btn_a.update() is like doing Debouncer().update()

InitState:
- inits i2c comms., all labels (w/ correct x-coords), and buttons
- sets machine.btn_x to Debouncer, which has helper flags like btn.value, btn.rose, btn.fell (debouncer needs to be updated every tick)

LABELS:
label_title:    y=8  (default)
label_body_top: y=24
label_body_btm: y=36

BUTTONS:
btn_a_pin = board.D7
btn_b_pin = board.D9
btn_c_pin = board.D8
"""
"""
code outline:
- initialise starting state,
- then goto counter
- should handle button presses to increment / decrement values
"""
# TODO: add typing, finish nfc impl.

class ScreenLabel(label.Label):
    def __init__(self):
        super().__init__(FONT, text="", x=0, y=8)

    def update(self, text=None, x=None, y=None):
        if text is not None:
            self.text = text

        if x is not None:
            self.x = x

        if y is not None:
            self.y = y

    def clear(self):
        self.update(text="")

class State:
    tag = "_state"

    def __init__(self):
        pass

    def enter(self, machine, state_tag):
        # machine.serial.state_tag = state_tag
        pass

    def leave(self, machine):
        pass

    def update(self, machine):
        machine.btn_a.update()
        machine.btn_b.update()
        machine.btn_c.update()
        # machine.serial.update()

class StateMachine:
    def __init__(self):
        self.state = None
        self.states = {}

        # self.serial = Serial()

        self.ctx = None
        self.label_title = ScreenLabel()
        self.label_body_top = ScreenLabel()
        self.label_body_btm = ScreenLabel()
        self.label_btn_a = ScreenLabel()
        self.label_btn_b = ScreenLabel()
        self.label_btn_c = ScreenLabel()
        self.btn_a = None
        self.btn_b = None
        self.btn_c = None
        self.pn532: Optional[PN532_I2C] = None

    def add_state(self, state):
        self.states[state.tag] = state

    def go_to_state(self, state_name, **kwargs):
        if self.state:
            self.state.leave(self)

        self.state = self.states[state_name]
        self.state.enter(self, **kwargs)

    def update(self):
        if self.state:
            self.state.update(self)

    # def set_body_visible(self):
    #     if self.ctx:
    #         self.ctx.pop()
    #         self.ctx.append(self.label_body_top)
    #         self.ctx.append(self.label_body_btm)
            
class InitState(State):
    tag = "init"

    def __init__(self):
        pass

    def enter(self, machine):
        super().enter(machine, self.tag)

        # Release any resources currently in use for the displays
        displayio.release_displays()

        # Set up I2C communication
        i2c = board.I2C()
        display_bus = I2CDisplayBus(i2c, device_address=0x3C)
        display = SSD1306(display_bus, width=128, height=64)

        # Make the display context
        machine.ctx = displayio.Group()
        display.root_group = machine.ctx

        # Create title label
        machine.label_title.update(text="HnR'26 NFC controller")
        machine.ctx.append(machine.label_title)

        # Create button labels
        machine.label_btn_a.update(y=56)
        machine.ctx.append(machine.label_btn_a)

        machine.label_btn_b.update(y=56)
        machine.ctx.append(machine.label_btn_b)

        machine.label_btn_c.update(y=56)
        machine.ctx.append(machine.label_btn_c)

        # Create body labels (w/ text for label_body_top)
        machine.label_body_top.update(text="I coloured my badge\nand all I got was \nthis lousy PCB", y=24)
        machine.ctx.append(machine.label_body_top)
        sleep(3)

        machine.label_body_btm.update(y=36)
        machine.ctx.append(machine.label_body_btm)

        # Set up buttons
        btn_a_pin = digitalio.DigitalInOut(board.D7)
        btn_a_pin.direction = digitalio.Direction.INPUT
        btn_a_pin.pull = digitalio.Pull.UP
        machine.btn_a = Debouncer(btn_a_pin, interval=0.05)

        btn_b_pin = digitalio.DigitalInOut(board.D9)
        btn_b_pin.direction = digitalio.Direction.INPUT
        btn_b_pin.pull = digitalio.Pull.UP
        machine.btn_b = Debouncer(btn_b_pin, interval=0.05)

        btn_c_pin = digitalio.DigitalInOut(board.D8)
        btn_c_pin.direction = digitalio.Direction.INPUT
        btn_c_pin.pull = digitalio.Pull.UP
        machine.btn_c = Debouncer(btn_c_pin, interval=0.05)
        
        while True:
            try:
                machine.pn532 = PN532_I2C(i2c)
            except(ValueError, RuntimeError):
                print("Cannot connect to PN532 NFC, trying again...")
                sleep(1)
            else:
                break    

        # configure PN532 to communicate w/ MiFare cards
        machine.pn532.SAM_configuration()

        machine.go_to_state(CounterState.tag)

    def leave(self, machine):
        pass

    def update(self, machine):
        pass


class CounterState(State):
    tag = "counter"

    def __init__(self):
        self.index = 0

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="meow counter!")
        machine.label_body_top.update(text=f"value: {self.index}")
        machine.label_body_btm.clear()
        machine.label_btn_a.update(text="+1")
        machine.label_btn_b.update(text="reset", x=52)
        machine.label_btn_c.update(text="-1", x=117)

    def leave(self):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_a.fell:
            self.index += 1
            machine.label_body_top.update(text=f"value: {self.index}")
        if machine.btn_b.fell:
            self.index = 0
            machine.label_body_top.update(text=f"value: {self.index}")
        if machine.btn_c.fell:
            self.index -= 1
            machine.label_body_top.update(text=f"value: {self.index}")


# current impl. for the original hnr badge,
# but will probs see how it can be used for amusement IC cards
class NfcReadState(State):
    tag = "nfc_read"

    def __init__(self):
        pass
    
    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="Read badge ID")
        machine.label_body_top.update(text="Tap to badge QR code,")
        machine.label_body_btm.update(text="then press 'read'")
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.update(text="read", x=105)

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell:
            machine.go_to_state(NfcReadResultState.tag)


class NfcReadResultState(State):
    tag = "nfc_read_result"

    def __init__(self):
        self.nfc_id = None
        self.badge_id_bytes = None
    
    def enter(self, machine: StateMachine):
        super().enter(machine, self.tag)
    
        machine.label_title.update(text="Read badge ID")
        machine.label_body_top.update(text="Reading badge...")
        machine.label_body_btm.clear()
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.clear()

        self.nfc_id = machine.pn532.read_passive_target()

        if self.nfc_id is None:
            machine.label_body_top.update(text="No badge found qwq")
            machine.label_body_btm.update(text="try again?")
        else:
            nfc_id_text = f"NFC: 0x{self.nfc_id.hex()}"
            machine.label_body_top.update(text=nfc_id_text)
            
            self.badge_id_bytes = machine.pn532.ntag2xx_read_block(0x04)  # TODO: what is this sob

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)


class NfcWriteState(State):
    tag = "nfc_write"

    def __init__(self):
        pass
    
    def enter(self, machine):
        super().enter(machine, self.tag)

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)
        

def main():
    # Initialise a state machine to deal with the different screens and program
    # states
    machine = StateMachine()

    # Add all the possible states to the state machine
    machine.add_state(InitState())
    machine.add_state(CounterState())
    machine.add_state(NfcReadState())
    machine.add_state(NfcReadResultState())
    machine.add_state(NfcWriteState())

    # set state entry point
    machine.go_to_state(InitState.tag)

    # keep state machine updated every tick
    while True:
        machine.update()
    

if __name__ == "__main__":
    main()