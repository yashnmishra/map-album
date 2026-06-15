import os
import shutil
import logging
from sqlalchemy.orm import Session
from src.models.models import Country, State, District, Map
from src.utils.paths import get_maps_dir, get_relative_path, get_absolute_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FolderSyncService:
    def __init__(self, session: Session):
        self.session = session

    def get_district_folder_path(self, district_id: int) -> str:
        district = self.session.query(District).get(district_id)
        if not district:
            return ""
        state = district.state
        country = state.country
        return os.path.join(get_maps_dir(), country.name, state.name, district.name)

    def rename_country(self, country: Country, new_name: str) -> bool:
        old_name = country.name
        old_folder = os.path.join(get_maps_dir(), old_name)
        new_folder = os.path.join(get_maps_dir(), new_name)
        
        physical_renamed = False
        if os.path.exists(old_folder):
            try:
                os.rename(old_folder, new_folder)
                physical_renamed = True
            except OSError as e:
                logger.error(f"Failed to rename country folder: {e}")
                return False
                
        try:
            country.name = new_name
            for state in country.states:
                for district in state.districts:
                    for m in district.maps:
                        m.relative_path = m.relative_path.replace(f"maps/{old_name}/", f"maps/{new_name}/", 1)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Database update failed, rolling back: {e}")
            self.session.rollback()
            if physical_renamed:
                os.rename(new_folder, old_folder)
            return False

    def rename_state(self, state: State, new_name: str) -> bool:
        country_name = state.country.name
        old_name = state.name
        old_folder = os.path.join(get_maps_dir(), country_name, old_name)
        new_folder = os.path.join(get_maps_dir(), country_name, new_name)
        
        physical_renamed = False
        if os.path.exists(old_folder):
            try:
                os.rename(old_folder, new_folder)
                physical_renamed = True
            except OSError as e:
                logger.error(f"Failed to rename state folder: {e}")
                return False
                
        try:
            state.name = new_name
            for district in state.districts:
                for m in district.maps:
                    m.relative_path = m.relative_path.replace(f"maps/{country_name}/{old_name}/", f"maps/{country_name}/{new_name}/", 1)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            if physical_renamed:
                os.rename(new_folder, old_folder)
            return False

    def rename_district(self, district: District, new_name: str) -> bool:
        country_name = district.state.country.name
        state_name = district.state.name
        old_name = district.name
        old_folder = os.path.join(get_maps_dir(), country_name, state_name, old_name)
        new_folder = os.path.join(get_maps_dir(), country_name, state_name, new_name)
        
        physical_renamed = False
        if os.path.exists(old_folder):
            try:
                os.rename(old_folder, new_folder)
                physical_renamed = True
            except OSError as e:
                logger.error(f"Failed to rename district folder: {e}")
                return False
                
        try:
            district.name = new_name
            for m in district.maps:
                m.relative_path = m.relative_path.replace(f"maps/{country_name}/{state_name}/{old_name}/", f"maps/{country_name}/{state_name}/{new_name}/", 1)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            if physical_renamed:
                os.rename(new_folder, old_folder)
            return False

    def create_district_folder(self, district: District):
        path = self.get_district_folder_path(district.id)
        os.makedirs(path, exist_ok=True)
        return path

    def move_map(self, map_obj: Map, target_district: District) -> bool:
        old_abs_path = get_absolute_path(map_obj.relative_path)
        new_folder = self.get_district_folder_path(target_district.id)
        os.makedirs(new_folder, exist_ok=True)
        
        filename = os.path.basename(old_abs_path)
        new_abs_path = os.path.join(new_folder, filename)
        
        physical_moved = False
        if os.path.exists(old_abs_path):
            try:
                shutil.move(old_abs_path, new_abs_path)
                physical_moved = True
            except OSError as e:
                logger.error(f"Failed to move map file: {e}")
                return False
                
        try:
            map_obj.district_id = target_district.id
            map_obj.relative_path = get_relative_path(new_abs_path)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            if physical_moved:
                shutil.move(new_abs_path, old_abs_path)
            return False

    def delete_map(self, map_obj: Map) -> bool:
        abs_path = get_absolute_path(map_obj.relative_path)
        thumb_path = get_absolute_path(map_obj.thumbnail_path)
        
        try:
            self.session.delete(map_obj)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Database delete failed: {e}")
            return False
            
        # Physical delete
        if abs_path and os.path.exists(abs_path):
            os.remove(abs_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        return True

    def add_country(self, name: str) -> bool:
        if self.session.query(Country).filter_by(name=name).first():
            return False
        country = Country(name=name)
        self.session.add(country)
        self.session.commit()
        os.makedirs(os.path.join(get_maps_dir(), name), exist_ok=True)
        return True
        
    def add_state(self, country_id: int, name: str) -> bool:
        country = self.session.query(Country).get(country_id)
        if not country or self.session.query(State).filter_by(country_id=country_id, name=name).first():
            return False
        state = State(country_id=country_id, name=name)
        self.session.add(state)
        self.session.commit()
        os.makedirs(os.path.join(get_maps_dir(), country.name, name), exist_ok=True)
        return True
        
    def add_district(self, state_id: int, name: str) -> bool:
        state = self.session.query(State).get(state_id)
        if not state or self.session.query(District).filter_by(state_id=state_id, name=name).first():
            return False
        district = District(state_id=state_id, name=name)
        self.session.add(district)
        self.session.commit()
        os.makedirs(os.path.join(get_maps_dir(), state.country.name, state.name, name), exist_ok=True)
        return True

    def delete_country(self, country_id: int) -> tuple[bool, str]:
        country = self.session.query(Country).get(country_id)
        if not country:
            return False, "Country not found."
        if country.states:
            return False, "Cannot delete country because it contains states. Delete them first."
            
        path = os.path.join(get_maps_dir(), country.name)
        try:
            self.session.delete(country)
            self.session.commit()
            if os.path.exists(path):
                os.rmdir(path)
            return True, ""
        except Exception as e:
            self.session.rollback()
            return False, f"Database error: {e}"

    def delete_state(self, state_id: int) -> tuple[bool, str]:
        state = self.session.query(State).get(state_id)
        if not state:
            return False, "State not found."
        if state.districts:
            return False, "Cannot delete state because it contains districts. Delete them first."
            
        path = os.path.join(get_maps_dir(), state.country.name, state.name)
        try:
            self.session.delete(state)
            self.session.commit()
            if os.path.exists(path):
                os.rmdir(path)
            return True, ""
        except Exception as e:
            self.session.rollback()
            return False, f"Database error: {e}"

    def delete_district(self, district_id: int) -> tuple[bool, str]:
        district = self.session.query(District).get(district_id)
        if not district:
            return False, "District not found."
        if district.maps:
            return False, "Cannot delete district because it contains maps. Delete them first."
            
        path = os.path.join(get_maps_dir(), district.state.country.name, district.state.name, district.name)
        try:
            self.session.delete(district)
            self.session.commit()
            if os.path.exists(path):
                os.rmdir(path)
            return True, ""
        except Exception as e:
            self.session.rollback()
            return False, f"Database error: {e}"

    def sync_from_filesystem(self) -> int:
        from src.services.thumbnail_service import ThumbnailService
        thumb_service = ThumbnailService()
        
        maps_dir = get_maps_dir()
        if not os.path.exists(maps_dir):
            return 0
            
        items_added = 0
        
        for c_name in os.listdir(maps_dir):
            c_path = os.path.join(maps_dir, c_name)
            if not os.path.isdir(c_path) or c_name.startswith('.'):
                continue
                
            country = self.session.query(Country).filter_by(name=c_name).first()
            if not country:
                country = Country(name=c_name)
                self.session.add(country)
                self.session.commit()
                items_added += 1
                
            for s_name in os.listdir(c_path):
                s_path = os.path.join(c_path, s_name)
                if not os.path.isdir(s_path) or s_name.startswith('.'):
                    continue
                    
                state = self.session.query(State).filter_by(country_id=country.id, name=s_name).first()
                if not state:
                    state = State(country_id=country.id, name=s_name)
                    self.session.add(state)
                    self.session.commit()
                    items_added += 1
                    
                for d_name in os.listdir(s_path):
                    d_path = os.path.join(s_path, d_name)
                    if not os.path.isdir(d_path) or d_name.startswith('.'):
                        continue
                        
                    district = self.session.query(District).filter_by(state_id=state.id, name=d_name).first()
                    if not district:
                        district = District(state_id=state.id, name=d_name)
                        self.session.add(district)
                        self.session.commit()
                        items_added += 1
                        
                    for f_name in os.listdir(d_path):
                        f_path = os.path.join(d_path, f_name)
                        if not os.path.isfile(f_path) or f_name.startswith('.'):
                            continue
                        
                        ext = os.path.splitext(f_name)[1].lower()
                        if ext not in ['.jpg', '.jpeg', '.png', '.bmp']:
                            continue
                            
                        rel_path = get_relative_path(f_path)
                        map_obj = self.session.query(Map).filter_by(relative_path=rel_path).first()
                        if not map_obj:
                            map_obj = Map(district_id=district.id, name=f_name, relative_path=rel_path)
                            self.session.add(map_obj)
                            self.session.commit()
                            
                            thumb_rel_path = thumb_service.generate_thumbnail(f_path, map_obj.id)
                            map_obj.thumbnail_path = thumb_rel_path
                            self.session.commit()
                            items_added += 1
                            
        return items_added
