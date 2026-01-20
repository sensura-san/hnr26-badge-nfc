## environment setup
for easily accessing the esp32 micropython REPL prompt over serial:
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

alternatively:
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
