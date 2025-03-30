from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base

class Part(Base):
    """Modèle pour les pièces détachées"""
    __tablename__ = 'parts'
    
    id = Column(Integer, primary_key=True)
    reference = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    availabilities = relationship("Availability", back_populates="part", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Part(id={self.id}, reference='{self.reference}', name='{self.name}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Supplier(Base):
    """Modèle pour les fournisseurs (sites sources)"""
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    website = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    availabilities = relationship("Availability", back_populates="supplier", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'website': self.website,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Availability(Base):
    """Modèle pour la disponibilité et les prix des pièces chez les fournisseurs"""
    __tablename__ = 'availability'
    
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    price = Column(Float, nullable=True)
    in_stock = Column(Boolean, default=False)
    url = Column(String(500), nullable=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    part = relationship("Part", back_populates="availabilities")
    supplier = relationship("Supplier", back_populates="availabilities")
    
    # Index composé pour optimiser les recherches
    __table_args__ = (
        Index('idx_part_supplier', 'part_id', 'supplier_id', unique=True),
    )
    
    def __repr__(self):
        return f"<Availability(part_id={self.part_id}, supplier_id={self.supplier_id}, in_stock={self.in_stock})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'part_id': self.part_id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'price': self.price,
            'in_stock': self.in_stock,
            'url': self.url,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None
        }


class ApiKey(Base):
    """Modèle pour les clés API"""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', active={self.active})>"
