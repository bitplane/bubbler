#!/bin/sh

# Pipes the default mic port into the bubble counter script, then timestamps it
arecord --format=S32_LE --file-type=raw | ./BubbleCounter.py
