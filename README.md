# rollin_gif
Generates a rotating gif from an image.

### Requirements

Requires Pillow to be installed before running: https://pillow.readthedocs.io/en/stable/installation.html

### Usage
``` usage: rollin-gif-script [-h] filename [--size SIZE] [--fps FPS] [--duration DURATION] [--clockwise CLOCKWISE] [--output OUTPUT] ```

#### positional arguments:

*filename* : Enter the filename of an image to make a rollin' .gif

#### optional arguments:

*-h*, *--help* :  show this help message and exit

*--size* :    Output image size width,height.

*--fps* :     Frames per second of the .gif (affects file-size) Note: Maximum frames-per-second for browser-compatibility is 50. (Default=50)

*--duration*, *--dur* :   Duration of the .gif in seconds. (Default=1.2)

*--clockwise*, *--direction* :    Set to 1 for clockwise, or any other integer for anti-clockwise (Default=1)

*--output* :    Output filename.
