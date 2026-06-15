from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel, QPushButton, QFormLayout, QLineEdit, QComboBox, QMessageBox, QHBoxLayout, QListWidget, QInputDialog
from src.models.models import Tag, CustomField
from src.services.folder_sync_service import FolderSyncService
from src.services.tag_service import TagService
from src.services.metadata_service import MetadataService

class AdminWindow(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.folder_sync = FolderSyncService(session)
        self.tag_service = TagService(session)
        self.metadata_service = MetadataService(session)
        
        self.setWindowTitle("Administration Panel")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.setup_tags_tab()
        self.setup_custom_fields_tab()
        
    def setup_tags_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.tag_list = QListWidget()
        self.refresh_tags()
        layout.addWidget(self.tag_list)
        
        btn_layout = QHBoxLayout()
        self.btn_new_tag = QPushButton("New Tag")
        self.btn_new_tag.clicked.connect(self.new_tag)
        btn_layout.addWidget(self.btn_new_tag)
        
        self.btn_rename_tag = QPushButton("Rename Tag")
        self.btn_rename_tag.clicked.connect(self.rename_tag)
        btn_layout.addWidget(self.btn_rename_tag)
        
        self.btn_delete_tag = QPushButton("Delete Tag")
        self.btn_delete_tag.clicked.connect(self.delete_tag)
        btn_layout.addWidget(self.btn_delete_tag)
        
        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "Tags")
        
    def refresh_tags(self):
        self.tag_list.clear()
        tags = self.session.query(Tag).order_by(Tag.name).all()
        for t in tags:
            self.tag_list.addItem(t.name)
            
    def new_tag(self):
        name, ok = QInputDialog.getText(self, "New Tag", "Tag Name:")
        if ok and name:
            self.tag_service.create_tag(name)
            self.refresh_tags()

    def rename_tag(self):
        item = self.tag_list.currentItem()
        if not item: return
        old_name = item.text()
        tag = self.session.query(Tag).filter_by(name=old_name).first()
        if tag:
            new_name, ok = QInputDialog.getText(self, "Rename Tag", "New Name:", text=old_name)
            if ok and new_name:
                self.tag_service.rename_tag(tag, new_name)
                self.refresh_tags()
                
    def delete_tag(self):
        item = self.tag_list.currentItem()
        if not item: return
        tag = self.session.query(Tag).filter_by(name=item.text()).first()
        if tag:
            self.tag_service.delete_tag(tag)
            self.refresh_tags()
        
    def setup_custom_fields_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.cf_name = QLineEdit()
        layout.addRow("Field Name:", self.cf_name)
        
        self.cf_type = QComboBox()
        self.cf_type.addItems(["Text", "Number", "Date", "Dropdown", "Multi-Select"])
        layout.addRow("Field Type:", self.cf_type)
        
        self.cf_options = QLineEdit()
        self.cf_options.setPlaceholderText("Comma separated options (for Dropdown)")
        layout.addRow("Options:", self.cf_options)
        
        self.btn_add_cf = QPushButton("Add Field")
        self.btn_add_cf.clicked.connect(self.add_custom_field)
        layout.addRow(self.btn_add_cf)
        
        self.tabs.addTab(tab, "Custom Fields")

    def add_custom_field(self):
        name = self.cf_name.text()
        ftype = self.cf_type.currentText()
        opts = [o.strip() for o in self.cf_options.text().split(",") if o.strip()]
        
        if name:
            self.metadata_service.create_custom_field(name, ftype, opts)
            QMessageBox.information(self, "Success", "Custom field added!")
            self.cf_name.clear()
            self.cf_options.clear()
