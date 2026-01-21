#!/bin/bash
sudo chmod 666 /dev/ttyACM0 && \
mpremote connect dev/ttyACM0 fs cp ./code.py :/code.py