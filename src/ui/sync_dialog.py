import os
import time
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from src.services.folder_sync_service import FolderSyncService
from src.services.cache_service import CacheService, CacheMetrics
from src.models.models import Country, State, District, Map
from src.utils.paths import get_maps_dir, get_relative_path

class SyncWorker(QThread):
    progress_updated = Signal(dict)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.cache_service = CacheService()
        self._is_running = True

    def run(self):
        try:
            maps_dir = get_maps_dir()
            if not os.path.exists(maps_dir):
                self.finished.emit(0)
                return

            # Pre-scan to count total files for progress bar
            total_files = 0
            file_list = []
            
            for c_name in os.listdir(maps_dir):
                c_path = os.path.join(maps_dir, c_name)
                if not os.path.isdir(c_path) or c_name.startswith('.'): continue
                for s_name in os.listdir(c_path):
                    s_path = os.path.join(c_path, s_name)
                    if not os.path.isdir(s_path) or s_name.startswith('.'): continue
                    for d_name in os.listdir(s_path):
                        d_path = os.path.join(s_path, d_name)
                        if not os.path.isdir(d_path) or d_name.startswith('.'): continue
                        for f_name in os.listdir(d_path):
                            f_path = os.path.join(d_path, f_name)
                            if not os.path.isfile(f_path) or f_name.startswith('.'): continue
                            ext = os.path.splitext(f_name)[1].lower()
                            if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                                total_files += 1
                                file_list.append((c_name, s_name, d_name, f_name, f_path))

            if total_files == 0:
                self.finished.emit(0)
                return

            items_added = 0
            processed = 0
            start_time = time.time()
            metrics = CacheMetrics()
            metrics.total_files = total_files

            # Actually process
            for c_name, s_name, d_name, f_name, f_path in file_list:
                if not self._is_running:
                    break
                    
                self.emit_progress(processed, total_files, f"Processing: {f_name}", start_time, metrics)
                
                # DB Creation logic
                country = self.session.query(Country).filter_by(name=c_name).first()
                if not country:
                    country = Country(name=c_name)
                    self.session.add(country)
                    self.session.commit()
                    
                state = self.session.query(State).filter_by(country_id=country.id, name=s_name).first()
                if not state:
                    state = State(country_id=country.id, name=s_name)
                    self.session.add(state)
                    self.session.commit()
                    
                district = self.session.query(District).filter_by(state_id=state.id, name=d_name).first()
                if not district:
                    district = District(state_id=state.id, name=d_name)
                    self.session.add(district)
                    self.session.commit()

                rel_path = get_relative_path(f_path)
                map_obj = self.session.query(Map).filter_by(relative_path=rel_path).first()
                
                if not map_obj:
                    # New Map!
                    map_obj = Map(district_id=district.id, name=f_name, relative_path=rel_path)
                    self.session.add(map_obj)
                    self.session.commit()
                    
                    self.emit_progress(processed, total_files, f"Generating Cache: {f_name}", start_time, metrics)
                    cache_result = self.cache_service.generate_cache(f_path, map_obj.id)
                    
                    if cache_result:
                        map_obj.thumbnail_path = cache_result.get('thumbnail_path')
                        map_obj.preview_path = cache_result.get('preview_path')
                        map_obj.has_tiles = cache_result.get('has_tiles', False)
                        map_obj.tile_dir_path = cache_result.get('tile_dir_path')
                        
                        metrics.thumbnails_generated += 1
                        metrics.previews_generated += 1
                        metrics.tiles_generated += cache_result.get('tiles_generated', 0)
                        
                    self.session.commit()
                    items_added += 1
                
                processed += 1
                metrics.processed_files = processed

            self.finished.emit(items_added)

        except Exception as e:
            self.error.emit(str(e))

    def emit_progress(self, processed, total, status, start_time, metrics):
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / speed if speed > 0 else 0
        
        self.progress_updated.emit({
            'processed': processed,
            'total': total,
            'status': status,
            'elapsed': elapsed,
            'eta': eta,
            'speed': speed * 60, # files per min
            'metrics': metrics
        })

    def cancel(self):
        self._is_running = False

class SyncProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filesystem Synchronization")
        self.setFixedSize(450, 300)
        
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Scanning directory...")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.lbl_stats = QLabel("Time Elapsed: 0s | ETA: Calc...")
        layout.addWidget(self.lbl_stats)
        
        self.lbl_metrics = QLabel("Thumbnails: 0 | Previews: 0 | Tiles: 0")
        layout.addWidget(self.lbl_metrics)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_sync)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def set_worker(self, worker):
        self.worker = worker
        self.worker.progress_updated.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

    def on_progress(self, data):
        proc = data['processed']
        tot = data['total']
        if tot > 0:
            self.progress_bar.setMaximum(tot)
            self.progress_bar.setValue(proc)
            
        self.lbl_status.setText(data['status'])
        
        mins, secs = divmod(int(data['elapsed']), 60)
        eta_mins, eta_secs = divmod(int(data['eta']), 60)
        
        self.lbl_stats.setText(f"Elapsed: {mins}m {secs}s | ETA: {eta_mins}m {eta_secs}s | Speed: {int(data['speed'])} files/min")
        
        m = data['metrics']
        self.lbl_metrics.setText(f"Thumbnails: {m.thumbnails_generated} | Previews: {m.previews_generated} | Tiles: {m.tiles_generated}")

    def on_finished(self, items_added):
        QMessageBox.information(self, "Sync Complete", f"Successfully synced filesystem. {items_added} new items added.")
        self.accept()

    def on_error(self, error_msg):
        QMessageBox.critical(self, "Error", f"An error occurred during sync:\n{error_msg}")
        self.reject()

    def cancel_sync(self):
        if hasattr(self, 'worker'):
            self.worker.cancel()
        self.reject()
