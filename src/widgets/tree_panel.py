from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMenu, QInputDialog, QMessageBox
from PySide6.QtCore import Qt, Signal
from src.models.models import Country, State, District

class TreePanel(QWidget):
    district_selected = Signal(int)
    
    def __init__(self, session):
        super().__init__()
        self.session = session
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.tree)
        self.populate_tree()

    def populate_tree(self):
        self.tree.clear()
        countries = self.session.query(Country).order_by(Country.name).all()
        for country in countries:
            country_item = QTreeWidgetItem(self.tree, [country.name])
            country_item.setData(0, Qt.UserRole, {"type": "country", "id": country.id})
            
            for state in sorted(country.states, key=lambda s: s.name):
                state_item = QTreeWidgetItem(country_item, [state.name])
                state_item.setData(0, Qt.UserRole, {"type": "state", "id": state.id})
                
                for district in sorted(state.districts, key=lambda d: d.name):
                    district_item = QTreeWidgetItem(state_item, [district.name])
                    district_item.setData(0, Qt.UserRole, {"type": "district", "id": district.id})
                    
        self.tree.expandAll()

    def on_selection_changed(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
            
        item = selected[0]
        data = item.data(0, Qt.UserRole)
        
        if data and data.get("type") == "district":
            self.district_selected.emit(data["id"])
        else:
            self.district_selected.emit(-1)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        menu = QMenu()
        
        if not item:
            action_add_country = menu.addAction("Add New Country")
            action = menu.exec(self.tree.mapToGlobal(position))
            if action == action_add_country:
                self.add_region("country", None)
            return
            
        data = item.data(0, Qt.UserRole)
        region_type = data.get("type")
        region_id = data.get("id")
        
        if region_type == "country":
            action_add = menu.addAction("Add State")
            menu.addSeparator()
            action_delete = menu.addAction("Delete Country")
        elif region_type == "state":
            action_add = menu.addAction("Add District")
            menu.addSeparator()
            action_delete = menu.addAction("Delete State")
        elif region_type == "district":
            action_add = None
            action_delete = menu.addAction("Delete District")
        else:
            return
            
        action = menu.exec(self.tree.mapToGlobal(position))
        
        if action == action_add:
            if region_type == "country":
                self.add_region("state", region_id)
            elif region_type == "state":
                self.add_region("district", region_id)
        elif action == action_delete:
            self.delete_region(region_type, region_id)
            
    def add_region(self, region_type: str, parent_id: int):
        from src.services.folder_sync_service import FolderSyncService
        folder_sync = FolderSyncService(self.session)
        
        name, ok = QInputDialog.getText(self, f"Add {region_type.capitalize()}", "Name:")
        if not ok or not name.strip():
            return
            
        name = name.strip()
        success = False
        
        if region_type == "country":
            success = folder_sync.add_country(name)
        elif region_type == "state":
            success = folder_sync.add_state(parent_id, name)
        elif region_type == "district":
            success = folder_sync.add_district(parent_id, name)
            
        if success:
            self.populate_tree()
        else:
            QMessageBox.warning(self, "Error", f"Failed to add {region_type}. It might already exist.")
            
    def delete_region(self, region_type: str, region_id: int):
        reply = QMessageBox.question(self, f"Delete {region_type.capitalize()}", 
            f"Are you sure you want to delete this {region_type}? It must be empty.", 
            QMessageBox.Yes | QMessageBox.No)
            
        if reply != QMessageBox.Yes:
            return
            
        from src.services.folder_sync_service import FolderSyncService
        folder_sync = FolderSyncService(self.session)
        success = False
        msg = ""
        
        if region_type == "country":
            success, msg = folder_sync.delete_country(region_id)
        elif region_type == "state":
            success, msg = folder_sync.delete_state(region_id)
        elif region_type == "district":
            success, msg = folder_sync.delete_district(region_id)
            
        if success:
            self.populate_tree()
            self.district_selected.emit(-1)
        else:
            QMessageBox.warning(self, "Error", msg)
