import os
import logging
import pandas as pd
from typing import List
from src.models.models import Map
from src.utils.paths import get_absolute_path

logger = logging.getLogger(__name__)

class ExportService:
    def export_maps(self, maps: List[Map], file_path: str, format_type: str) -> bool:
        """Export maps to CSV, Excel, or JSON."""
        try:
            data = []
            for m in maps:
                row = {
                    "Map Name": m.name,
                    "Country": m.district.state.country.name if m.district and m.district.state else "",
                    "State": m.district.state.name if m.district and m.district.state else "",
                    "District": m.district.name if m.district else "",
                    "Tags": ", ".join([t.name for t in m.tags]),
                    "Notes": m.notes or "",
                    "Relative File Path": m.relative_path,
                }
                
                # Add metadata columns
                for md in m.metadata_values:
                    row[md.field.name] = md.value
                    
                data.append(row)
                
            df = pd.DataFrame(data)
            
            if format_type == 'csv':
                df.to_csv(file_path, index=False)
            elif format_type == 'xlsx':
                df.to_excel(file_path, index=False)
            elif format_type == 'json':
                df.to_json(file_path, orient='records', indent=4)
            else:
                logger.error(f"Unsupported format type: {format_type}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error exporting maps: {e}")
            return False
