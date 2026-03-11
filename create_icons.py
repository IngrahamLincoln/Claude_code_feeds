#!/usr/bin/env python3
"""
Generates PNG icon files for the AI Reader PWA.
Uses only Python standard library — no Pillow required.
Produces: icon-192.png, icon-512.png, apple-touch-icon.png
"""
import struct
import zlib
import math

# Indigo accent: #6366f1  background: #0d0d14
BG = (13, 13, 20)        # #0d0d14
ACCENT = (99, 102, 241)  # #6366f1
WHITE = (255, 255, 255)

def write_png(filename, pixels, width, height):
    """Write an RGBA pixel array as a PNG file."""
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    # Flatten RGBA pixel rows with filter byte 0 prepended
    raw = b''
    for y in range(height):
        row = b'\x00'
        for x in range(width):
            r, g, b, a = pixels[y][x]
            row += bytes([r, g, b, a])
        raw += row

    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(raw, 6))
    iend = chunk(b'IEND', b'')

    with open(filename, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend)
    print(f'  Created {filename} ({width}x{height})')

def make_icon(size):
    """Draw a rounded-square icon with an 'AI' logotype."""
    pixels = [[(0, 0, 0, 0)] * size for _ in range(size)]
    cx = size / 2
    radius = size / 2  # outer circle radius
    corner = size * 0.22  # rounded corner radius for the squircle

    def in_rounded_rect(x, y, r):
        """True if (x,y) is inside a rounded square with corner radius r."""
        inner = size / 2 - r
        dx = abs(x - cx) - inner
        dy = abs(y - cx) - inner
        if dx <= 0 and dy <= 0:
            return True
        if dx > r or dy > r:
            return False
        return math.sqrt(max(dx, 0) ** 2 + max(dy, 0) ** 2) <= r

    def lerp_color(c1, c2, t):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    # Gradient: top-left lighter indigo → bottom-right darker
    light = (120, 124, 245)
    dark  = (75,  78, 210)

    for y in range(size):
        for x in range(size):
            if not in_rounded_rect(x + 0.5, y + 0.5, corner):
                continue
            # Gradient
            t = (x + y) / (size * 2)
            bg = lerp_color(light, dark, t)
            pixels[y][x] = (bg[0], bg[1], bg[2], 255)

    # Draw "AI" text using a simple pixel-font approach
    # Each character is defined as a 5x7 bitmap (columns)
    FONT = {
        'A': [
            [0,1,1,1,0],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,0,0,0,1],
        ],
        'I': [
            [1,1,1,1,1],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [1,1,1,1,1],
        ],
    }

    char_w = 5
    char_h = 7
    gap = max(2, size // 32)
    scale = max(1, size // 40)

    total_w = (char_w * 2 + gap) * scale
    total_h = char_h * scale

    start_x = int(cx - total_w / 2)
    start_y = int(cx - total_h / 2)

    def draw_char(char, ox, oy):
        bitmap = FONT[char]
        for row_i, row in enumerate(bitmap):
            for col_i, bit in enumerate(row):
                if bit:
                    for sy in range(scale):
                        for sx in range(scale):
                            py = oy + row_i * scale + sy
                            px = ox + col_i * scale + sx
                            if 0 <= px < size and 0 <= py < size:
                                pixels[py][px] = (WHITE[0], WHITE[1], WHITE[2], 255)

    draw_char('A', start_x, start_y)
    draw_char('I', start_x + (char_w + gap) * scale, start_y)

    return pixels

if __name__ == '__main__':
    print('Generating icons…')
    for size, name in [(192, 'icon-192.png'), (512, 'icon-512.png'), (180, 'apple-touch-icon.png')]:
        px = make_icon(size)
        write_png(name, px, size, size)
    print('Done.')
