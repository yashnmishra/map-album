# GeoMap Catalog Manager

GeoMap Catalog Manager is a comprehensive desktop application designed to organize, visualize, and seamlessly stream massive geographic maps (up to 140-megapixels). It features an advanced asynchronous progressive rendering engine, strict hierarchical syncing to a local database, and Google Maps-style deep zoom tiling.

## Features

- **Progressive Map Viewer:** Instantly loads a 1920px preview while seamlessly streaming multi-gigabyte full-resolution images or Level-of-Detail (LOD) tile pyramids.
- **Deep Zoom & Tiling:** Systematically slices massive images into 256x256 multi-level LOD tile pyramids using a background asset pipeline, allowing efficient memory management.
- **Asynchronous Threading:** Uses PySide6 multithreading (QThread) to ensure the UI never freezes during heavy computational tasks like syncing and image decoding.
- **Robust Database Sync:** Keeps the local SQLite database continuously synchronized with the physical filesystem. Supports a geographic hierarchy (`State` &rarr; `District`).
- **Dynamic Metadata:** Implements an Entity-Attribute-Value (EAV) database schema for fully customizable metadata and tags.
- **Gallery & Filtering:** Provides 300px cached thumbnails, sorts via regex numerical analysis, and allows filtering by attributes.

## Architecture

The application uses an advanced Model-View-Controller (MVC) setup with multi-threading:
- **Frontend Layer:** `GalleryPanel`, `SyncProgressDialog`, and a hardware-accelerated `MapViewerWindow`.
- **Backend Services:** `FolderSyncService` for database synchronization and `CacheService` utilizing Pillow to generate thumbnails, previews, and map tiles.
- **Database:** Powered by SQLite and SQLAlchemy ORM.

## Tech Stack

- **GUI & Threading:** PySide6 (Qt6) - Native C++ wrapper
- **Database Engine:** SQLite 3 with SQLAlchemy ORM
- **Asset Generation:** Pillow (Python Imaging Library)

## Setup & Run

1. **Ensure Python is installed.** This project requires Python 3.
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python src/main.py
   ```
   *(Note: You may want to run `migrate_db.py` first depending on the database state).*

## Maps Folder Structure

The application expects map images to be organized hierarchically in the `maps/` directory by `State`, and `District`.

Example structure:
```text
maps/
├── Rajasthan/
│   ├── Jaipur/
│   │   ├── REE_Prospectivity_0.jpg
│   │   └── Soil_Geochemistry_1.jpg
│   ├── Jodhpur/
│   └── Udaipur/
└── Telangana/
```

## Documentation

For a more detailed breakdown of the application architecture and threading models, please refer to the `project_documentation.html` file included in this repository.
