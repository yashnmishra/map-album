from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QLabel, QComboBox, QScrollArea, QGroupBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QTimer, Signal
from src.models.models import Map, CustomField, Tag
from src.services.metadata_service import MetadataService

class MetadataPanel(QWidget):
    map_deleted = Signal()
    
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.metadata_service = MetadataService(session)
        self.current_map_id = -1
        
        self.setup_ui()
        
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_metadata)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        self.form_layout = QFormLayout(content)
        
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_changed)
        self.form_layout.addRow("Map Name:", self.name_edit)
        
        self.full_screen_btn = QPushButton("Open in Full Screen")
        self.full_screen_btn.clicked.connect(self.open_full_screen)
        self.full_screen_btn.setEnabled(False)
        
        self.btn_delete_map = QPushButton("Delete Map")
        self.btn_delete_map.setStyleSheet("background-color: #d32f2f; color: white;")
        self.btn_delete_map.clicked.connect(self.delete_map)
        self.btn_delete_map.setEnabled(False)
        
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.full_screen_btn)
        button_layout.addWidget(self.btn_delete_map)
        self.form_layout.addRow("", button_layout)
        
        self.location_label = QLabel()
        self.form_layout.addRow("Location:", self.location_label)
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Comma separated tags")
        self.tags_edit.textChanged.connect(self.on_changed)
        self.form_layout.addRow("Tags:", self.tags_edit)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.textChanged.connect(self.on_changed)
        self.form_layout.addRow("Notes:", self.notes_edit)
        
        self.custom_fields_group = QGroupBox("Custom Metadata")
        self.custom_fields_layout = QFormLayout(self.custom_fields_group)
        self.form_layout.addRow(self.custom_fields_group)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        self.custom_widgets = {}

    def load_map(self, map_id: int):
        self.current_map_id = -1 
        self.save_timer.stop()
        
        if map_id == -1:
            self.clear_fields()
            self.full_screen_btn.setEnabled(False)
            self.btn_delete_map.setEnabled(False)
            return
            
        m = self.session.query(Map).get(map_id)
        if not m:
            return
            
        self.name_edit.setText(m.name)
        if m.district and m.district.state:
            loc = f"{m.district.state.country.name} > {m.district.state.name} > {m.district.name}"
            self.location_label.setText(loc)
        
        self.tags_edit.setText(", ".join([t.name for t in m.tags]))
        self.notes_edit.setText(m.notes or "")
        
        while self.custom_fields_layout.count():
            item = self.custom_fields_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.custom_widgets.clear()
        
        fields = self.session.query(CustomField).all()
        metadata_dict = {md.field_id: md.value for md in m.metadata_values}
        
        for field in fields:
            val = metadata_dict.get(field.id, "")
            
            if field.type == "Dropdown":
                combo = QComboBox()
                combo.addItem("")
                for opt in field.options:
                    combo.addItem(opt.value)
                combo.setCurrentText(val)
                combo.currentTextChanged.connect(self.on_changed)
                self.custom_fields_layout.addRow(field.name + ":", combo)
                self.custom_widgets[field.id] = combo
            else:
                edit = QLineEdit(val)
                edit.textChanged.connect(self.on_changed)
                self.custom_fields_layout.addRow(field.name + ":", edit)
                self.custom_widgets[field.id] = edit
                
        self.current_map_id = map_id
        self.full_screen_btn.setEnabled(True)
        self.btn_delete_map.setEnabled(True)

    def clear_fields(self):
        self.name_edit.clear()
        self.location_label.clear()
        self.tags_edit.clear()
        self.notes_edit.clear()
        while self.custom_fields_layout.count():
            item = self.custom_fields_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.custom_widgets.clear()
        self.full_screen_btn.setEnabled(False)
        self.btn_delete_map.setEnabled(False)

    def delete_map(self):
        if self.current_map_id == -1:
            return
            
        reply = QMessageBox.question(self, "Delete Map", "Are you sure you want to delete this map? This will permanently remove the file.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            m = self.session.query(Map).get(self.current_map_id)
            if m:
                from src.services.folder_sync_service import FolderSyncService
                folder_sync = FolderSyncService(self.session)
                folder_sync.delete_map(m)
                self.clear_fields()
                self.current_map_id = -1
                self.map_deleted.emit()

    def open_full_screen(self):
        if self.current_map_id == -1:
            return
        m = self.session.query(Map).get(self.current_map_id)
        if m:
            from src.ui.map_viewer import MapViewerWindow
            viewer = MapViewerWindow(m, self)
            viewer.exec()

    def on_changed(self):
        if self.current_map_id != -1:
            self.save_timer.start(1000) 

    def save_metadata(self):
        if self.current_map_id == -1:
            return
            
        m = self.session.query(Map).get(self.current_map_id)
        if not m:
            return
            
        m.name = self.name_edit.text()
        m.notes = self.notes_edit.toPlainText()
        
        tags_text = self.tags_edit.text().strip()
        tag_names = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        db_tags = []
        for t_name in tag_names:
            tag = self.session.query(Tag).filter_by(name=t_name).first()
            if not tag:
                tag = Tag(name=t_name)
                self.session.add(tag)
            db_tags.append(tag)
        m.tags = db_tags
        
        for field_id, widget in self.custom_widgets.items():
            if isinstance(widget, QComboBox):
                val = widget.currentText()
            else:
                val = widget.text()
            self.metadata_service.update_map_metadata(m, field_id, val)
            
        self.session.commit()
