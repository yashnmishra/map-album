import logging
from sqlalchemy.orm import Session
from src.models.models import Tag

logger = logging.getLogger(__name__)

class TagService:
    def __init__(self, session: Session):
        self.session = session

    def create_tag(self, name: str) -> Tag:
        tag = Tag(name=name)
        self.session.add(tag)
        self.session.commit()
        return tag

    def rename_tag(self, tag: Tag, new_name: str) -> bool:
        try:
            tag.name = new_name
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error renaming tag: {e}")
            return False

    def delete_tag(self, tag: Tag) -> bool:
        try:
            self.session.delete(tag)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting tag: {e}")
            return False

    def merge_tags(self, source_tag: Tag, target_tag: Tag) -> bool:
        """Merge source_tag into target_tag.
        All maps having source_tag will now point to target_tag if not already present.
        """
        try:
            for map_obj in source_tag.maps:
                if target_tag not in map_obj.tags:
                    map_obj.tags.append(target_tag)
            
            self.session.delete(source_tag)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error merging tags: {e}")
            return False
