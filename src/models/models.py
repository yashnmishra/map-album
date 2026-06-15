from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Text
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

map_tag_association = Table(
    'map_tags',
    Base.metadata,
    Column('map_id', Integer, ForeignKey('maps.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Country(Base):
    __tablename__ = 'countries'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    
    states: Mapped[List["State"]] = relationship(back_populates="country", cascade="all, delete-orphan")

class State(Base):
    __tablename__ = 'states'
    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.id'))
    name: Mapped[str] = mapped_column(String(100))
    
    country: Mapped["Country"] = relationship(back_populates="states")
    districts: Mapped[List["District"]] = relationship(back_populates="state", cascade="all, delete-orphan")

class District(Base):
    __tablename__ = 'districts'
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey('states.id'))
    name: Mapped[str] = mapped_column(String(100))
    
    state: Mapped["State"] = relationship(back_populates="districts")
    maps: Mapped[List["Map"]] = relationship(back_populates="district", cascade="all, delete-orphan")

class Map(Base):
    __tablename__ = 'maps'
    id: Mapped[int] = mapped_column(primary_key=True)
    district_id: Mapped[int] = mapped_column(ForeignKey('districts.id'))
    name: Mapped[str] = mapped_column(String(200))
    relative_path: Mapped[str] = mapped_column(String(500))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    has_tiles: Mapped[bool] = mapped_column(default=False)
    tile_dir_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    district: Mapped["District"] = relationship(back_populates="maps")
    tags: Mapped[List["Tag"]] = relationship(secondary=map_tag_association, back_populates="maps")
    metadata_values: Mapped[List["MapMetadata"]] = relationship(back_populates="map_obj", cascade="all, delete-orphan")

class Tag(Base):
    __tablename__ = 'tags'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    
    maps: Mapped[List["Map"]] = relationship(secondary=map_tag_association, back_populates="tags")

class CustomField(Base):
    __tablename__ = 'custom_fields'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50)) # Text, Number, Date, Dropdown, Multi-Select
    
    options: Mapped[List["CustomFieldOption"]] = relationship(back_populates="field", cascade="all, delete-orphan")
    metadata_values: Mapped[List["MapMetadata"]] = relationship(back_populates="field", cascade="all, delete-orphan")

class CustomFieldOption(Base):
    __tablename__ = 'custom_field_options'
    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey('custom_fields.id'))
    value: Mapped[str] = mapped_column(String(200))
    
    field: Mapped["CustomField"] = relationship(back_populates="options")

class MapMetadata(Base):
    __tablename__ = 'map_metadata'
    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[int] = mapped_column(ForeignKey('maps.id'))
    field_id: Mapped[int] = mapped_column(ForeignKey('custom_fields.id'))
    value: Mapped[str] = mapped_column(Text)
    
    map_obj: Mapped["Map"] = relationship(back_populates="metadata_values")
    field: Mapped["CustomField"] = relationship(back_populates="metadata_values")

class SavedFilter(Base):
    __tablename__ = 'saved_filters'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    filter_json: Mapped[str] = mapped_column(Text) # JSON encoded filter definition
