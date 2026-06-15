import os
import math
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                               QGraphicsPixmapItem, QWidget, QHBoxLayout, QPushButton, 
                               QGraphicsItem, QGraphicsOpacityEffect)
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence, QPainter, QImageReader, QPixmapCache, QImage, QNativeGestureEvent
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPropertyAnimation, QEasingCurve, QEvent
from src.models.models import Map
from src.utils.paths import get_absolute_path

class ImageLoaderThread(QThread):
    finished = Signal(object)
    
    def __init__(self, path):
        super().__init__()
        self.path = path
        
    def run(self):
        if os.path.exists(self.path):
            # MUST load as QImage in background thread. QPixmap crashes off main thread.
            image = QImage(self.path)
            self.finished.emit(image)

class TiledMapGraphicsItem(QGraphicsItem):
    def __init__(self, tile_dir, full_width, full_height, tile_size=256):
        super().__init__()
        self.tile_dir = tile_dir
        self.full_width = full_width
        self.full_height = full_height
        self.tile_size = tile_size
        
        # Optimize using Qt's highly optimized native cache (Limit: 500 MB)
        QPixmapCache.setCacheLimit(500 * 1024)
        
    def boundingRect(self):
        return QRectF(0, 0, self.full_width, self.full_height)
        
    def paint(self, painter, option, widget):
        exposed = option.exposedRect
        
        # Calculate dynamic LOD based on zoom scale
        scale = painter.transform().m11()
        level = 0
        if scale > 0.0 and scale < 1.0:
            calc_level = int(-math.log2(scale))
            level = max(0, calc_level)
            
        # Fallback to nearest valid level if we zoomed out past generated pyramids
        while not os.path.exists(os.path.join(self.tile_dir, str(level))) and level > 0:
            level -= 1
            
        effective_tile_size = self.tile_size * (2 ** level)
        
        # Calculate which tiles intersect the exposed rectangle
        c_start = max(0, int(exposed.left() // effective_tile_size))
        c_end = int(math.ceil(exposed.right() / effective_tile_size))
        r_start = max(0, int(exposed.top() // effective_tile_size))
        r_end = int(math.ceil(exposed.bottom() / effective_tile_size))
        
        for r in range(r_start, r_end):
            for c in range(c_start, c_end):
                # Unique key for QPixmapCache
                cache_key = f"{self.tile_dir}_{level}_{c}_{r}"
                
                # Check cache first (fast path)
                pixmap = QPixmapCache.find(cache_key)
                
                if not pixmap:
                    # Cache miss: load from disk (slow path)
                    path = os.path.join(self.tile_dir, str(level), f"{c}_{r}.jpg")
                    if os.path.exists(path):
                        # Use QImageReader for faster native decoding
                        reader = QImageReader(path)
                        img = reader.read()
                        if not img.isNull():
                            pixmap = QPixmap.fromImage(img)
                            QPixmapCache.insert(cache_key, pixmap)
                        else:
                            continue
                    else:
                        continue
                        
                painter.drawPixmap(
                    int(c * effective_tile_size), 
                    int(r * effective_tile_size), 
                    int(effective_tile_size), 
                    int(effective_tile_size), 
                    pixmap
                )

class MapViewerWindow(QDialog):
    def __init__(self, map_obj: Map, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Map Full Screen")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()
        
        self.map_obj = map_obj
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QGraphicsView()
        self.view.setStyleSheet("background-color: black; border: none;")
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)
        
        self.view.viewport().installEventFilter(self)
        
        self.setup_overlay_buttons()
        self.setup_shortcuts()
        
        self.load_map()
        
    def eventFilter(self, obj, event):
        if obj == self.view.viewport() and event.type() == QEvent.NativeGesture:
            if event.gestureType() == Qt.ZoomNativeGesture:
                zoom_factor = 1.0 + event.value()
                if zoom_factor > 0:
                    self.view.scale(zoom_factor, zoom_factor)
                return True
        return super().eventFilter(obj, event)
        
    def load_map(self):
        preview_abs = get_absolute_path(self.map_obj.preview_path) if self.map_obj.preview_path else None
        original_abs = get_absolute_path(self.map_obj.relative_path)
        tile_dir_abs = get_absolute_path(self.map_obj.tile_dir_path) if self.map_obj.tile_dir_path else None
        thumb_abs = get_absolute_path(self.map_obj.thumbnail_path) if self.map_obj.thumbnail_path else None
        
        # 1. Instantly load preview if it exists, else load thumbnail
        initial_path = None
        if preview_abs and os.path.isfile(preview_abs):
            initial_path = preview_abs
        elif thumb_abs and os.path.isfile(thumb_abs):
            initial_path = thumb_abs
        
        if initial_path:
            self.preview_pixmap = QPixmap(initial_path)
            self.preview_item = QGraphicsPixmapItem(self.preview_pixmap)
            self.preview_item.setTransformationMode(Qt.SmoothTransformation)
            self.scene.addItem(self.preview_item)
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            # Fallback
            self.preview_item = None
            
        # 2. Progressively load full resolution or tiles
        if self.map_obj.has_tiles and tile_dir_abs and os.path.exists(tile_dir_abs):
            # Tiled Deep Zoom
            # We need the full dimensions. Get from ImageReader without loading into memory.
            reader = QImageReader(original_abs)
            size = reader.size()
            width, height = size.width(), size.height()
            
            self.tiled_item = TiledMapGraphicsItem(tile_dir_abs, width, height)
            self.scene.addItem(self.tiled_item)
            
            # Since preview is smaller, we must scale it up to match the tiled item's full size
            if self.preview_item:
                scale_x = width / self.preview_pixmap.width()
                scale_y = height / self.preview_pixmap.height()
                self.preview_item.setScale(max(scale_x, scale_y))
                # Now that the tiled item covers it, we can fade out the preview
                self.fade_out_preview()
            
            # Reset view to fit the new full size scene
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            
        else:
            # Asynchronous Full-Res Loading
            if original_abs and os.path.exists(original_abs):
                self.loading_label.show()
                self.loading_label.setText("Loading Full Resolution...")
                self.loading_label.adjustSize()
                self.reposition_overlays()
                
                self.loader = ImageLoaderThread(original_abs)
                self.loader.finished.connect(self.on_full_res_loaded)
                self.loader.start()

    def on_full_res_loaded(self, image):
        self.loading_label.hide()
        if not image or image.isNull():
            return
            
        pixmap = QPixmap.fromImage(image)
        self.full_item = QGraphicsPixmapItem(pixmap)
        self.full_item.setTransformationMode(Qt.SmoothTransformation)
        
        # Set opacity to 0 initially for fade in
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.full_item.setGraphicsEffect(self.opacity_effect)
        
        self.scene.addItem(self.full_item)
        
        if self.preview_item and self.preview_pixmap:
            # Scale preview to match full res
            scale_x = pixmap.width() / self.preview_pixmap.width()
            scale_y = pixmap.height() / self.preview_pixmap.height()
            self.preview_item.setScale(max(scale_x, scale_y))
            
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Smooth Fade Transition
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500) # 500ms fade
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self.remove_preview)
        self.animation.start()

    def fade_out_preview(self):
        if not self.preview_item: return
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.preview_item.setGraphicsEffect(self.opacity_effect)
        
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(800)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.remove_preview)
        self.animation.start()

    def remove_preview(self):
        if self.preview_item:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close)
        QShortcut(QKeySequence("+"), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("="), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("-"), self).activated.connect(self.zoom_out)
        QShortcut(QKeySequence("0"), self).activated.connect(self.fit_to_screen)
        
    def setup_overlay_buttons(self):
        # Loading Label
        from PySide6.QtWidgets import QLabel
        self.loading_label = QLabel("Loading...", self)
        self.loading_label.setStyleSheet("""
            color: white; 
            background-color: rgba(30, 30, 30, 200); 
            padding: 10px 20px; 
            border-radius: 8px; 
            font-size: 16px;
            font-weight: bold;
        """)
        self.loading_label.hide()
        
        # Toolbar Overlay
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(self.overlay)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        btn_layout.setSpacing(15)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_fit = QPushButton("Reset")
        self.btn_zoom_in = QPushButton("+")
        self.btn_close = QPushButton("X")
        
        for btn in (self.btn_zoom_out, self.btn_fit, self.btn_zoom_in, self.btn_close):
            if btn == self.btn_fit:
                btn.setFixedSize(80, 50)
            else:
                btn.setFixedSize(50, 50)
                
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(40, 42, 54, 220);
                    color: white;
                    border: 2px solid #8aadf4;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #8aadf4;
                    color: #1e2030;
                }
            """)
            btn_layout.addWidget(btn)
            
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_fit.clicked.connect(self.fit_to_screen)
        self.btn_close.clicked.connect(self.close)
        
    def reposition_overlays(self):
        if hasattr(self, 'overlay'):
            overlay_w = self.overlay.sizeHint().width()
            overlay_h = self.overlay.sizeHint().height()
            # Bottom Center
            self.overlay.setGeometry((self.width() - overlay_w) // 2, self.height() - overlay_h - 40, overlay_w, overlay_h)
            
        if hasattr(self, 'loading_label') and not self.loading_label.isHidden():
            lw = self.loading_label.sizeHint().width()
            lh = self.loading_label.sizeHint().height()
            self.loading_label.setGeometry((self.width() - lw) // 2, self.height() - overlay_h - lh - 60, lw, lh)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reposition_overlays()
            
    def zoom_in(self):
        self.view.scale(1.25, 1.25)

    def zoom_out(self):
        self.view.scale(1 / 1.25, 1 / 1.25)
        
    def fit_to_screen(self):
        if self.scene.sceneRect().isValid():
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
