import os
from PySide6.QtWidgets import QMainWindow, QSplitter, QMenuBar, QMenu, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from src.widgets.tree_panel import TreePanel
from src.widgets.gallery_panel import GalleryPanel
from src.widgets.metadata_panel import MetadataPanel
from src.ui.admin_window import AdminWindow
from src.ui.filter_builder import FilterBuilder
from src.services.export_service import ExportService
from src.models.models import Map

class MainWindow(QMainWindow):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.export_service = ExportService()
        
        self.setWindowTitle("GeoMap Catalog Manager")
        self.resize(1200, 800)
        
        self.setup_ui()
        self.setup_menu()
        
    def setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        
        self.tree_panel = TreePanel(self.session)
        self.gallery_panel = GalleryPanel(self.session)
        self.metadata_panel = MetadataPanel(self.session)
        
        splitter.addWidget(self.tree_panel)
        splitter.addWidget(self.gallery_panel)
        splitter.addWidget(self.metadata_panel)
        
        splitter.setSizes([250, 600, 350])
        self.setCentralWidget(splitter)
        
        self.tree_panel.district_selected.connect(self.gallery_panel.load_district_maps)
        self.gallery_panel.map_selected.connect(self.metadata_panel.load_map)
        self.metadata_panel.map_deleted.connect(self.gallery_panel.apply_filter)
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        sync_action = file_menu.addAction("Sync with Filesystem")
        sync_action.triggered.connect(self.sync_filesystem)
        file_menu.addSeparator()
        
        action_admin = file_menu.addAction("Administration")
        action_admin.triggered.connect(self.open_admin)
        
        action_filter = file_menu.addAction("Filter Builder")
        action_filter.triggered.connect(self.open_filter)
        
        action_export = file_menu.addAction("Export Current District (CSV)")
        action_export.triggered.connect(self.export_csv)
        
        file_menu.addSeparator()
        
        action_exit = file_menu.addAction("Exit")
        action_exit.triggered.connect(self.close)

    def sync_filesystem(self):
        from src.ui.sync_dialog import SyncProgressDialog, SyncWorker
        
        self.sync_dialog = SyncProgressDialog(self)
        self.sync_worker = SyncWorker(self.session)
        self.sync_dialog.set_worker(self.sync_worker)
        
        self.sync_worker.finished.connect(self._on_sync_finished)
        
        self.sync_worker.start()
        self.sync_dialog.exec()

    def _on_sync_finished(self, items_added):
        self.tree_panel.populate_tree()
        self.gallery_panel.apply_filter()

    def open_admin(self):
        dlg = AdminWindow(self.session, self)
        dlg.exec()
        self.tree_panel.populate_tree()
        
    def open_filter(self):
        dlg = FilterBuilder(self.session, self)
        if dlg.exec():
            filters = dlg.get_filters()
            QMessageBox.information(self, "Filters", f"Filters generated: {filters}\n\nNote: Visual filtering of the gallery is to be fully integrated in the next version.")

    def export_csv(self):
        dist_id = self.gallery_panel.current_district_id
        if dist_id == -1:
            QMessageBox.warning(self, "Export", "Select a district first.")
            return
            
        maps = self.session.query(Map).filter(Map.district_id == dist_id).all()
        if not maps:
            QMessageBox.information(self, "Export", "No maps to export.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if path:
            if self.export_service.export_maps(maps, path, 'csv'):
                QMessageBox.information(self, "Success", "Export successful.")
            else:
                QMessageBox.critical(self, "Error", "Export failed.")
