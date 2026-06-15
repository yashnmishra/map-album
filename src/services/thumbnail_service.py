import os
import logging
from PIL import Image
from src.utils.paths import get_thumbnails_dir, get_relative_path

logger = logging.getLogger(__name__)

class ThumbnailService:
    def __init__(self, size=(256, 256)):
        self.size = size

    def generate_thumbnail(self, original_abs_path: str, map_id: int) -> str:
        """Generates a thumbnail and returns its relative path."""
        try:
            if not os.path.exists(original_abs_path):
                return ""
            
            thumb_filename = f"thumb_{map_id}.jpg"
            thumb_abs_path = os.path.join(get_thumbnails_dir(), thumb_filename)
            
            with Image.open(original_abs_path) as img:
                img.thumbnail(self.size)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(thumb_abs_path, "JPEG")
                
            return get_relative_path(thumb_abs_path)
        except Exception as e:
            logger.error(f"Error generating thumbnail for map {map_id}: {e}")
            return ""
