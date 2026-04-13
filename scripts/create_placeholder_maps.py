#!/usr/bin/env python3
"""
Create placeholder map images for development.
Uses Pillow when available for better quality (grid lines + labels).
Falls back to pure-Python minimal PNG generation if Pillow is absent.
"""
import json
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# Pure-Python PNG helpers (no external deps)
# ---------------------------------------------------------------------------

def _png_chunk(chunk_type, data):
    c = chunk_type + data
    crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    return struct.pack('>I', len(data)) + c + crc


def create_png(width, height, r, g, b):
    """Create a minimal solid-color PNG file in memory."""
    header = b'\x89PNG\r\n\x1a\n'
    ihdr = _png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    row = bytes([0]) + bytes([r, g, b]) * width
    raw = row * height
    idat = _png_chunk(b'IDAT', zlib.compress(raw))
    iend = _png_chunk(b'IEND', b'')
    return header + ihdr + idat + iend


# ---------------------------------------------------------------------------
# Pillow-based helpers (richer placeholders with grid + labels)
# ---------------------------------------------------------------------------

# Common TrueType font search paths (Linux, macOS, Windows)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]


def _find_font(size: int):
    """Return a Pillow font of the requested size, falling back to the built-in default."""
    try:
        from PIL import ImageFont  # type: ignore
        for path in _FONT_CANDIDATES:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
    except Exception:
        return None

def _try_pillow_full(width_cells, height_cells, grid_px_target, r, g, b, name):
    """Generate a grid-lined placeholder PNG using Pillow. Returns bytes or None."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        import io

        cell = grid_px_target
        w = width_cells * cell
        h = height_cells * cell

        img = Image.new('RGB', (w, h), (r, g, b))
        draw = ImageDraw.Draw(img)

        # Subtle cell fill variation (checkerboard-ish)
        for cy in range(height_cells):
            for cx in range(width_cells):
                if (cx + cy) % 2 == 1:
                    x0, y0 = cx * cell, cy * cell
                    draw.rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1],
                                   fill=(min(r + 6, 255), min(g + 6, 255), min(b + 6, 255)))

        # Grid lines
        grid_color = (min(r + 30, 255), min(g + 30, 255), min(b + 30, 255))
        for cx in range(width_cells + 1):
            x = cx * cell
            draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
        for cy in range(height_cells + 1):
            y = cy * cell
            draw.line([(0, y), (w, y)], fill=grid_color, width=1)

        # Map name label
        label_color = (min(r + 120, 255), min(g + 100, 255), min(b + 60, 255))
        font = _find_font(max(10, cell * 2))
        draw.text((w // 2, h // 2), name, fill=label_color, anchor='mm', font=font)

        buf = io.BytesIO()
        img.save(buf, 'PNG', optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def _try_pillow_thumb(width, height, r, g, b, name):
    """Generate a thumbnail PNG using Pillow. Returns bytes or None."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        import io

        img = Image.new('RGB', (width, height), (r, g, b))
        draw = ImageDraw.Draw(img)

        # Simple grid lines
        step_x = width // 6
        step_y = height // 5
        grid_color = (min(r + 25, 255), min(g + 25, 255), min(b + 25, 255))
        for x in range(0, width, step_x):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, step_y):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Label
        label_color = (min(r + 100, 255), min(g + 85, 255), min(b + 50, 255))
        font = _find_font(11)
        draw.text((width // 2, height // 2), name, fill=label_color, anchor='mm', font=font)

        buf = io.BytesIO()
        img.save(buf, 'PNG', optimize=True)
        return buf.getvalue()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'client', 'static')
    thumbs_dir = os.path.join(base_dir, 'maps', 'thumbs')
    full_dir = os.path.join(base_dir, 'maps', 'full')
    os.makedirs(thumbs_dir, exist_ok=True)
    os.makedirs(full_dir, exist_ok=True)

    maps_json = os.path.join(base_dir, 'data', 'maps.json')
    with open(maps_json) as f:
        maps = json.load(f)

    colors = {
        'cave': (30, 20, 40),
        'volcanic': (50, 20, 15),
        'crystal': (20, 30, 50),
        'flooded': (15, 25, 45),
        'underground': (25, 20, 30),
        'castle': (40, 35, 30),
        'fortress': (45, 40, 35),
        'forest': (20, 40, 20),
        'swamp': (25, 35, 20),
        'crypt': (25, 20, 35),
        'dungeon': (30, 25, 35),
        'temple': (35, 25, 40),
        'urban': (40, 35, 40),
        'coastal': (20, 35, 50),
        'mountain': (35, 35, 40),
        'desert': (50, 40, 25),
        'ruins': (35, 30, 25),
        'magical': (30, 20, 50),
        'arctic': (40, 50, 55),
    }
    default_color = (35, 35, 45)

    # Shared placeholder thumbnail (for missing/unknown maps)
    placeholder_data = (_try_pillow_thumb(300, 220, *default_color, '?')
                        or create_png(300, 220, *default_color))
    placeholder_path = os.path.join(thumbs_dir, 'placeholder.webp')
    with open(placeholder_path, 'wb') as f:
        f.write(placeholder_data)

    count = 0
    for m in maps:
        terrain = m['terrain'][0] if m['terrain'] else 'default'
        r, g, b = colors.get(terrain, default_color)
        name = m.get('name', m['id'])
        width_cells = m['width_cells']
        height_cells = m['height_cells']

        # --- Thumbnail (300×220) ---
        thumb_data = (_try_pillow_thumb(300, 220, r, g, b, name)
                      or create_png(300, 220, r, g, b))
        thumb_full_path = os.path.join(base_dir, '..', m['thumb'].lstrip('/'))
        os.makedirs(os.path.dirname(thumb_full_path), exist_ok=True)
        with open(thumb_full_path, 'wb') as f:
            f.write(thumb_data)

        # --- Full-res placeholder ---
        # Target 20 px per cell so the map is visible on the tabletop,
        # capped to keep file sizes reasonable (≤ 1024 px on longest side).
        cell_px = 20
        fw = width_cells * cell_px
        fh = height_cells * cell_px
        max_side = 1024
        if max(fw, fh) > max_side:
            scale = max_side / max(fw, fh)
            cell_px = max(4, int(cell_px * scale))
            fw = width_cells * cell_px
            fh = height_cells * cell_px

        full_data = (_try_pillow_full(width_cells, height_cells, cell_px,
                                      min(r + 10, 255), min(g + 10, 255), min(b + 10, 255),
                                      name)
                     or create_png(fw, fh,
                                   min(r + 10, 255), min(g + 10, 255), min(b + 10, 255)))
        full_path = os.path.join(base_dir, '..', m['src'].lstrip('/'))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(full_data)

        count += 1

    print(f'Created {count} placeholder maps + shared placeholder thumbnail')


if __name__ == '__main__':
    main()
