import os
import sys

def get_base_dir():
    """Get the base directory of the application, ensuring portability."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

def get_maps_dir():
    maps_dir = os.path.join(get_base_dir(), 'maps')
    os.makedirs(maps_dir, exist_ok=True)
    return maps_dir

def get_thumbnails_dir():
    thumbnails_dir = os.path.join(get_base_dir(), 'thumbnails')
    os.makedirs(thumbnails_dir, exist_ok=True)
    return thumbnails_dir

def get_cache_dir():
    cache_dir = os.path.join(get_base_dir(), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_tiles_dir():
    tiles_dir = os.path.join(get_cache_dir(), 'tiles')
    os.makedirs(tiles_dir, exist_ok=True)
    return tiles_dir

def get_absolute_path(relative_path):
    if not relative_path:
        return ""
    return os.path.join(get_base_dir(), relative_path)

def get_relative_path(absolute_path):
    if not absolute_path:
        return ""
    base_dir = get_base_dir()
    try:
        # Use relpath to store relative path against base_dir
        return os.path.relpath(absolute_path, base_dir)
    except ValueError:
        return absolute_path
