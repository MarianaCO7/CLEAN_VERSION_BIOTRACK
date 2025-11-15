#!/usr/bin/env python3
"""
🗄️ DATABASE MANAGER - GESTOR DE BASE DE DATOS CON SQLAlchemy
==============================================================
Módulo de gestión de base de datos para BIOTRACK usando SQLAlchemy ORM.
Se conecta a la base de datos existente en database/biotrack.db

CARACTERÍSTICAS:
- SQLAlchemy ORM con modelos para todas las tablas
- Métodos CRUD para User, Subject, ROMSession, AngleMeasurement, SystemLog
- Autenticación de usuarios con Werkzeug
- Consultas específicas del negocio educativo
- Context managers para conexiones seguras
- Sin columna weight en Subject (solo height)

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, CheckConstraint, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from werkzeug.security import check_password_hash, generate_password_hash

# ============================================================================
# BASE DE DATOS Y ENGINE
# ============================================================================

Base = declarative_base()


# ============================================================================
# MODELOS ORM (Mapeo de Tablas Existentes)
# ============================================================================

class User(Base):
    """
    Modelo de Usuario (Administradores y Estudiantes)
    Tabla: user
    """
    __tablename__ = 'user'
    
    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Información Personal
    full_name = Column(String(150), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    
    # Información Académica
    role = Column(String(20), nullable=False, default='student')
    student_id = Column(String(50))
    program = Column(String(100))
    semester = Column(Integer)
    
    # Datos Antropométricos (Drillis & Contini)
    height = Column(Float)  # Altura en cm (necesaria para cálculos)
    
    # Estado y Auditoría
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey('user.id'))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relaciones
    subjects = relationship('Subject', back_populates='creator', foreign_keys='Subject.created_by')
    rom_sessions = relationship('ROMSession', back_populates='user', foreign_keys='ROMSession.user_id')
    system_logs = relationship('SystemLog', back_populates='user', foreign_keys='SystemLog.user_id')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'student')", name='check_role'),
        CheckConstraint("is_active IN (0, 1)", name='check_is_active'),
        CheckConstraint("semester IS NULL OR (semester >= 1 AND semester <= 12)", name='check_semester'),
        CheckConstraint("height IS NULL OR (height >= 50 AND height <= 250)", name='check_height'),
    )
    
    def set_password(self, password: str):
        """Establece el hash de la contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> dict:
        """Convierte el usuario a diccionario"""
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'student_id': self.student_id,
            'program': self.program,
            'semester': self.semester,
            'height': self.height,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Subject(Base):
    """
    Modelo de Sujeto de Estudio
    Tabla: subject
    NOTA: Sin columna weight (solo height)
    """
    __tablename__ = 'subject'
    
    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_code = Column(String(50), unique=True, nullable=False)
    
    # Información Personal
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime)
    gender = Column(String(10))
    
    # Información Física (SIN weight)
    height = Column(Float)  # Solo altura en cm
    
    # Información Adicional
    activity_level = Column(String(50))
    notes = Column(Text)
    
    # Auditoría
    created_by = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    creator = relationship('User', back_populates='subjects', foreign_keys=[created_by])
    rom_sessions = relationship('ROMSession', back_populates='subject', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F', 'Other') OR gender IS NULL", name='check_gender'),
        CheckConstraint("height IS NULL OR (height >= 50 AND height <= 250)", name='check_subject_height'),
        CheckConstraint("activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active') OR activity_level IS NULL", name='check_activity_level'),
    )
    
    @property
    def full_name(self) -> str:
        """Nombre completo del sujeto"""
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        """Convierte el sujeto a diccionario"""
        return {
            'id': self.id,
            'subject_code': self.subject_code,
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'height': self.height,
            'activity_level': self.activity_level,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<Subject(id={self.id}, code='{self.subject_code}', name='{self.full_name}')>"


class ROMSession(Base):
    """
    Modelo de Sesión de Análisis ROM
    Tabla: rom_session
    """
    __tablename__ = 'rom_session'
    
    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relaciones
    subject_id = Column(Integer, ForeignKey('subject.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Configuración del Análisis
    segment = Column(String(50), nullable=False)
    exercise_type = Column(String(50), nullable=False)
    camera_view = Column(String(20))
    side = Column(String(20))
    
    # Resultados del Análisis
    max_angle = Column(Float)
    min_angle = Column(Float)
    rom_value = Column(Float)
    repetitions = Column(Integer, default=0)
    duration = Column(Float)
    quality_score = Column(Float)
    
    # Información Adicional
    notes = Column(Text)
    video_path = Column(String(500))
    
    # Auditoría
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    subject = relationship('Subject', back_populates='rom_sessions')
    user = relationship('User', back_populates='rom_sessions', foreign_keys=[user_id])
    angle_measurements = relationship('AngleMeasurement', back_populates='session', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("segment IN ('ankle', 'knee', 'hip', 'shoulder', 'elbow')", name='check_segment'),
        CheckConstraint("camera_view IN ('lateral', 'frontal', 'posterior') OR camera_view IS NULL", name='check_camera_view'),
        CheckConstraint("side IN ('left', 'right', 'bilateral') OR side IS NULL", name='check_side'),
        CheckConstraint("max_angle IS NULL OR (max_angle >= 0 AND max_angle <= 360)", name='check_max_angle'),
        CheckConstraint("min_angle IS NULL OR (min_angle >= 0 AND min_angle <= 360)", name='check_min_angle'),
        CheckConstraint("rom_value IS NULL OR (rom_value >= 0 AND rom_value <= 360)", name='check_rom_value'),
        CheckConstraint("quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)", name='check_quality_score'),
    )
    
    def to_dict(self) -> dict:
        """Convierte la sesión a diccionario"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'user_id': self.user_id,
            'segment': self.segment,
            'exercise_type': self.exercise_type,
            'camera_view': self.camera_view,
            'side': self.side,
            'max_angle': self.max_angle,
            'min_angle': self.min_angle,
            'rom_value': self.rom_value,
            'repetitions': self.repetitions,
            'duration': self.duration,
            'quality_score': self.quality_score,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<ROMSession(id={self.id}, segment='{self.segment}', rom={self.rom_value})>"


class AngleMeasurement(Base):
    """
    Modelo de Medición de Ángulo Frame-by-Frame
    Tabla: angle_measurement
    """
    __tablename__ = 'angle_measurement'
    
    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('rom_session.id'), nullable=False)
    
    # Datos de la Medición
    timestamp = Column(Float, nullable=False)
    frame_number = Column(Integer, nullable=False)
    angle_value = Column(Float, nullable=False)
    confidence = Column(Float)
    landmarks_json = Column(Text)
    
    # Relaciones
    session = relationship('ROMSession', back_populates='angle_measurements')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("angle_value >= 0 AND angle_value <= 360", name='check_angle_value'),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name='check_confidence'),
    )
    
    def to_dict(self) -> dict:
        """Convierte la medición a diccionario"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'timestamp': self.timestamp,
            'frame_number': self.frame_number,
            'angle_value': self.angle_value,
            'confidence': self.confidence
        }
    
    def __repr__(self):
        return f"<AngleMeasurement(id={self.id}, frame={self.frame_number}, angle={self.angle_value})>"


class SystemLog(Base):
    """
    Modelo de Log del Sistema
    Tabla: system_log
    """
    __tablename__ = 'system_log'
    
    # Identificación
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Información del Evento
    user_id = Column(Integer, ForeignKey('user.id'))
    action = Column(String(100), nullable=False)
    details = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    user = relationship('User', back_populates='system_logs', foreign_keys=[user_id])
    
    def to_dict(self) -> dict:
        """Convierte el log a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, action='{self.action}')>"


# ============================================================================
# DATABASE MANAGER CLASS
# ============================================================================

class DatabaseManager:
    """
    Gestor de Base de Datos con SQLAlchemy
    
    Proporciona métodos para:
    - Conexión a la BD existente
    - Operaciones CRUD para todas las tablas
    - Autenticación de usuarios
    - Consultas específicas del negocio
    - Context managers para sesiones seguras
    """
    
    def __init__(self, db_path: str = 'database/biotrack.db'):
        """
        Inicializa el gestor de base de datos
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        
        # Verificar que la BD existe
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {db_path}")
        
        # Crear engine
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        
        # Crear sesión
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager para sesiones de BD
        
        Uso:
            with db_manager.get_session() as session:
                user = session.query(User).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ========================================================================
    # MÉTODOS DE AUTENTICACIÓN
    # ========================================================================
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """
        Autentica un usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            Diccionario con datos del usuario si las credenciales son correctas, None en caso contrario
        """
        with self.get_session() as session:
            user = session.query(User).filter_by(username=username).first()
            
            if user and user.check_password(password):
                # Actualizar last_login
                user.last_login = datetime.utcnow()
                session.commit()
                
                # Retornar datos del usuario como diccionario para evitar DetachedInstanceError
                return {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                    'email': user.email,
                    'is_active': user.is_active
                }
            
            return None
    
    def update_last_login(self, user_id: int):
        """Actualiza la fecha de último login"""
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                session.commit()
    
    # ========================================================================
    # MÉTODOS CRUD - USER
    # ========================================================================
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene un usuario por ID"""
        with self.get_session() as session:
            return session.query(User).filter_by(id=user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por username"""
        with self.get_session() as session:
            return session.query(User).filter_by(username=username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        with self.get_session() as session:
            return session.query(User).filter_by(email=email).first()
    
    def create_user(self, username: str, password: str, full_name: str, email: str,
                   role: str = 'student', **kwargs) -> User:
        """
        Crea un nuevo usuario
        
        Args:
            username: Nombre de usuario único
            password: Contraseña (se hasheará)
            full_name: Nombre completo
            email: Email único
            role: 'admin' o 'student'
            **kwargs: Campos opcionales (student_id, program, semester, height, created_by)
        
        Returns:
            Usuario creado
        """
        with self.get_session() as session:
            user = User(
                username=username,
                full_name=full_name,
                email=email,
                role=role,
                **kwargs
            )
            user.set_password(password)
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            return user
    
    def get_all_users(self, role: Optional[str] = None, active_only: bool = True) -> List[User]:
        """
        Obtiene todos los usuarios
        
        Args:
            role: Filtrar por rol ('admin', 'student', None para todos)
            active_only: Solo usuarios activos
        
        Returns:
            Lista de usuarios
        """
        with self.get_session() as session:
            query = session.query(User)
            
            if role:
                query = query.filter_by(role=role)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            return query.all()
    
    def get_students(self, active_only: bool = True) -> List[User]:
        """Obtiene todos los estudiantes"""
        return self.get_all_users(role='student', active_only=active_only)
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Actualiza un usuario"""
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                
                session.commit()
                session.refresh(user)
            
            return user
    
    def delete_user(self, user_id: int) -> bool:
        """Elimina (desactiva) un usuario"""
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if user:
                user.is_active = False
                session.commit()
                return True
            
            return False
    
    # ========================================================================
    # MÉTODOS CRUD - SUBJECT
    # ========================================================================
    
    def create_subject(self, subject_code: str, first_name: str, last_name: str,
                      created_by: int, **kwargs) -> Subject:
        """
        Crea un nuevo sujeto de estudio
        
        Args:
            subject_code: Código único (ej: SUJ-2024-0001)
            first_name: Nombre
            last_name: Apellido
            created_by: ID del usuario que crea el sujeto
            **kwargs: Campos opcionales (date_of_birth, gender, height, activity_level, notes)
        
        Returns:
            Sujeto creado
        """
        with self.get_session() as session:
            subject = Subject(
                subject_code=subject_code,
                first_name=first_name,
                last_name=last_name,
                created_by=created_by,
                **kwargs
            )
            
            session.add(subject)
            session.commit()
            session.refresh(subject)
            
            return subject
    
    def get_subject_by_id(self, subject_id: int) -> Optional[Subject]:
        """Obtiene un sujeto por ID"""
        with self.get_session() as session:
            return session.query(Subject).filter_by(id=subject_id).first()
    
    def get_subject_by_code(self, subject_code: str) -> Optional[Subject]:
        """Obtiene un sujeto por código"""
        with self.get_session() as session:
            return session.query(Subject).filter_by(subject_code=subject_code).first()
    
    def get_subjects_by_user(self, user_id: int) -> List[Subject]:
        """Obtiene todos los sujetos creados por un usuario"""
        with self.get_session() as session:
            return session.query(Subject).filter_by(created_by=user_id).all()
    
    def get_all_subjects(self) -> List[Subject]:
        """Obtiene todos los sujetos"""
        with self.get_session() as session:
            return session.query(Subject).all()
    
    def update_subject(self, subject_id: int, **kwargs) -> Optional[Subject]:
        """Actualiza un sujeto"""
        with self.get_session() as session:
            subject = session.query(Subject).filter_by(id=subject_id).first()
            
            if subject:
                for key, value in kwargs.items():
                    if hasattr(subject, key):
                        setattr(subject, key, value)
                
                subject.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(subject)
            
            return subject
    
    def delete_subject(self, subject_id: int) -> bool:
        """Elimina un sujeto (y sus sesiones en cascada)"""
        with self.get_session() as session:
            subject = session.query(Subject).filter_by(id=subject_id).first()
            
            if subject:
                session.delete(subject)
                session.commit()
                return True
            
            return False
    
    # ========================================================================
    # MÉTODOS CRUD - ROM SESSION
    # ========================================================================
    
    def create_rom_session(self, subject_id: int, user_id: int, segment: str,
                          exercise_type: str, **kwargs) -> ROMSession:
        """
        Crea una nueva sesión de análisis ROM
        
        Args:
            subject_id: ID del sujeto analizado
            user_id: ID del estudiante que realiza el análisis
            segment: Segmento corporal ('ankle', 'knee', 'hip', 'shoulder', 'elbow')
            exercise_type: Tipo de movimiento
            **kwargs: Campos opcionales (camera_view, side, max_angle, etc.)
        
        Returns:
            Sesión ROM creada
        """
        with self.get_session() as session:
            rom_session = ROMSession(
                subject_id=subject_id,
                user_id=user_id,
                segment=segment,
                exercise_type=exercise_type,
                **kwargs
            )
            
            session.add(rom_session)
            session.commit()
            session.refresh(rom_session)
            
            return rom_session
    
    def get_rom_session_by_id(self, session_id: int) -> Optional[ROMSession]:
        """Obtiene una sesión ROM por ID"""
        with self.get_session() as session:
            return session.query(ROMSession).filter_by(id=session_id).first()
    
    def get_sessions_by_user(self, user_id: int) -> List[ROMSession]:
        """Obtiene todas las sesiones de un usuario"""
        with self.get_session() as session:
            return session.query(ROMSession).filter_by(user_id=user_id).order_by(ROMSession.created_at.desc()).all()
    
    def get_sessions_by_subject(self, subject_id: int) -> List[ROMSession]:
        """Obtiene todas las sesiones de un sujeto"""
        with self.get_session() as session:
            return session.query(ROMSession).filter_by(subject_id=subject_id).order_by(ROMSession.created_at.desc()).all()
    
    def get_sessions_by_segment(self, segment: str) -> List[ROMSession]:
        """Obtiene sesiones por segmento corporal"""
        with self.get_session() as session:
            return session.query(ROMSession).filter_by(segment=segment).all()
    
    def update_rom_session(self, session_id: int, **kwargs) -> Optional[ROMSession]:
        """Actualiza una sesión ROM"""
        with self.get_session() as session:
            rom_session = session.query(ROMSession).filter_by(id=session_id).first()
            
            if rom_session:
                for key, value in kwargs.items():
                    if hasattr(rom_session, key):
                        setattr(rom_session, key, value)
                
                session.commit()
                session.refresh(rom_session)
            
            return rom_session
    
    def delete_rom_session(self, session_id: int) -> bool:
        """Elimina una sesión ROM"""
        with self.get_session() as session:
            rom_session = session.query(ROMSession).filter_by(id=session_id).first()
            
            if rom_session:
                session.delete(rom_session)
                session.commit()
                return True
            
            return False
    
    # ========================================================================
    # MÉTODOS CRUD - ANGLE MEASUREMENT
    # ========================================================================
    
    def add_angle_measurement(self, session_id: int, timestamp: float, frame_number: int,
                             angle_value: float, confidence: Optional[float] = None,
                             landmarks_json: Optional[str] = None) -> AngleMeasurement:
        """Agrega una medición de ángulo a una sesión"""
        with self.get_session() as session:
            measurement = AngleMeasurement(
                session_id=session_id,
                timestamp=timestamp,
                frame_number=frame_number,
                angle_value=angle_value,
                confidence=confidence,
                landmarks_json=landmarks_json
            )
            
            session.add(measurement)
            session.commit()
            session.refresh(measurement)
            
            return measurement
    
    def get_measurements_by_session(self, session_id: int) -> List[AngleMeasurement]:
        """Obtiene todas las mediciones de una sesión"""
        with self.get_session() as session:
            return session.query(AngleMeasurement).filter_by(session_id=session_id).order_by(AngleMeasurement.frame_number).all()
    
    # ========================================================================
    # MÉTODOS CRUD - SYSTEM LOG
    # ========================================================================
    
    def log_action(self, action: str, user_id: Optional[int] = None,
                  details: Optional[str] = None, ip_address: Optional[str] = None) -> SystemLog:
        """
        Registra una acción en el sistema
        
        Args:
            action: Tipo de acción ('login', 'logout', 'create_subject', etc.)
            user_id: ID del usuario (None para eventos del sistema)
            details: Detalles adicionales
            ip_address: IP del cliente
        
        Returns:
            Log creado
        """
        with self.get_session() as session:
            log = SystemLog(
                action=action,
                user_id=user_id,
                details=details,
                ip_address=ip_address
            )
            
            session.add(log)
            session.commit()
            session.refresh(log)
            
            return log
    
    def get_logs_by_user(self, user_id: int, limit: int = 100) -> List[SystemLog]:
        """Obtiene los logs de un usuario"""
        with self.get_session() as session:
            return session.query(SystemLog).filter_by(user_id=user_id).order_by(SystemLog.timestamp.desc()).limit(limit).all()
    
    def get_recent_logs(self, limit: int = 100) -> List[SystemLog]:
        """Obtiene los logs más recientes del sistema"""
        with self.get_session() as session:
            return session.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(limit).all()
    
    # ========================================================================
    # MÉTODOS ESTADÍSTICOS Y DE NEGOCIO
    # ========================================================================
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un usuario estudiante
        
        Returns:
            Diccionario con estadísticas (sujetos registrados, sesiones, avg quality, etc.)
        """
        with self.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return {}
            
            subjects_count = session.query(func.count(Subject.id)).filter_by(created_by=user_id).scalar()
            sessions_count = session.query(func.count(ROMSession.id)).filter_by(user_id=user_id).scalar()
            avg_quality = session.query(func.avg(ROMSession.quality_score)).filter_by(user_id=user_id).scalar()
            
            last_session = session.query(ROMSession).filter_by(user_id=user_id).order_by(ROMSession.created_at.desc()).first()
            
            return {
                'user_id': user_id,
                'full_name': user.full_name,
                'student_id': user.student_id,
                'program': user.program,
                'subjects_registered': subjects_count or 0,
                'sessions_performed': sessions_count or 0,
                'avg_quality_score': round(avg_quality, 2) if avg_quality else 0,
                'last_activity': last_session.created_at.isoformat() if last_session else None
            }
    
    def get_segment_statistics(self, segment: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un segmento corporal
        
        Args:
            segment: 'ankle', 'knee', 'hip', 'shoulder', 'elbow'
        
        Returns:
            Estadísticas del segmento
        """
        with self.get_session() as session:
            sessions = session.query(ROMSession).filter_by(segment=segment).filter(ROMSession.rom_value.isnot(None)).all()
            
            if not sessions:
                return {'segment': segment, 'total_sessions': 0}
            
            rom_values = [s.rom_value for s in sessions]
            
            return {
                'segment': segment,
                'total_sessions': len(sessions),
                'avg_rom': round(sum(rom_values) / len(rom_values), 2),
                'min_rom': min(rom_values),
                'max_rom': max(rom_values)
            }
    
    def search_subjects(self, query: str) -> List[Subject]:
        """
        Busca sujetos por nombre o código
        
        Args:
            query: Texto a buscar
        
        Returns:
            Lista de sujetos que coinciden
        """
        with self.get_session() as session:
            return session.query(Subject).filter(
                (Subject.first_name.like(f'%{query}%')) |
                (Subject.last_name.like(f'%{query}%')) |
                (Subject.subject_code.like(f'%{query}%'))
            ).all()
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def test_connection(self) -> bool:
        """Verifica la conexión a la base de datos"""
        try:
            with self.get_session() as session:
                session.query(User).first()
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Obtiene información general de la base de datos"""
        with self.get_session() as session:
            return {
                'total_users': session.query(func.count(User.id)).scalar(),
                'total_students': session.query(func.count(User.id)).filter_by(role='student').scalar(),
                'total_subjects': session.query(func.count(Subject.id)).scalar(),
                'total_sessions': session.query(func.count(ROMSession.id)).scalar(),
                'total_measurements': session.query(func.count(AngleMeasurement.id)).scalar(),
                'total_logs': session.query(func.count(SystemLog.id)).scalar()
            }


# ============================================================================
# SINGLETON INSTANCE (Opcional - para uso global)
# ============================================================================

# Instancia global del database manager (se puede importar en otros módulos)
# from database.database_manager import db_manager
# user = db_manager.get_user_by_id(1)

_db_manager_instance = None

def get_db_manager(db_path: str = 'database/biotrack.db') -> DatabaseManager:
    """Obtiene la instancia singleton del DatabaseManager"""
    global _db_manager_instance
    
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager(db_path)
    
    return _db_manager_instance


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == '__main__':
    # Inicializar database manager
    db_manager = DatabaseManager('database/biotrack.db')
    
    # Test de conexión
    if db_manager.test_connection():
        print("✅ Conexión a base de datos exitosa")
        
        # Obtener información
        info = db_manager.get_database_info()
        print(f"\n📊 Información de la Base de Datos:")
        print(f"   • Usuarios: {info['total_users']}")
        print(f"   • Estudiantes: {info['total_students']}")
        print(f"   • Sujetos: {info['total_subjects']}")
        print(f"   • Sesiones ROM: {info['total_sessions']}")
        print(f"   • Mediciones: {info['total_measurements']}")
        print(f"   • Logs: {info['total_logs']}")
        
        # Listar usuarios
        users = db_manager.get_all_users()
        print(f"\n👥 Usuarios en el sistema:")
        for user in users:
            print(f"   • {user.username} ({user.role}) - {user.full_name}")
    else:
        print("❌ Error de conexión a la base de datos")
