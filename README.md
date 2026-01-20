## environment setup
### access micropython REPL using `mpremote`
```bash
uv tool install mpremote
```

to enter REPL on the serial device:
```bash
mpremote repl
```
- then `CTRL + C` to enter device's REPL prompt. (ends running programme and exits into REPL)
- `CTRL + D` to re-run previously ended programme (by soft-rebooting micropython interpreter)
- `CTRL + X` to exit prompt

### alternatively using screen
```bash
screen /dev/ttyACM0
```
- then `CTRL + C` to enter REPL
- use `CTRL + A, then K, then Y` to exit screen

## dumping files
using `mpremote`, use:
```bash
mpremote connect /dev/ttyACM0 fs cp :<file_to_dump> ./<location_in_cwd>
```

in this specific micropython environment, because the environment is either outdated or too minimal, the `ls` and `cp -r` commands don't work on `mpremote` as they rely on `ilistdir()` which isn't implemented.

therefore, use:
```bash
mpremote run copytree.py
```
then manually copy the output files one-by-one into the correct directories using the earlier `cp` command (yeah is scuffed)

## dumping flash
put esp into bootloader mode:
```bash
- hold BOOT
- press and release RESET
- realse BOOT
```

install `esptool`:
```bash
uv tool install esptool
```

check connection:
```bash
esptool --chip esp32c3 chip_id
```

find flash size (for dumping):
```bash
esptool flash_id
```

dump entire flash:
```bash
esptool.py read_flash 0x000000 0x400000 full_flash_dump.bin
```
