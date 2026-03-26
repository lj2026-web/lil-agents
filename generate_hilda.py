#!/usr/bin/env python3
"""Generate walk-hilda-01.mov — pixel art West Highland White Terrier walk cycle.

Output: 1080x1920, 30fps, 10s loop, transparent background (ProRes 4444).
The dog is small (matching Bruce/Jazz scale ~60-80px at display size),
positioned in the lower-center of the frame.
"""

import os
import struct
import subprocess
import tempfile
from PIL import Image, ImageDraw

WIDTH, HEIGHT = 1080, 1920
FPS = 30
DURATION = 10  # seconds
TOTAL_FRAMES = FPS * DURATION

# Pixel art scale: each "pixel" is this many actual pixels
# At 1080x1920 displayed at 200px height, scale factor ~9.6
# So a 7-pixel-tall dog becomes ~67px displayed — good match
PX = 10

# Colors
WHITE_BODY = (230, 224, 217, 255)       # warm white fur
WHITE_LIGHT = (240, 236, 230, 255)      # highlights
WHITE_SHADOW = (200, 194, 187, 255)     # shadow/depth
NOSE = (40, 40, 40, 255)                # black nose
EYE = (30, 30, 30, 255)                 # dark eyes
TONGUE = (220, 120, 130, 255)           # pink tongue (subtle)
TRANSPARENT = (0, 0, 0, 0)

# Dog is drawn on a small grid, then scaled up by PX
# Grid size: roughly 12w x 10h pixels for the dog body
# The dog faces RIGHT by default

def draw_pixel(draw, gx, gy, color, ox, oy):
    """Draw a single pixel-art pixel at grid position (gx, gy) with offset (ox, oy)."""
    x = ox + gx * PX
    y = oy + gy * PX
    draw.rectangle([x, y, x + PX - 1, y + PX - 1], fill=color)

def draw_westie(draw, frame_phase, ox, oy):
    """Draw a Westie in pixel art. frame_phase 0-7 for walk cycle."""
    p = lambda gx, gy, color: draw_pixel(draw, gx, gy, color, ox, oy)

    # === HEAD (rows 0-3, cols 3-9) ===
    # Ears
    p(3, 0, WHITE_BODY)
    p(4, 0, WHITE_BODY)
    p(8, 0, WHITE_BODY)
    p(9, 0, WHITE_BODY)

    # Head top fur
    for x in range(3, 10):
        p(x, 1, WHITE_BODY)
    p(2, 1, WHITE_LIGHT)  # fluffy left edge

    # Head middle - eyes row
    p(2, 2, WHITE_BODY)
    p(3, 2, WHITE_BODY)
    p(4, 2, WHITE_BODY)
    p(5, 2, EYE)           # left eye
    p(6, 2, WHITE_BODY)
    p(7, 2, WHITE_BODY)
    p(8, 2, EYE)           # right eye
    p(9, 2, WHITE_BODY)
    p(10, 2, WHITE_BODY)

    # Head bottom - nose/mouth
    p(2, 3, WHITE_BODY)
    p(3, 3, WHITE_BODY)
    p(4, 3, WHITE_BODY)
    p(5, 3, WHITE_BODY)
    p(6, 3, WHITE_SHADOW)
    p(7, 3, NOSE)          # nose
    p(8, 3, WHITE_BODY)
    p(9, 3, WHITE_BODY)
    p(10, 3, WHITE_BODY)

    # Chin/beard fur
    p(4, 4, WHITE_LIGHT)
    p(5, 4, WHITE_LIGHT)
    p(6, 4, WHITE_LIGHT)
    p(7, 4, WHITE_LIGHT)
    p(8, 4, WHITE_LIGHT)

    # === BODY (rows 3-7, cols 0-8) ===
    # Neck connection
    p(3, 4, WHITE_BODY)
    p(2, 4, WHITE_BODY)

    # Body top
    for x in range(0, 6):
        p(x, 5, WHITE_BODY)
    p(6, 5, WHITE_SHADOW)  # body contour

    # Body middle
    p(0, 6, WHITE_SHADOW)
    for x in range(1, 6):
        p(x, 6, WHITE_BODY)
    p(6, 6, WHITE_SHADOW)

    # Body bottom / belly
    p(0, 7, WHITE_SHADOW)
    for x in range(1, 6):
        p(x, 7, WHITE_LIGHT)

    # === TAIL (rows 3-5, cols -2 to 0) ===
    # Tail goes up and slightly back, wagging based on frame
    tail_wag = frame_phase % 4
    if tail_wag == 0:
        p(-1, 4, WHITE_BODY)
        p(-1, 3, WHITE_BODY)
        p(-1, 2, WHITE_LIGHT)
    elif tail_wag == 1:
        p(-1, 4, WHITE_BODY)
        p(-2, 3, WHITE_BODY)
        p(-2, 2, WHITE_LIGHT)
    elif tail_wag == 2:
        p(-1, 4, WHITE_BODY)
        p(-1, 3, WHITE_BODY)
        p(0, 2, WHITE_LIGHT)
    else:
        p(-1, 4, WHITE_BODY)
        p(-2, 3, WHITE_BODY)
        p(-1, 2, WHITE_LIGHT)

    # === LEGS (rows 8-9) ===
    # 4 legs with walk cycle animation
    # phase 0-7 maps to different leg positions
    phase = frame_phase % 8

    # Front legs (cols 4-5), Back legs (cols 1-2)
    # Each pair alternates: when front-left is forward, back-right is forward

    if phase in (0, 1):
        # Front-right forward, back-left forward
        p(5, 8, WHITE_SHADOW); p(6, 8, WHITE_SHADOW)   # front-right forward
        p(4, 8, WHITE_SHADOW); p(4, 9, WHITE_SHADOW)   # front-left down
        p(0, 8, WHITE_SHADOW); p(-1, 8, WHITE_SHADOW)  # back-left forward
        p(1, 8, WHITE_SHADOW); p(1, 9, WHITE_SHADOW)   # back-right down
    elif phase in (2, 3):
        # All legs mid-stride
        p(5, 8, WHITE_SHADOW); p(5, 9, WHITE_SHADOW)   # front-right down
        p(4, 8, WHITE_SHADOW); p(4, 9, WHITE_SHADOW)   # front-left down
        p(1, 8, WHITE_SHADOW); p(1, 9, WHITE_SHADOW)   # back-right down
        p(0, 8, WHITE_SHADOW); p(0, 9, WHITE_SHADOW)   # back-left down
    elif phase in (4, 5):
        # Front-left forward, back-right forward
        p(4, 8, WHITE_SHADOW); p(3, 8, WHITE_SHADOW)   # front-left forward
        p(5, 8, WHITE_SHADOW); p(5, 9, WHITE_SHADOW)   # front-right down
        p(1, 8, WHITE_SHADOW); p(2, 8, WHITE_SHADOW)   # back-right forward
        p(0, 8, WHITE_SHADOW); p(0, 9, WHITE_SHADOW)   # back-left down
    else:  # 6, 7
        # All legs mid-stride (return)
        p(5, 8, WHITE_SHADOW); p(5, 9, WHITE_SHADOW)
        p(4, 8, WHITE_SHADOW); p(4, 9, WHITE_SHADOW)
        p(1, 8, WHITE_SHADOW); p(1, 9, WHITE_SHADOW)
        p(0, 8, WHITE_SHADOW); p(0, 9, WHITE_SHADOW)

    # Tongue out on some frames (cute detail)
    if frame_phase % 16 < 8:
        p(10, 3, TONGUE)


def generate_frame(frame_num):
    """Generate a single frame as RGBA Image."""
    img = Image.new('RGBA', (WIDTH, HEIGHT), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Walk cycle: 8 phases per cycle, cycle at ~2 steps/sec for a trotting dog
    # At 30fps, change phase every ~4 frames for a brisk trot
    phase = (frame_num // 4) % 8

    # Dog position: centered horizontally, near bottom of frame
    # The character sits in the lower portion — matching Bruce/Jazz positioning
    dog_grid_w = 13  # grid cells wide
    dog_grid_h = 10  # grid cells tall

    # Center horizontally
    ox = (WIDTH - dog_grid_w * PX) // 2
    # Position vertically — bottom third of frame, leaving room below for dock alignment
    oy = HEIGHT - dog_grid_h * PX - (HEIGHT // 6)

    # Slight vertical bounce during walk
    bounce = 0
    if phase in (1, 2, 5, 6):
        bounce = -PX // 2  # slight up

    draw_westie(draw, phase, ox, oy + bounce)
    return img


def main():
    outdir = tempfile.mkdtemp(prefix='hilda_frames_')
    print(f"Generating {TOTAL_FRAMES} frames to {outdir}...")

    for i in range(TOTAL_FRAMES):
        img = generate_frame(i)
        img.save(os.path.join(outdir, f'frame_{i:04d}.png'))
        if (i + 1) % 60 == 0:
            print(f"  {i + 1}/{TOTAL_FRAMES} frames")

    print("Encoding to ProRes 4444 with alpha...")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'LilAgents', 'walk-hilda-01.mov')

    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(FPS),
        '-i', os.path.join(outdir, 'frame_%04d.png'),
        '-c:v', 'prores_ks',
        '-profile:v', '4444',
        '-pix_fmt', 'yuva444p10le',
        '-an',
        output_path
    ]

    subprocess.run(cmd, check=True)

    # Cleanup frames
    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))
    os.rmdir(outdir)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! {output_path} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
