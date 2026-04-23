#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy python3-spidev python3-rpi.gpio
pip3 install --user waveshare-epaper

echo "Enable SPI with: sudo raspi-config"
