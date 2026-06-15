import os
import math
import logging
from dataclasses import dataclass
from PIL import Image

# Suppress massive image warnings as we are explicitly handling them
Image.MAX_IMAGE_PIXELS = None

from src.utils.paths import get_thumbnails_dir, get_cache_dir, get_tiles_dir, get_relative_path

logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    total_files: int = 0
    processed_files: int = 0
    thumbnails_generated: int = 0
    previews_generated: int = 0
    tiles_generated: int = 0
    cache_size_bytes: int = 0

class CacheService:
    def __init__(self):
        self.thumb_size = (300, 300)
        self.preview_size = (1920, 1920)
        self.tile_size = 256
        self.max_dimension_for_tiles = 5000
        
    def generate_cache(self, original_abs_path: str, map_id: int) -> dict:
        """
        Generates thumbnail, preview, and tiles.
        Returns dict with paths and generation metrics.
        """
        metrics = {'tiles_generated': 0}
        
        try:
            if not os.path.exists(original_abs_path):
                return {}
                
            thumb_filename = f"thumb_{map_id}.jpg"
            thumb_abs_path = os.path.join(get_thumbnails_dir(), thumb_filename)
            
            preview_filename = f"preview_{map_id}.jpg"
            preview_abs_path = os.path.join(get_cache_dir(), preview_filename)
            
            tile_dir_name = f"tiles_{map_id}"
            tile_dir_abs_path = os.path.join(get_tiles_dir(), tile_dir_name)
            
            has_tiles = False
            
            # Check if cache already exists (optimization)
            if os.path.exists(thumb_abs_path) and os.path.exists(preview_abs_path):
                # We skip full generation if previews exist, assuming tiles also exist if needed
                # However, for a complete sync, we will just regenerate if it reaches here or we can skip
                pass
                
            with Image.open(original_abs_path) as img:
                # RGB Conversion
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                width, height = img.size
                
                # Generate Thumbnail
                img_thumb = img.copy()
                img_thumb.thumbnail(self.thumb_size)
                img_thumb.save(thumb_abs_path, "JPEG", quality=85)
                
                # Generate Preview
                img_preview = img.copy()
                img_preview.thumbnail(self.preview_size)
                img_preview.save(preview_abs_path, "JPEG", quality=85)
                
                # Generate Tiles if large enough
                if width > self.max_dimension_for_tiles or height > self.max_dimension_for_tiles:
                    has_tiles = True
                    os.makedirs(tile_dir_abs_path, exist_ok=True)
                    tiles_count = self._generate_tile_pyramid(img, tile_dir_abs_path)
                    metrics['tiles_generated'] = tiles_count
                    
            return {
                'thumbnail_path': get_relative_path(thumb_abs_path),
                'preview_path': get_relative_path(preview_abs_path),
                'has_tiles': has_tiles,
                'tile_dir_path': get_relative_path(tile_dir_abs_path) if has_tiles else None,
                'tiles_generated': metrics['tiles_generated']
            }
            
        except Exception as e:
            logger.error(f"Error generating cache for map {map_id}: {e}")
            return {}

    def _generate_tile_pyramid(self, img: Image.Image, output_dir: str) -> int:
        tiles_generated = 0
        width, height = img.size
        
        level = 0
        current_img = img
        
        while True:
            level_dir = os.path.join(output_dir, str(level))
            os.makedirs(level_dir, exist_ok=True)
            
            cw, ch = current_img.size
            cols = math.ceil(cw / self.tile_size)
            rows = math.ceil(ch / self.tile_size)
            
            for r in range(rows):
                for c in range(cols):
                    left = c * self.tile_size
                    upper = r * self.tile_size
                    right = min(left + self.tile_size, cw)
                    lower = min(upper + self.tile_size, ch)
                    
                    tile = current_img.crop((left, upper, right, lower))
                    tile_path = os.path.join(level_dir, f"{c}_{r}.jpg")
                    tile.save(tile_path, "JPEG", quality=85)
                    tiles_generated += 1
            
            if cw <= self.tile_size and ch <= self.tile_size:
                break
                
            level += 1
            # Resize by 50%
            new_w = max(1, cw // 2)
            new_h = max(1, ch // 2)
            current_img = current_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
        return tiles_generated
