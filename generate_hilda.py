#!/usr/bin/env python3
"""Generate walk-hilda-01.mov from an 8-frame sprite sheet.

Splits the 4x2 sprite sheet into 8 walking frames, cycles through them
at 3 frames per sprite (for smooth 24fps playback), with subtle bounce.
"""

import os
import math
import subprocess
import tempfile
from PIL import Image

WIDTH, HEIGHT = 800, 600
FPS = 24
DURATION = 10
TOTAL_FRAMES = FPS * DURATION

SPRITE_SHEET = "/Users/miairis/Downloads/ChatGPT Image 2026年3月26日 23_06_05.png"
COLS, ROWS = 4, 2  # 8 frames total


def load_sprite_frames():
    """Split sprite sheet into individual walk cycle frames."""
    print("Loading sprite sheet...")
    sheet = Image.open(SPRITE_SHEET).convert('RGBA')
    sw, sh = sheet.size
    fw, fh = sw // COLS, sh // ROWS
    print(f"Sheet: {sw}x{sh}, each frame: {fw}x{fh}")

    frames = []
    for row in range(ROWS):
        for col in range(COLS):
            x0, y0 = col * fw, row * fh
            frame = sheet.crop((x0, y0, x0 + fw, y0 + fh))

            # Clean near-transparent pixels
            px = frame.load()
            for y in range(fh):
                for x in range(fw):
                    if px[x, y][3] < 10:
                        px[x, y] = (0, 0, 0, 0)

            # Crop to visible content
            bbox = frame.getbbox()
            if bbox:
                frame = frame.crop(bbox)
            frames.append(frame)

    # Resize all frames to fill ~90% of the video frame height
    target_h = int(HEIGHT * 0.90)
    resized = []
    for f in frames:
        scale = target_h / f.height
        target_w = int(f.width * scale)
        resized.append(f.resize((target_w, target_h), Image.LANCZOS))

    print(f"Loaded {len(resized)} frames, target size ~{resized[0].width}x{target_h}")
    return resized


def generate_frame(sprite_frames, frame_num):
    """Generate a single video frame by cycling through sprite frames."""
    frame = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))

    # Each sprite frame shows for 3 video frames = 8 sprites per cycle = 1 cycle/sec
    sprite_idx = (frame_num // 3) % len(sprite_frames)
    char_img = sprite_frames[sprite_idx]

    # Subtle vertical bounce synced with walk cycle
    t = (frame_num % 24) / 24.0
    bounce_y = int(math.sin(t * 2 * math.pi * 2) * 5)  # 2 bounces per cycle

    # Center character near bottom of frame
    x = (WIDTH - char_img.width) // 2
    y = HEIGHT - char_img.height - 10 + bounce_y

    frame.paste(char_img, (x, y), char_img)
    return frame


def main():
    sprite_frames = load_sprite_frames()

    outdir = tempfile.mkdtemp(prefix='hilda_frames_')
    print(f"Generating {TOTAL_FRAMES} frames to {outdir}...")

    for i in range(TOTAL_FRAMES):
        frame = generate_frame(sprite_frames, i)
        frame.save(os.path.join(outdir, f'frame_{i:04d}.png'))
        if (i + 1) % 60 == 0:
            print(f"  {i + 1}/{TOTAL_FRAMES} frames")

    print("Encoding to HEVC...")
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
