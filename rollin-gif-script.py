from PIL import Image

import os
import argparse
import sys

# Transparency issue solved by egocarib in included code, found at https://gist.github.com/egocarib/ea022799cca8a102d14c54a22c45efe0.

# This code adapted from https://github.com/python-pillow/Pillow/issues/4644 to resolve an issue
# described in https://github.com/python-pillow/Pillow/issues/4640
#
# There is a known issue with the Pillow library that messes up GIF transparency by replacing the
# transparent pixels with black pixels (among other issues) when the GIF is saved using PIL.Image.save().
# This code works around the issue and allows us to properly generate transparent GIFs.

from typing import Tuple, List, Union
from collections import defaultdict
from random import randrange
from itertools import chain


class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image.Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        """Set the transparent pixels to the color 0."""
        self._transparent_pixels = set(
            idx for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel='A').getdata())
            if alpha <= self._alpha_threshold)

    def _set_parsed_palette(self):
        """Parse the RGB palette color `tuple`s from the palette."""
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = set(
            idx for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels)
        self._img_p_parsedpalette = dict(
            (idx, tuple(palette[idx * 3:idx * 3 + 3]))
            for idx in self._img_p_used_palette_idxs)

    def _get_similar_color_idx(self):
        """Return a palette index with the closest similar color."""
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum((
                abs(old_color[0] - color_item[0]),  # Red
                abs(old_color[1] - color_item[1]),  # Green
                abs(old_color[2] - color_item[2])))  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        """Since the first color is used in the palette, remap it."""
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else \
            self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces['idx_from'].append(0)
        self._palette_replaces['idx_to'].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del(self._img_p_parsedpalette[0])

    def _get_unused_color(self) -> tuple:
        """ Return a color for the palette that does not collide with any other already in the palette."""
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        """Adjust palette to have the zeroth color set as transparent. Basically, get another palette
        index for the zeroth color."""
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        """Convert the pixels into their new values."""
        if self._palette_replaces['idx_from']:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces['idx_from']),
                bytes(self._palette_replaces['idx_to']))
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        """Modify the palette in the new `Image`."""
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256))
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image.Image:
        """Return the processed mode `P` `Image`."""
        self._img_p = self._img_rgba.convert(mode='P')
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info['transparency'] = 0
        self._img_p.info['background'] = 0
        return self._img_p


def create_animated_gif(images: List[Image.Image], durations: Union[int, List[int]]) -> Tuple[Image.Image, dict]:
    """If the image is a GIF, create an its thumbnail here."""
    save_kwargs = dict()
    new_images: List[Image.Image] = []

    for frame in images:
        thumbnail = frame.copy()  # type: Image.Image
        thumbnail_rgba = thumbnail.convert(mode='RGBA')
        thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
        converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
        thumbnail_p = converter.process()  # type: Image.Image
        new_images.append(thumbnail_p)

    output_image = new_images[0]
    save_kwargs.update(
        format='GIF',
        save_all=True,
        optimize=False,
        append_images=new_images[1:],
        duration=durations,
        disposal=2,  # Other disposals don't work
        loop=0)
    return output_image, save_kwargs


def save_transparent_gif(images: List[Image.Image], durations: Union[int, List[int]], save_file):
    """Creates a transparent GIF, adjusting to avoid transparency issues that are present in the PIL library

    Note that this does NOT work for partial alpha. The partial alpha gets discarded and replaced by solid colors.

    Parameters:
        images: a list of PIL Image objects that compose the GIF frames
        durations: an int or List[int] that describes the animation durations for the frames of this GIF
        save_file: A filename (string), pathlib.Path object or file object. (This parameter corresponds
                   and is passed to the PIL.Image.save() method.)
    Returns:
        Image - The PIL Image object (after first saving the image to the specified target)
    """
    root_frame, save_args = create_animated_gif(images, durations)
    root_frame.save(save_file, **save_args)

# The above was written by egocarib https://gist.github.com/egocarib/ea022799cca8a102d14c54a22c45efe0
# The following is original work by Arcanewinds.

def generate_rollin_gif(src_filename, output_filename=None, fps=50, gif_time=2, clockwise=1, size=None, speed='linear', reverse=0, num_rotations=1):
    PROG_RESOLUTION = 10  # resolution of progress indicator
    src_filename, file_ext = src_filename.split('.')
    file_ext = '.'+file_ext
    im = Image.open(src_filename + file_ext)

    num_images = int(gif_time * fps)
    if speed != 'linear':
        num_images = int(num_images/4)

    total_rotation = num_rotations*360
    avg_step = total_rotation/num_images
    min_step = 1
    max_step = avg_step + (avg_step - min_step)
    if speed == 'increasing':
        print('Incrementally increasing rotation angle.')
        deg_step = [(x * ((max_step - min_step) / num_images))+min_step for x in range(num_images-1)]
        deg_step = [x * ((num_rotations*360) / sum(deg_step)) for x in deg_step]
    elif speed == 'decreasing':
        print('Incrementally decreasing rotation angle.')
        deg_step = [(x * ((max_step - min_step) / num_images))+min_step for x in range(num_images-1, -1, -1)]
        deg_step = [x * ((num_rotations * 360) / sum(deg_step)) for x in deg_step]
    elif speed == 'linear':
        print('Linear rotation angle.')
        if reverse:
            deg_step = (num_rotations*360) / num_images
        else:
            deg_step = 360 / num_images
    else:
        raise ValueError(f"Speed \'{speed}\' not recognised.")

    filenames = []
    progress_ids = [int((x / PROG_RESOLUTION) * num_images)-1 for x in list(range(1, PROG_RESOLUTION + 1, 1))]
    progress_percentages = [((x / PROG_RESOLUTION) * 100) for x in list(range(1, PROG_RESOLUTION + 1, 1))]
    if clockwise == 1:
        print('Clockwise rotation.')
        direction = -1
    else:
        print('Anti-clockwise rotation.')
        direction = 1

    created_png = False
    if not file_ext == '.png':
        im = im.convert('RGBA')
        created_png = True
        im.save(src_filename+'.png', format='PNG', optimize=True)
        file_ext = '.png'
        im = Image.open(src_filename + file_ext)
    else:
        im = im.convert('RGBA')
    if size is not None:
        print(f"Resizing {src_filename}.{file_ext} to {size}.")
        im = im.resize(size)
    print('Generating '+str(num_images)+' images.')
    rollin_images = []
    cum_deg_step = 0
    for i in range(num_images):
        #angle = direction * (i * deg_step)
        if speed == 'linear':
            angle = direction * (i * deg_step)
            rotated_im = im.rotate(angle)
        else:
            angle = direction * cum_deg_step  # cum_deg_step
            rotated_im = im.rotate(angle)
            if i < (num_images - 1):
                cum_deg_step += deg_step[i]  # cumulative
        if file_ext == '.png':
            alpha = rotated_im.getchannel('A')  # isolate transparency
            rotated_im = rotated_im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
            mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)  # transparency mask
            rotated_im.paste(255, mask)  # add transparency
            rotated_im.info['transparency'] = 255  # encode transparency value
        rollin_images.append(rotated_im)
        # this_filename = src_filename+f'_{i}'+file_ext
        # rotated_im.save(this_filename, optimize=False)
        # filenames.append(this_filename)
        if i in progress_ids:
            print(f'Generating images: {progress_percentages[progress_ids.index(i)]}% complete.')

    if output_filename is None:
        output_filename = src_filename+'.gif'
    else:
        if '.gif' not in output_filename:
            if '.' in output_filename:
                output_filename = output_filename.split('.')[0] + '.gif'
            else:
                output_filename += '.gif'

    avg_dur = (gif_time*1000) / num_images
    min_dur = 20  # 20 milliseconds = highest fps (50) supported by browsers
    max_dur = avg_dur + (avg_dur - min_dur)
    if speed == 'increasing':
        print('Incrementally increasing rotation velocity.')
        durations = [int((x * ((max_dur - min_dur) / num_images)) + min_dur) for x in range(num_images, -1, -1)]
    elif speed == 'decreasing':
        print('Incrementally decreasing rotation velocity.')
        durations = [int((x * ((max_dur - min_dur) / num_images)) + min_dur) for x in range(num_images)]
    else:
        print('Linear rotation velocity.')
        durations = max([int((gif_time/num_images)*1000), 20])
    if reverse == 1:
        print('Adding reverse order images.')
        for i in range(num_images - 1, -1, -1):
            rollin_images.append(rollin_images[i])
            if isinstance(durations, list):
                durations.append(durations[i])
    print('Converting images to .gif')
    save_transparent_gif(rollin_images, durations, output_filename)

    try:
        from pygifsicle import optimize
        print('Optimizing .gif')
        optimize(src_filename+'.gif')
    except ImportError:
        print('For file-size optimized .gifs, install pygifsicle.')

    if created_png:
        os.remove(src_filename+'.png')
    print('Rollin .gif generated: '+output_filename)

    return src_filename+'.gif'


def img_size(s):
    try:
        width, height = map(int, s.split(','))
        return width, height
    except:
        raise argparse.ArgumentTypeError("Image size must be width,height")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="rollin-gif-script",
        description='Generates a rollin\' gif from a provided image.'
    )
    parser.add_argument(
        'filename',
        type=str,
        help='Enter the filename of an image to make a rollin\' .gif'
    )
    parser.add_argument(
        '--size',
        default=None,
        type=img_size,
        help='''Output image size width,height.'''
    )
    parser.add_argument(
        '--fps',
        default=50,
        type=float,
        help='''Frames per second of the .gif (affects file-size)
                 Note: Maximum frames-per-second for browser-compatibility is 50.'''
    )
    parser.add_argument(
        '--duration', '--dur',
        default=1.2,
        type=float,
        help='''Duration of the .gif in seconds. Default=1.2.
             Note: Minimum duration is limited by a maximum frames-per-second of 50.'''
    )
    parser.add_argument(
        '--clockwise', '--direction',
        default=1,
        type=int,
        help='''Set to 1 for clockwise, or any other integer for anti-clockwise.'''
    )
    parser.add_argument(
        '--speed',
        default='linear',
        type=str,
        help='''Type of speed to use: \'linear\', \'increasing\', \'decreasing\'.'''
    )
    parser.add_argument(
        '--reverse',
        default=0,
        type=int,
        help='''Reverse at end of rotations, 0=False, 1=True'''
    )
    parser.add_argument(
        '--num_rotations',
        default=1.,
        type=float,
        help='''Number of 360 degree image rotations (float).'''
    )
    parser.add_argument(
        '--output',
        default=None,
        type=str,
        help='''Output filename.'''
    )
    args = parser.parse_args()
    if args.filename is None:
        print('Please enter the filename of an image to make a rollin gif.')
        print('Usage: python rollin-gif-script.py [filename] --deg [degrees(int)] --dur [duration(float)]')
        print('Use python rollin-gif-script.py -h for more information')
    else:
        generate_rollin_gif(args.filename,
                            output_filename=args.output,
                            fps=args.fps,
                            gif_time=args.duration,
                            clockwise=args.clockwise,
                            speed=args.speed,
                            reverse=args.reverse,
                            num_rotations=args.num_rotations,
                            size=args.size)
