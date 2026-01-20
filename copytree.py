# Run this on the device via REPL
import os

def copytree(src, dst):
    # dst is a host-side path, we send one file at a time via host script
    # but for simplicity we'll just print what needs to be copied
    # → you will run mpremote cp manually for each file
    for entry in os.listdir(src):
        s = src + '/' + entry if src != '/' else '/' + entry
        try:
            st = os.stat(s)
            if st[0] & 0o170000 == 0o040000:  # is directory
                print(f"DIR  {s}")
                copytree(s, dst)               # recurse
            else:
                print(f"FILE {s}")
                # → copy this file manually from host:
                # mpremote cp ":{s}" "{dst}/{entry}"
        except OSError:
            pass  # skip broken symlinks / permission issues

copytree('/lib', '')
