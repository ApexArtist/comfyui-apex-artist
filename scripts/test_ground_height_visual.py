#!/usr/bin/env python3
"""Visual diagnostic for ground height behavior."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math

# Import the actual implementation
from apex_hdri_viewer import equirect_to_camera_view, DEFAULT_CAPTURE_HEIGHT

def create_test_panorama(width=512, height=256):
    """Create a test panorama with grid lines to visualize distortion.

    Red horizontal lines every 15 degrees latitude.
    Blue vertical lines every 15 degrees longitude.
    Green line at the horizon (equator).
    """
    img = Image.new('RGB', (width, height), (40, 40, 50))
    draw = ImageDraw.Draw(img)

    # Draw latitude lines (horizontal)
    for lat_deg in range(-75, 90, 15):
        lat_rad = math.radians(lat_deg)
        # Equirectangular: v = 0.5 - lat/(pi), v in [0,1]
        v = 0.5 - lat_rad / math.pi
        y = int(v * (height - 1))
        color = (0, 255, 0) if lat_deg == 0 else (255, 100, 100)  # green for horizon
        width_line = 3 if lat_deg == 0 else 1
        draw.line([(0, y), (width, y)], fill=color, width=width_line)

    # Draw longitude lines (vertical)
    for lon_deg in range(-180, 180, 15):
        lon_rad = math.radians(lon_deg)
        # Equirectangular: u = 0.5 + lon/(2*pi), u in [0,1]
        u = 0.5 + lon_rad / (2 * math.pi)
        x = int(u * width) % width
        draw.line([(x, 0), (x, height)], fill=(100, 100, 255), width=1)

    # Add degree markers at horizon
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()

    horizon_y = height // 2
    for lon_deg in range(-180, 180, 30):
        u = 0.5 + math.radians(lon_deg) / (2 * math.pi)
        x = int(u * width) % width
        draw.text((x, horizon_y - 15), f"{lon_deg}°", fill=(255, 255, 255), font=font)

    # Convert to tensor
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)  # [1, H, W, 3]

def render_comparison(pano, camera_height, capture_height=DEFAULT_CAPTURE_HEIGHT,
                     ground_range=25.0, output_name="test"):
    """Render a view with the given parameters."""
    result = equirect_to_camera_view(
        pano,
        yaw_deg=0.0,
        pitch_deg=0.0,  # Look straight ahead at horizon
        roll_deg=0.0,
        fov_deg=90.0,
        out_w=512,
        out_h=512,
        lens_type="rectilinear",
        camera_height=camera_height,
        capture_height=capture_height,
        ground_range=ground_range
    )

    # Convert back to image
    img_array = (result[0].cpu().numpy() * 255).astype(np.uint8)
    img = Image.fromarray(img_array)

    # Add label
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    label = f"Cam: {camera_height}m | Cap: {capture_height}m | Range: {ground_range}m"
    draw.text((10, 10), label, fill=(255, 255, 0), font=font)

    img.save(f"{output_name}.png")
    print(f"Saved {output_name}.png")
    return img

def main():
    print("Creating test panorama with grid...")
    pano = create_test_panorama()

    print("\nRendering comparison views...")
    print("=" * 60)

    # Test 1: Identity (camera == capture height)
    print("\n1. Identity test (camera height = capture height)")
    render_comparison(pano, 1.6, 1.6, 25.0, "ground_test_1_identity")

    # Test 2: Camera lower than capture (ground should move UP)
    print("\n2. Lower camera (0.8m vs 1.6m capture)")
    render_comparison(pano, 0.8, 1.6, 25.0, "ground_test_2_lower")

    # Test 3: Camera higher than capture (ground should move DOWN)
    print("\n3. Higher camera (3.2m vs 1.6m capture)")
    render_comparison(pano, 3.2, 1.6, 25.0, "ground_test_3_higher")

    # Test 4: Very low camera (extreme case)
    print("\n4. Very low camera (0.2m vs 1.6m capture)")
    render_comparison(pano, 0.2, 1.6, 25.0, "ground_test_4_very_low")

    # Test 5: No fade (ground_range = 0)
    print("\n5. No fade - pure plane projection")
    render_comparison(pano, 0.8, 1.6, 0.0, "ground_test_5_no_fade")

    # Test 6: Large fade range
    print("\n6. Large fade range (100m)")
    render_comparison(pano, 0.8, 1.6, 100.0, "ground_test_6_large_fade")

    print("\n" + "=" * 60)
    print("Visual tests complete!")
    print("Check the generated PNG files to inspect ground behavior.")
    print("\nWhat to look for:")
    print("- Green line = horizon (should stay near center)")
    print("- Red lines = latitude markers (ground should shift)")
    print("- Blue lines = straight lines should stay straight")
    print("- Ground grid should show proper perspective distortion")

if __name__ == "__main__":
    main()
