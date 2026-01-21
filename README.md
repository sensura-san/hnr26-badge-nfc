# hnr26-badge-nfc
monorepo related to development/experimentation on the hack and roll nfc badge reader~

## project ideas
- bus card info reader
- maimai card info reader..?! it has wifi after all... (but depends on their api hhh)
- pure c graphics manipulation on the screen per-pixel? see: https://youtu.be/xNX9H_ZkfNE

## project experiments
- [x] hello world test
- [x] counter programme (impl. original code for UI)
- [ ] nfc reader reimplementation
- [ ] image UI (does this need lower level?)
- [ ] spotify websocket thing

## dumped file structure

```
esp32c3-dump
|- fs/             # copy of device's root dir
|- full_flash.bin  # complete copy of flash
```

## environment setup (for interacting with device)
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
- hold BOOT
- press and release RESET
- release BOOT

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
esptool.py read_flash 0x000000 0x400000 full_flash.bin
```

