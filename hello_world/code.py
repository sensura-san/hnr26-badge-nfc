import board
import displayio
from adafruit_display_text import label
from adafruit_displayio_ssd1306 import SSD1306
from i2cdisplaybus import I2CDisplayBus
import terminalio

# set up i2c comms (w/ default pins on the esp)
i2c = board.I2C()

# set up display bus for the SSD1306 display
# 126x64 res, I2C address 0x3C
# datasheet: cdn-shop.adafruit.com/datasheets/SSD1306.pdf
displayio.release_displays()  # Release any resources currently in use for the displays

display_bus = I2CDisplayBus(i2c, device_address=0x3C)
display = SSD1306(display_bus, width=128, height=64)

# create display group (UI element container)
group = displayio.Group()
display.root_group = group

# create and add text labels
label_1 = label.Label(terminalio.FONT, text="mrrow!", y=8)
label_2 = label.Label(terminalio.FONT, text="nya!", y=24)
group.append(label_1)
group.append(label_2)

# keep programme running (to keep display on)
while True:
    pass