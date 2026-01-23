## documentation
### datasheets
- [SSD1306](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf)
- 128x64, I2C address 0x3C (0111100)

### code reference
- [CircuitPython: adafruit-circuitpython-ssd1306](https://docs.circuitpython.org/projects/ssd1306/en/latest/api.html)
- [CircuitPython: adafruit-circuitpython-pn532](https://adafru.it/DJA) 

## copy code.py file over
> ![NOTE] you cannot enter REPL in bootloader mode; ensure that you are outside of bootloader mode when doing serial connections

```bash
mpremote connect COM7 fs cp ./code.py :/code.py
```

