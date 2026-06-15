from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QComboBox, QLineEdit, QHBoxLayout
from src.models.models import CustomField

class FilterBuilder(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Filter Builder")
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        self.filters_layout = QVBoxLayout()
        layout.addLayout(self.filters_layout)
        
        self.btn_add_filter = QPushButton("Add Condition")
        self.btn_add_filter.clicked.connect(self.add_condition)
        layout.addWidget(self.btn_add_filter)
        
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply Filter")
        self.btn_apply.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)
        
        self.conditions = []
        
    def add_condition(self):
        row = QHBoxLayout()
        
        field_combo = QComboBox()
        field_combo.addItems(["Country", "State", "District", "Map Name", "Tags", "Notes"])
        
        custom_fields = self.session.query(CustomField).all()
        for cf in custom_fields:
            field_combo.addItem(cf.name)
            
        op_combo = QComboBox()
        op_combo.addItems(["Equals", "Contains"])
        
        val_edit = QLineEdit()
        
        row.addWidget(field_combo)
        row.addWidget(op_combo)
        row.addWidget(val_edit)
        
        btn_remove = QPushButton("X")
        row.addWidget(btn_remove)
        
        self.filters_layout.addLayout(row)
        
        condition = {"field": field_combo, "op": op_combo, "val": val_edit, "layout": row}
        self.conditions.append(condition)
        
        btn_remove.clicked.connect(lambda: self.remove_condition(condition))

    def remove_condition(self, condition):
        for i in reversed(range(condition["layout"].count())): 
            widget = condition["layout"].itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.filters_layout.removeItem(condition["layout"])
        self.conditions.remove(condition)
        
    def get_filters(self):
        filters = []
        for c in self.conditions:
            filters.append({
                "field": c["field"].currentText(),
                "op": c["op"].currentText(),
                "value": c["val"].text()
            })
        return filters
