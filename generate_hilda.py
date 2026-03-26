#!/usr/bin/env python3
"""Generate walk-hilda-01.mov from a static Westie character image.

Takes the ChatGPT-generated Westie PNG (already has alpha), resizes to 1080x1920,
and creates a walk animation with subtle bounce and sway.
"""

import os
import math
import subprocess
import tempfile
from PIL import Image

WIDTH, HEIGHT = 1080, 1920
FPS = 24  # match Bruce/Jazz
DURATION = 10  # seconds
TOTAL_FRAMES = FPS * DURATION

SRC_IMAGE = "/Users/miairis/Downloads/ChatGPT Image 2026年3月26日 22_45_32.png"


def prepare_character():
    """Load image, clean alpha, resize for animation."""
    print("Loading and processing character image...")
    img = Image.open(SRC_IMAGE).convert('RGBA')
    px = img.load()
    w, h = img.size

    # Clean: zero out RGB for fully/mostly transparent pixels to reduce file size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 10:
                px[x, y] = (0, 0, 0, 0)

    # Crop to bounding box of visible content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Target: character about 70% of 1920 height = 1344px
    target_h = int(HEIGHT * 0.70)
    scale = target_h / img.height
    target_w = int(img.width * scale)
    img = img.resize((target_w, target_h), Image.LANCZOS)

    print(f"Character size: {target_w}x{target_h}")
    return img


def generate_frame(char_img, frame_num):
    """Generate a single animation frame with walk bounce."""
    frame = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))  # black bg like Bruce

    # Walk cycle: one full cycle per second (24 frames at 24fps)
    t = (frame_num % 24) / 24.0

    # Vertical bounce
    bounce_y = int(math.sin(t * 2 * math.pi) * 12)

    # Slight horizontal sway
    sway_x = int(math.sin(t * 2 * math.pi) * 4)

    # Slight tilt for liveliness
    tilt = math.sin(t * 2 * math.pi) * 1.5
    rotated = char_img.rotate(tilt, expand=True, resample=Image.BICUBIC)

    # Center character, lower portion of frame
    x = (WIDTH - rotated.width) // 2 + sway_x
    y = HEIGHT - rotated.height - (HEIGHT // 8) + bounce_y

    frame.paste(rotated, (x, y), rotated)
    return frame


def main():
    char_img = prepare_character()

    outdir = tempfile.mkdtemp(prefix='hilda_frames_')
    print(f"Generating {TOTAL_FRAMES} frames to {outdir}...")

    for i in range(TOTAL_FRAMES):
        frame = generate_frame(char_img, i)
        frame.save(os.path.join(outdir, f'frame_{i:04d}.png'))
        if (i + 1) % 60 == 0:
            print(f"  {i + 1}/{TOTAL_FRAMES} frames")

    print("Encoding to HEVC (matching Bruce/Jazz format)...")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'LilAgents', 'walk-hilda-01.mov')

    cmd = [
        'ffmpeg', '-y',
        '-framerate', '24',
        '-i', os.path.join(outdir, 'frame_%04d.png'),
        '-c:v', 'libx265',
        '-pix_fmt', 'yuv420p',
        '-crf', '23',
        '-tag:v', 'hvc1',
        '-an',
        output_path
    ]

    subprocess.run(cmd, check=True)

    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))
    os.rmdir(outdir)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! {output_path} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
