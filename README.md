# rollin_gif
Generates a rotating gif from an image.

Requires Pillow to be installed before running: https://pillow.readthedocs.io/en/stable/installation.html

usage: rollin-gif-script [-h] [--size SIZE] [--fps FPS] [--duration DURATION]
                         [--clockwise CLOCKWISE] [--output OUTPUT]
                         filename

positional arguments:

filename : Enter the filename of an image to make a rollin' .gif

optional arguments:

-h, --help show this help message and exit

--size : Output image size width,height.

--fps : Frames per second of the .gif (affects file-size) Note: Maximum frames-per-second for browser-compatibility is 50.

--duration --dur : Duration of the .gif in seconds. Default=1.2. Note: Minimum duration is limited by a maximum frames-per-second of 50.

--clockwise, --direction : Set to 1 for clockwise, or any other integer for anti-clockwise.

--output : Output filename.
