#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A color scheme generator.
Takes an image (local or online) and grabs the most dominant colors
using kmeans.
Also creates bold colors by adding value to the dominant colors.
Finally, outputs the colors to stdout
(one normal and one bold per line, space delimited) and
generates an HTML preview of the color scheme.
"""

"""
The MIT License (MIT)

Copyright (c) 2015 Ethan Chan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import webbrowser
from sys import exit
from io import BytesIO
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser
from PIL import Image
from numpy import array
from scipy.cluster.vq import kmeans
from colorsys import rgb_to_hsv, hsv_to_rgb

# Python3 compatibility
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

DEFAULT_NUM_COLORS = 6
DEFAULT_MINV = 170
DEFAULT_MAXV = 200
DEFAULT_BOLD_ADD = 50
DEFAULT_FONT_SIZE = 1
DEFAULT_BG_COLOR = '#272727'

THUMB_SIZE = (200, 200)
SCALE = 256.0


def down_scale(x):
    return x / SCALE


def up_scale(x):
    return int(x * SCALE)


def hexify(rgb):
    return '#%s' % ''.join('%02x' % p for p in rgb)


def get_colors(img):
    """
    Returns a list of all the image's colors.
    """
    w, h = img.size
    return [color[:3] for count, color in img.convert('RGB').getcolors(w * h)]


def clamp(color, min_v, max_v):
    """
    Clamps a color such that the value is between min_v and max_v.
    """
    h, s, v = rgb_to_hsv(*map(down_scale, color))
    min_v, max_v = map(down_scale, (min_v, max_v))
    v = min(max(min_v, v), max_v)
    return tuple(map(up_scale, hsv_to_rgb(h, s, v)))


def order_by_hue(colors):
    """
    Orders colors by hue.
    """
    hsvs = [rgb_to_hsv(*map(down_scale, color)) for color in colors]
    hsvs.sort(key=lambda t: -t[0])
    return [tuple(map(up_scale, hsv_to_rgb(*hsv))) for hsv in hsvs]


def brighten(color, brightness):
    """
    Adds or subtracts value to a color.
    """
    h, s, v = rgb_to_hsv(*map(down_scale, color))
    return tuple(map(up_scale, hsv_to_rgb(h, s, v + down_scale(brightness))))


def colorz(fd, n=DEFAULT_NUM_COLORS, min_v=DEFAULT_MINV, max_v=DEFAULT_MAXV,
           bold_add=DEFAULT_BOLD_ADD, order_colors=True):
    """
    Get the n most dominant colors of an image.
    Clamps value to between min_v and max_v.
    Creates bold colors using bold_add.
    Total number of colors returned is 2*n, optionally ordered by hue.
    Returns as a list of pairs of RGB triples.
    For terminal colors, the hue order is:
    red, yellow, green, cyan, blue, magenta
    """
    img = Image.open(fd)
    img.thumbnail(THUMB_SIZE)

    obs = get_colors(img)
    clamped = [clamp(color, min_v, max_v) for color in obs]
    clusters, _ = kmeans(array(clamped).astype(float), n)
    colors = order_by_hue(clusters) if order_colors else clusters
    return list(zip(colors, [brighten(c, bold_add) for c in colors]))


def open_malloc_img(url):
    """
    Slurp url image into memory.
    """
    try:
        img_fd = BytesIO(urlopen(args.image).read())
    except ValueError:
        print("%s was not a valid URL." % args.image)
        return None
