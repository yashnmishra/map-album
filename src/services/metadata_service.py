import logging
from typing import List
from sqlalchemy.orm import Session
from src.models.models import CustomField, CustomFieldOption, MapMetadata, Map

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, session: Session):
        self.session = session

    def create_custom_field(self, name: str, field_type: str, options: List[str] = None) -> CustomField:
        try:
            field = CustomField(name=name, type=field_type)
            self.session.add(field)
            self.session.flush() # to get ID
            
            if options and field_type in ['Dropdown', 'Multi-Select']:
                for opt_val in options:
                    opt = CustomFieldOption(field_id=field.id, value=opt_val)
                    self.session.add(opt)
            
            self.session.commit()
            return field
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating custom field: {e}")
            return None

    def update_map_metadata(self, map_obj: Map, field_id: int, value: str) -> bool:
        try:
            metadata_entry = self.session.query(MapMetadata).filter_by(
                map_id=map_obj.id, field_id=field_id
            ).first()
            
            if metadata_entry:
                if value is None or value == "":
                    self.session.delete(metadata_entry)
                else:
                    metadata_entry.value = value
            else:
                if value is not None and value != "":
                    new_entry = MapMetadata(map_id=map_obj.id, field_id=field_id, value=value)
                    self.session.add(new_entry)
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating map metadata: {e}")
            return False
