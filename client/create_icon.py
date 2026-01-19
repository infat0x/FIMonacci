#!/usr/bin/env python3
"""Convert logo image to Windows .ico format or generate default icon"""

import sys
try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw

from pathlib import Path


def generate_default_icon(size=256):
    """Generate a default FIMonacci icon with geometric F design"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors matching Pearl Aqua theme
    bg_color = (26, 26, 46, 255)       # Dark blue background
    accent_color = (117, 221, 221, 255)  # Pearl aqua
    gold_color = (180, 160, 120, 255)    # Gold accent
    
    # Draw rounded rectangle background
    margin = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 6,
        fill=bg_color
    )
    
    # Draw geometric "F" shape with connected nodes
    # Scale factor
    s = size / 256
    
    # Node positions for "F" shape
    nodes = [
        (80*s, 50*s),   # Top left
        (180*s, 50*s),  # Top right
        (80*s, 120*s),  # Middle left
        (150*s, 120*s), # Middle right
        (80*s, 200*s),  # Bottom
    ]
    
    # Draw lines connecting nodes (main F)
    lines = [(0, 1), (0, 2), (2, 3), (2, 4)]
    for i, j in lines:
        draw.line([nodes[i], nodes[j]], fill=accent_color, width=int(3*s))
    
    # Draw inner connections (web pattern)
    for i, node1 in enumerate(nodes):
        for j, node2 in enumerate(nodes):
            if i < j:
                draw.line([node1, node2], fill=(*accent_color[:3], 80), width=int(1*s))
    
    # Draw gold accent (small i)
    gold_nodes = [
        (160*s, 140*s),
        (190*s, 140*s),
        (175*s, 180*s),
    ]
    for i, node1 in enumerate(gold_nodes):
        for j, node2 in enumerate(gold_nodes):
            if i < j:
                draw.line([node1, node2], fill=gold_color, width=int(2*s))
    
    # Draw nodes (dots)
    node_radius = int(8 * s)
    for node in nodes:
        x, y = node
        draw.ellipse(
            [x - node_radius, y - node_radius, x + node_radius, y + node_radius],
            fill=accent_color
        )
    
    # Draw gold nodes
    small_radius = int(5 * s)
    for node in gold_nodes:
        x, y = node
        draw.ellipse(
            [x - small_radius, y - small_radius, x + small_radius, y + small_radius],
            fill=gold_color
        )
    
    return img


def create_icon_from_image(logo_path, ico_path):
    """Convert an image file to .ico format"""
    print(f"  Converting {logo_path.name} to icon.ico...")
    
    img = Image.open(logo_path)
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")
    
    # Let Pillow generate a multi-size ICO directly
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    # Force BMP frames (no PNG compression) for better tooling compatibility
    img.save(ico_path, format="ICO", sizes=sizes, bitmap_format="bmp")
    
    print(f"  [OK] Created {ico_path}")
    return True


def create_icon():
    """Create icon.ico from logo image or generate default"""
    script_dir = Path(__file__).parent
    ico_path = script_dir / "icon.ico"
    
    # Look for logo image
    logo_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
    logo_path = None
    
    for ext in logo_extensions:
        candidate = script_dir / f"logo{ext}"
        if candidate.exists():
            logo_path = candidate
            break
    
    if logo_path:
        return create_icon_from_image(logo_path, ico_path)
    else:
        print("  No logo image found. Generating default icon...")
        
        # Generate icon at multiple sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []
        
        for size in sizes:
            img = generate_default_icon(size[0])
            icons.append(img)
        
        icons[0].save(
            ico_path,
            format='ICO',
            sizes=sizes,
            append_images=icons[1:]
        )
        
        print(f"  [OK] Generated default icon.ico")
        return True


if __name__ == "__main__":
    create_icon()

