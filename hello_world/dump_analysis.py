from sys import stdin
from time import sleep

import board
import digitalio
import displayio
from adafruit_debouncer import Debouncer
from adafruit_display_text import label
from adafruit_displayio_ssd1306 import SSD1306
from adafruit_pn532.I2C import PN532_I2C
from foamyguy_displayio_listselect import ListSelect
from i2cdisplaybus import I2CDisplayBus
from supervisor import runtime
from terminalio import FONT


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


class ScreenListSelect(ListSelect):
    def __init__(self):
        super().__init__(
            items=("",), visible_items_count=2, cursor_char="> ", x=0, y=16
        )

    def update(self, items=None):
        if items is not None:
            self.items = items
            self._refresh_label()

    def clear(self):
        self.update(items=())


class SerialRecvData:
    def __init__(self):
        self._is_set = False
        self._err = None
        self._num = 0
        self._yes = False

    @property
    def is_set(self):
        return self._is_set

    @property
    def err(self):
        if self._err is not None:
            return self._err.args[0]

        return None

    @property
    def num(self):
        return self._num if self._is_set else 0

    @property
    def yes(self):
        return self._is_set and self._yes

    @property
    def no(self):
        return self._is_set and not self._yes

    def update(self, err=None, num=None, yes=None):
        self._is_set = True
        self._err = err

        if num is not None:
            self._num = num

        if yes is not None:
            self._yes = yes

    def clear(self):
        self._is_set = False
        self._err = None


class Serial:
    def __init__(self):
        self.state_tag = ""
        self._recv_type = None
        self._data = SerialRecvData()

    @property
    def _recv_bytes(self):
        # Check how many bytes are available
        num_bytes = runtime.serial_bytes_available

        if num_bytes > 0:
            # Read data if there are some bytes available
            input_bytes = stdin.read(num_bytes)
            # Allow only printable ASCII characters
            return "".join(
                c for c in input_bytes if ord(" ") <= ord(c) <= ord("~")
            )

        return None

    @property
    def data(self):
        return self._data

    def _recv_answer_bool(self, data):
        if not data:
            self._data.update(yes=True)
            return

        lower = data.lower()

        if lower == "y" or lower == "yes" or lower == "true" or lower == "1":
            self._data.update(yes=True)
        elif lower == "n" or lower == "no" or lower == "false" or lower == "0":
            self._data.update(yes=False)
        else:
            self._data.update(err=TypeError("Unknown boolean reply given"))

    def _recv_answer_int(self, data):
        if not data:
            self._data.update(err=ValueError("No reply given"))
            return

        try:
            num = int(data)
        except ValueError:
            self._data.update(err=TypeError("Unknown integer reply given"))
            return

        self._data.update(num=num)

    def send_line(self, message, is_tagged=True, **kwargs):
        if not runtime.serial_connected:
            return

        if is_tagged:
            print(f"{self.state_tag}: {message}", **kwargs)
        else:
            print(f"{message}", **kwargs)

        self._data.clear()

    def send_question_bool(self, message, **kwargs):
        message += " (Y/n): "

        self.send_line(message, end="", **kwargs)
        self._recv_type = bool

    def send_question_int(self, message, **kwargs):
        message += ": "

        self.send_line(message, end="", **kwargs)
        self._recv_type = int

    def send_question_try_again(self, message, **kwargs):
        message += ", try again"

        if self._recv_type == int:
            self.send_question_int(message, **kwargs)
        else:
            self.send_question_bool(message, **kwargs)

    def send_answer_if_no_recv(self, data):
        if self._data.is_set:
            return

        if self._recv_type == bool:
            self.send_line("y" if data else "n", is_tagged=False)
        else:
            self.send_line(data, is_tagged=False)

        self._recv_type = None

    def update(self):
        data = self._recv_bytes

        if data is None:
            return

        self._data.clear()

        if self._recv_type == bool:
            self._recv_answer_bool(data)
        elif self._recv_type == int:
            self._recv_answer_int(data)
        else:
            # Ignore arbitrary data typed into serial
            pass

        if self._data.err:
            self.send_question_try_again(self._data.err)
        else:
            self._recv_type = None


class State:
    tag = "_state"

    def __init__(self):
        pass

    def enter(self, machine, state_tag):
        machine.serial.state_tag = state_tag

    def leave(self, machine):
        pass

    def update(self, machine):
        machine.btn_a.update()
        machine.btn_b.update()
        machine.btn_c.update()
        machine.serial.update()


class StateMachine:
    def __init__(self):
        self.state = None
        self.states = {}

        self.serial = Serial()

        self.ctx = None
        self.label_title = ScreenLabel()
        self.label_body_top = ScreenLabel()
        self.label_body_bottom = ScreenLabel()
        self.menu = ScreenListSelect()
        self.label_btn_a = ScreenLabel()
        self.label_btn_b = ScreenLabel()
        self.label_btn_c = ScreenLabel()
        self.pn532 = None
        self.btn_a = None
        self.btn_b = None
        self.btn_c = None

        self.last_written_badge_id = 0

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

    def set_body_visible(self):
        if self.ctx:
            self.ctx.pop()
            self.ctx.append(self.label_body_top)
            self.ctx.append(self.label_body_bottom)

    def set_menu_visible(self):
        if self.ctx:
            self.ctx.pop()
            self.ctx.pop()
            self.ctx.append(self.menu)
            self.label_body_top.clear()
            self.label_body_bottom.clear()


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

         
        
        # Connect to PN532 NFC module
        
        machine.label_body_top.update(text="I coloured my badge\nand all I got was \nthis lousy PCB", y=24)
        machine.ctx.append(machine.label_body_top)
        sleep(3)
        #machine.label_body_top.update(text="Loading...", y=24)
        
        machine.label_body_bottom.update(y=36)
        machine.ctx.append(machine.label_body_bottom)

        while True:
            try:
                machine.pn532 = PN532_I2C(i2c)
            except (ValueError, RuntimeError):
                print("Cannot connect to PN532 NFC, trying again...")
                sleep(1)
            else:
                break

        # Configure PN532 to communicate with MiFare cards
        machine.pn532.SAM_configuration()

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

        machine.go_to_state(MenuState.tag)

    def leave(self, machine):
        pass

    def update(self, machine):
        pass


class MenuState(State):
    tag = "menu"

    def __init__(self):
        self.items = (
            "Scan badge for food",
            "Read badge ID",
            "Write badge ID",
            "[Debug] NFC info",
        )
        self.states = (
            ScanFoodState.tag,
            BadgeReadState.tag,
            BadgeWriteState.tag,
            NfcInfoState.tag,
        )

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="HnR'26 NFC controller")
        machine.label_btn_a.update(text="up")
        machine.label_btn_b.update(text="down", x=52)
        machine.label_btn_c.update(text="go", x=117)

        # Create list select menu
        machine.menu.update(items=self.items)
        machine.set_menu_visible()

    def leave(self, machine):
        machine.set_body_visible()

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell:
            machine.go_to_state(self.states[machine.menu.selected_index])
        elif machine.btn_a.fell and not machine.btn_b.fell:
            if machine.menu.selected_index == 0:
                machine.menu.selected_index = len(machine.menu.items) - 1
            else:
                machine.menu.move_selection_up()
        elif machine.btn_b.fell and not machine.btn_a.fell:
            if machine.menu.selected_index == len(machine.menu.items) - 1:
                machine.menu.selected_index = 0
            else:
                machine.menu.move_selection_down()


class ScanFoodState(State):
    tag = "scan_food"

    def __init__(self):
        pass

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="Scan badge for food")
        machine.label_body_top.update(text="Not implemented yet!")
        machine.label_body_bottom.clear()
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.update(text="menu", x=105)

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell:
            machine.go_to_state(MenuState.tag)


class BadgeReadState(State):
    tag = "badge_read"

    def __init__(self):
        pass

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="Read badge ID")
        machine.label_body_top.update(text="Tap to badge QR code,")
        machine.label_body_bottom.update(text="then press 'read'")
        machine.label_btn_a.update(text="menu")
        machine.label_btn_b.clear()
        machine.label_btn_c.update(text="read", x=105)

        machine.serial.send_question_bool("Scan badge ID?")

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell or machine.serial.data.yes:
            machine.serial.send_answer_if_no_recv(True)
            machine.go_to_state(BadgeReadResultState.tag)
        elif machine.btn_a.fell or machine.serial.data.no:
            machine.serial.send_answer_if_no_recv(False)
            machine.go_to_state(MenuState.tag)


class BadgeReadResultState(State):
    tag = "badge_read_result"

    def __init__(self):
        self.nfc_id = None
        self.badge_id_bytes = None

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="Read badge ID")
        machine.label_body_top.update(text="Reading badge...")
        machine.label_body_bottom.clear()
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.clear()

        # Check if a badge is available to read
        self.nfc_id = machine.pn532.read_passive_target()

        if self.nfc_id is None:
            machine.label_body_top.update(text="No badge found ;-;")
            machine.label_body_bottom.update(text="Try again?")

            machine.serial.send_question_try_again("No badge found")
        else:
            nfc_id_text = f"NFC: 0x{self.nfc_id.hex()}"
            machine.label_body_top.update(text=nfc_id_text)
            machine.serial.send_line(nfc_id_text)

            self.badge_id_bytes = machine.pn532.ntag2xx_read_block(0x04)

            if self.badge_id_bytes is None:
                machine.label_body_bottom.update(text="Try again!")
                machine.serial.send_question_try_again(
                    "Failed to read badge ID"
                )
            else:
                badge_id_text = (
                    f"Badge ID: {int.from_bytes(self.badge_id_bytes)}"
                )
                machine.label_title.update(text="Read successful")
                machine.label_body_bottom.update(text=badge_id_text)

                machine.serial.send_line(badge_id_text)
                machine.serial.send_question_bool("Scan another badge ID?")

        machine.label_btn_a.update(text="menu")
        machine.label_btn_c.update(text="retry", x=99)

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell or machine.serial.data.yes:
            machine.serial.send_answer_if_no_recv(True)
            machine.go_to_state(BadgeReadResultState.tag)
        elif machine.btn_a.fell or machine.serial.data.no:
            machine.serial.send_answer_if_no_recv(False)
            machine.go_to_state(MenuState.tag)


class BadgeWriteState(State):
    tag = "badge_write"

    def __init__(self):
        self.badge_id = 0

    def enter(self, machine, badge_id=None):
        super().enter(machine, self.tag)

        if badge_id is None:
            if machine.last_written_badge_id < 9999:
                self.badge_id = machine.last_written_badge_id + 1
            else:
                self.badge_id = 0
        else:
            self.badge_id = badge_id

        machine.label_title.update(text="Write badge ID")
        machine.label_body_top.update(text="Badge ID to write:")
        machine.label_body_bottom.update(text=f"{self.badge_id}")
        machine.label_btn_a.update(text="next" if self.badge_id else "menu")
        machine.label_btn_b.update(text="inc", x=56)
        machine.label_btn_c.update(text="done", x=105)

        machine.serial.send_question_int("Write badge ID (<0 to menu)")

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell or machine.serial.data.is_set:
            if machine.serial.data.is_set:
                if machine.serial.data.num < 0:
                    machine.go_to_state(MenuState.tag)
                    return

                if machine.serial.data.num > 9999:
                    machine.serial.send_question_int(
                        "Badge ID must be non-negative 4 digit number, try again"
                    )
                    return

                self.badge_id = machine.serial.data.num

            machine.serial.send_answer_if_no_recv(self.badge_id)
            machine.go_to_state(
                BadgeWriteConfirmState.tag, badge_id=self.badge_id
            )
        elif machine.btn_a.fell and not machine.btn_b.fell:
            if self.badge_id == 0:
                machine.serial.send_answer_if_no_recv(-1)
                machine.go_to_state(MenuState.tag)
                return

            self.badge_id *= 10

            if self.badge_id > 9999:
                self.badge_id %= 10000

                if self.badge_id == 0:
                    machine.label_btn_a.update(text="menu")

            machine.label_body_bottom.update(text=f"{self.badge_id}")
        elif machine.btn_b.fell and not machine.btn_a.fell:
            if self.badge_id % 10 == 9:
                self.badge_id -= 9

                if self.badge_id == 0:
                    machine.label_btn_a.update(text="menu")
            else:
                self.badge_id += 1

                if self.badge_id % 10 == 1:
                    machine.label_btn_a.update(text="next")

            machine.label_body_bottom.update(text=f"{self.badge_id}")


class BadgeWriteConfirmState(State):
    tag = "badge_write_confirm"

    def __init__(self):
        self.badge_id = None

    def enter(self, machine, badge_id=None):
        super().enter(machine, self.tag)

        if badge_id is None:
            machine.serial.send_line("Badge ID is not set")
            machine.go_to_state(BadgeWriteState.tag)
            return

        machine.label_title.update(text=f"Write badge ID {badge_id}")
        machine.label_body_top.update(text="Tap to badge QR code,")
        machine.label_body_bottom.update(text="then press 'write'")
        machine.label_btn_a.update(text="back")
        machine.label_btn_b.clear()
        machine.label_btn_c.update(text="write", x=99)

        machine.serial.send_question_bool(f"Write badge ID {badge_id}?")

        self.badge_id = badge_id

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell or machine.serial.data.yes:
            machine.serial.send_answer_if_no_recv(True)
            machine.go_to_state(
                BadgeWriteResultState.tag, badge_id=self.badge_id
            )
        elif machine.btn_a.fell or machine.serial.data.no:
            machine.serial.send_answer_if_no_recv(False)
            machine.go_to_state(BadgeWriteState.tag, badge_id=self.badge_id)


class BadgeWriteResultState(State):
    tag = "badge_write_result"

    def __init__(self):
        self.is_write_success = False
        self.new_badge_id = None
        self.nfc_id = None
        self.old_badge_id_bytes = None
        self.new_badge_id_bytes = None

    def enter(self, machine, badge_id=None):
        super().enter(machine, self.tag)

        if badge_id is None:
            machine.go_to_state(BadgeWriteState.tag)
            return

        machine.label_title.update(text=f"Write badge ID {badge_id}")
        machine.label_body_top.update(text="Writing badge...")
        machine.label_body_bottom.clear()
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.clear()

        self.is_write_success = False

        # Check if a badge is available to read
        self.nfc_id = machine.pn532.read_passive_target()

        if self.nfc_id is None:
            machine.label_body_top.update(text="No badge found ;-;")
            machine.serial.send_line("No badge found")
        else:
            nfc_id_text = f"NFC: 0x{self.nfc_id.hex()}"
            machine.label_body_top.update(text=nfc_id_text)
            machine.serial.send_line(nfc_id_text)

            self.old_badge_id_bytes = machine.pn532.ntag2xx_read_block(0x04)

            if self.old_badge_id_bytes is not None:
                self.is_write_success = machine.pn532.ntag2xx_write_block(
                    0x04, badge_id.to_bytes(4)
                )

                if self.is_write_success:
                    self.new_badge_id_bytes = machine.pn532.ntag2xx_read_block(
                        0x04
                    )

                    if (
                        self.new_badge_id_bytes is not None
                        and self.new_badge_id_bytes == badge_id
                    ):
                        self.is_write_success = True

        if self.is_write_success:
            badge_id_text = (
                f"Badge ID: {int.from_bytes(self.old_badge_id_bytes)}"
                + f" > {int.from_bytes(self.new_badge_id_bytes)}"
            )

            machine.label_title.update(text="Write successful")
            machine.label_body_bottom.update(text=badge_id_text)
            machine.label_btn_c.update(text="menu", x=105)

            machine.serial.send_line(badge_id_text)
            machine.serial.send_question_bool("Write another badge ID?")

            machine.last_written_badge_id = badge_id
        else:
            machine.label_body_bottom.update(text="FAILED TO WRITE!")
            machine.label_btn_c.update(text="retry", x=99)

            machine.serial.send_question_try_again("Failed to write badge ID")

        machine.label_btn_a.update(text="back")
        self.new_badge_id = badge_id

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if self.is_write_success:
            if machine.btn_c.fell or machine.serial.data.no:
                machine.serial.send_answer_if_no_recv(False)
                machine.go_to_state(MenuState.tag)
            elif machine.btn_a.fell or machine.serial.data.yes:
                machine.serial.send_answer_if_no_recv(True)
                machine.go_to_state(BadgeWriteState.tag)
        else:
            if machine.btn_c.fell or machine.serial.data.yes:
                machine.serial.send_answer_if_no_recv(True)
                machine.go_to_state(
                    BadgeWriteResultState.tag, badge_id=self.new_badge_id
                )
            elif machine.btn_a.fell or machine.serial.data.no:
                machine.serial.send_answer_if_no_recv(False)
                machine.go_to_state(
                    BadgeWriteState.tag, badge_id=self.new_badge_id
                )


class NfcInfoState(State):
    tag = "nfc_info"

    def __init__(self):
        self.ic = None
        self.ver = None
        self.rev = None
        self.sup = None

    def enter(self, machine):
        super().enter(machine, self.tag)

        machine.label_title.update(text="[Debug] NFC info")
        machine.label_body_top.update(text="Loading...")
        machine.label_body_bottom.clear()
        machine.label_btn_a.clear()
        machine.label_btn_b.clear()
        machine.label_btn_c.clear()

        self.ic, self.ver, self.rev, self.sup = machine.pn532.firmware_version

        machine.label_body_top.update(
            text=f"PN5{self.ic:02x} v{self.ver}.{self.rev}"
        )
        machine.label_body_bottom.update(text=f"support {self.sup:#04x}")

        machine.label_btn_c.update(text="menu", x=105)

    def leave(self, machine):
        pass

    def update(self, machine):
        super().update(machine)

        if machine.btn_c.fell:
            machine.go_to_state(MenuState.tag)


def main():
    # Initialise a state machine to deal with the different screens and program
    # states
    machine = StateMachine()

    # Add all the possible states to the state machine
    machine.add_state(InitState())
    machine.add_state(MenuState())
    machine.add_state(ScanFoodState())
    machine.add_state(BadgeReadState())
    machine.add_state(BadgeReadResultState())
    machine.add_state(BadgeWriteState())
    machine.add_state(BadgeWriteConfirmState())
    machine.add_state(BadgeWriteResultState())
    machine.add_state(NfcInfoState())

    # Set the state entry point
    machine.go_to_state(InitState.tag)

    # Keep the state machine updated every tick
    while True:
        machine.update()


if __name__ == "__main__":
    # Program entry point
    main()
