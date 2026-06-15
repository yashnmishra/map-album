from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QSlider, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QFileDialog, QMenu, QLineEdit
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from src.models.models import Map, CustomField, MapMetadata
from src.utils.paths import get_absolute_path
import os

class GalleryPanel(QWidget):
    map_selected = Signal(int)
    
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.current_district_id = -1
        
        layout = QVBoxLayout(self)
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 400)
        self.zoom_slider.setValue(150)
        self.zoom_slider.valueChanged.connect(self.update_icon_size)
        toolbar.addWidget(self.zoom_slider)
        
        toolbar.addSpacing(10)
        self.btn_add_map = QPushButton("Add Map")
        self.btn_add_map.clicked.connect(self.add_map)
        toolbar.addWidget(self.btn_add_map)
        
        toolbar.addSpacing(20)
        toolbar.addWidget(QLabel("Metadata Filter:"))
        self.metadata_field_filter = QComboBox()
        self.metadata_field_filter.currentTextChanged.connect(self.on_metadata_field_changed)
        toolbar.addWidget(self.metadata_field_filter)
        
        self.metadata_value_filter = QComboBox()
        self.metadata_value_filter.addItem("All")
        self.metadata_value_filter.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(self.metadata_value_filter)
        
        toolbar.addSpacing(20)
        toolbar.addWidget(QLabel("Sort:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name (A-Z)", "Name (Z-A)"])
        self.sort_combo.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(self.sort_combo)
        
        toolbar.addSpacing(20)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search maps...")
        self.search_bar.textChanged.connect(self.on_filter_changed)
        toolbar.addWidget(self.search_bar)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(150, 150))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(10)
        self.list_widget.setTextElideMode(Qt.ElideRight)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

    def update_icon_size(self, size):
        self.list_widget.setIconSize(QSize(size, size))

    def load_district_maps(self, district_id: int):
        self.current_district_id = district_id
        self.populate_metadata_fields()
        self.apply_filter()
        
    def populate_metadata_fields(self):
        current_field = self.metadata_field_filter.currentText()
        self.metadata_field_filter.blockSignals(True)
        self.metadata_field_filter.clear()
        self.metadata_field_filter.addItem("None", None)
        
        fields = self.session.query(CustomField).all()
        for f in fields:
            self.metadata_field_filter.addItem(f.name, f.id)
            
        idx = self.metadata_field_filter.findText(current_field)
        if idx >= 0:
            self.metadata_field_filter.setCurrentIndex(idx)
        else:
            self.metadata_field_filter.setCurrentIndex(0)
            
        self.metadata_field_filter.blockSignals(False)
        self.on_metadata_field_changed()
        
    def on_metadata_field_changed(self):
        current_val = self.metadata_value_filter.currentText()
        self.metadata_value_filter.blockSignals(True)
        self.metadata_value_filter.clear()
        self.metadata_value_filter.addItem("All")
        
        field_id = self.metadata_field_filter.currentData()
        if field_id:
            values = self.session.query(MapMetadata.value).filter_by(field_id=field_id).distinct().all()
            for v in sorted([val[0] for val in values if val[0]]):
                self.metadata_value_filter.addItem(v)
                
        idx = self.metadata_value_filter.findText(current_val)
        if idx >= 0:
            self.metadata_value_filter.setCurrentIndex(idx)
        else:
            self.metadata_value_filter.setCurrentIndex(0)
            
        self.metadata_value_filter.blockSignals(False)
        self.apply_filter()

    def on_filter_changed(self):
        self.apply_filter()

    def apply_filter(self):
        self.list_widget.clear()
        
        if self.current_district_id == -1:
            return
            
        query = self.session.query(Map).filter(Map.district_id == self.current_district_id)
        
        field_id = self.metadata_field_filter.currentData()
        selected_value = self.metadata_value_filter.currentText()
        
        if field_id and selected_value and selected_value != "All":
            query = query.join(MapMetadata).filter(
                MapMetadata.field_id == field_id,
                MapMetadata.value == selected_value
            )
                
        search_text = self.search_bar.text().strip().lower()
        if search_text:
            # Using python-side filtering or SQLAlchemy like()
            query = query.filter(Map.name.ilike(f"%{search_text}%"))
                
        maps = query.all()
        
        import re
        def natural_sort_key(m):
            match = re.search(r'\d+', m.name)
            num = int(match.group()) if match else float('inf')
            return (num, m.name.lower())
            
        maps.sort(key=natural_sort_key, reverse=(self.sort_combo.currentText() == "Name (Z-A)"))
        
        for m in maps:
            item = QListWidgetItem()
            
            # Manually truncate long names for the display text
            max_len = 15
            display_name = m.name if len(m.name) <= max_len else m.name[:max_len] + "..."
            
            item.setText(display_name)
            item.setToolTip(m.name)
            item.setData(Qt.UserRole, m.id)
            
            thumb_abs = get_absolute_path(m.thumbnail_path)
            if thumb_abs and os.path.exists(thumb_abs):
                item.setIcon(QIcon(thumb_abs))
            else:
                map_abs = get_absolute_path(m.relative_path)
                if map_abs and os.path.exists(map_abs):
                    item.setIcon(QIcon(map_abs))
                    
            self.list_widget.addItem(item)

    def on_selection_changed(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            self.map_selected.emit(-1)
            return
            
        map_id = selected[0].data(Qt.UserRole)
        self.map_selected.emit(map_id)

    def on_item_double_clicked(self, item):
        map_id = item.data(Qt.UserRole)
        self.open_full_screen(map_id)
        
    def open_full_screen(self, map_id):
        m = self.session.query(Map).get(map_id)
        if m:
            from src.ui.map_viewer import MapViewerWindow
            viewer = MapViewerWindow(m, self)
            viewer.exec()

    def add_map(self):
        if self.current_district_id == -1:
            QMessageBox.warning(self, "Warning", "Please select a district first.")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not file_path:
            return
            
        from src.services.folder_sync_service import FolderSyncService
        from src.services.cache_service import CacheService
        from src.models.models import District
        from src.utils.paths import get_relative_path
        import shutil
        
        folder_sync = FolderSyncService(self.session)
        district = self.session.query(District).get(self.current_district_id)
        
        target_folder = folder_sync.get_district_folder_path(district.id)
        os.makedirs(target_folder, exist_ok=True)
        
        filename = os.path.basename(file_path)
        base, ext = os.path.splitext(filename)
        counter = 1
        new_abs_path = os.path.join(target_folder, filename)
        while os.path.exists(new_abs_path):
            new_abs_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
            counter += 1
            
        shutil.copy(file_path, new_abs_path)
        rel_path = get_relative_path(new_abs_path)
        
        new_map = Map(
            district_id=district.id,
            name=os.path.basename(new_abs_path),
            relative_path=rel_path
        )
        self.session.add(new_map)
        self.session.commit()
        
        cache_service = CacheService()
        cache_result = cache_service.generate_cache(new_abs_path, new_map.id)
        
        if cache_result:
            new_map.thumbnail_path = cache_result.get('thumbnail_path')
            new_map.preview_path = cache_result.get('preview_path')
            new_map.has_tiles = cache_result.get('has_tiles', False)
            new_map.tile_dir_path = cache_result.get('tile_dir_path')
            self.session.commit()
        
        self.apply_filter()

    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        delete_action = menu.addAction("Delete Map")
        action = menu.exec(self.list_widget.mapToGlobal(position))
        
        if action == delete_action:
            map_id = item.data(Qt.UserRole)
            self.delete_map(map_id)
            
    def delete_map(self, map_id):
        reply = QMessageBox.question(self, "Delete Map", "Are you sure you want to delete this map? This will permanently remove the file.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            m = self.session.query(Map).get(map_id)
            if m:
                from src.services.folder_sync_service import FolderSyncService
                folder_sync = FolderSyncService(self.session)
                folder_sync.delete_map(m)
                self.apply_filter()
                self.map_selected.emit(-1)


