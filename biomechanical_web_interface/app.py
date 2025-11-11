"""
BIOMECH ANALYZER - SISTEMA DE ANÁLISIS BIOMECÁNICO WEB
Backend Flask que integra los analyzers existentes sin modificar el código original
"""

import os
import sys

# 🔧 CONFIGURACIÓN ENCODING PARA WINDOWS (Debe ir ANTES de cualquier print)
if sys.platform == 'win32':
    import codecs
    # Configurar stdout y stderr para UTF-8 (soporte de emojis en Windows)
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

import json
from datetime import datetime, timedelta
import pytz
import atexit
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect as sqla_inspect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3

# =============================================================================
# 🔧 CONFIGURACIÓN DE LOGGING (DEBE IR AL INICIO)
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ✅ CONFIGURACIÓN LOCAL - MediaPipe estándar
logger.info("💻 Modo local - MediaPipe configuración estándar")

# 🔄 FUNCIÓN DE MIGRACIÓN AUTOMÁTICA
def auto_migrate_database():
    """Ejecuta migración automática al iniciar la aplicación"""
    try:
        # Determinar la ruta de la base de datos (local)
        db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'biomech_system.db')
        
        # Crear directorio instance si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Conectar y verificar estructura
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si necesitamos migración
        cursor.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'date_of_birth' not in columns:
            print("🔄 Ejecutando migración automática...")
            
            # Agregar nuevas columnas
            new_columns = [
                ('email', 'VARCHAR(120)'),
                ('full_name', 'VARCHAR(200)'),
                ('date_of_birth', 'DATE'),
                ('status', 'VARCHAR(20) DEFAULT "active"'),
                ('phone', 'VARCHAR(20)'),
                ('emergency_contact', 'TEXT'),
                ('medical_notes', 'TEXT'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('created_by', 'INTEGER'),
                ('last_login', 'TIMESTAMP'),
                ('modified_at', 'TIMESTAMP'),
                ('modified_by', 'INTEGER')
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE user ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Columna '{column_name}' agregada")
                    except Exception as e:
                        print(f"⚠️ Error con '{column_name}': {e}")
            
            # Crear tabla de auditoría COMPLETA
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    changed_fields TEXT,
                    old_values TEXT,
                    new_values TEXT,
                    performed_by INTEGER,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (performed_by) REFERENCES user (id)
                )
            """)
            
            # Si la tabla ya existe pero faltan columnas, agregarlas
            cursor.execute("PRAGMA table_info(user_audit_log)")
            audit_columns = [row[1] for row in cursor.fetchall()]
            
            audit_new_columns = [
                ('changed_fields', 'TEXT'),
                ('old_values', 'TEXT'), 
                ('new_values', 'TEXT'),
                ('ip_address', 'VARCHAR(45)')
            ]
            
            for column_name, column_type in audit_new_columns:
                if column_name not in audit_columns:
                    try:
                        cursor.execute(f"ALTER TABLE user_audit_log ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Columna audit '{column_name}' agregada")
                    except Exception as e:
                        print(f"⚠️ Error con audit '{column_name}': {e}")
            
            conn.commit()
            print("✅ Migración automática completada")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Error en migración automática: {e}")

# ✅ CONFIGURAR PATHS PARA IMPORTS
# Obtener el directorio actual (biomechanical_web_interface)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Agregar el directorio padre para imports de biomechanical_analysis
parent_dir = os.path.join(current_dir, '..')
sys.path.insert(0, parent_dir)
# Agregar el directorio actual para imports relativos de handlers
sys.path.insert(0, current_dir)

print(f"📂 Current dir: {current_dir}")
print(f"📂 Parent dir: {parent_dir}")
print(f"📂 Python path configurado correctamente")

# Configuración de Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'biomech_analyzer_secret_key_2025')

# 📦 CONFIGURACIÓN DE TAMAÑO MÁXIMO (Railway optimization)
# Aumentar límite para frames base64 (evitar 400 Bad Request)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB (era 16 MB antes, reducido)

# Configuración de la base de datos
# En producción usar PostgreSQL si está disponible, sino SQLite
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Railway usa postgres:// pero SQLAlchemy necesita postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Desarrollo local con SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "..", "instance", "biomech_system.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de la base de datos
db = SQLAlchemy(app)

# =============================================================================
# 🎯 VARIABLES GLOBALES
# =============================================================================

# Variable global para rastrear handlers disponibles (se llena después de imports)
AVAILABLE_HANDLERS = {}

# 🔄 EJECUTAR MIGRACIÓN AUTOMÁTICA AL INICIALIZAR
auto_migrate_database()

# 💬 IMPORTAR FUNCIÓN DE COMENTARIOS MOTIVACIONALES
from handlers.rom_utils import get_motivational_comment

# 📄 IMPORTAR GENERADOR DE PDF
from utils.pdf_generator import BiomechanicalPDFGenerator

# 🎨 REGISTRAR FILTRO DE JINJA2 PARA TEMPLATES
@app.template_filter('motivational_comment')
def motivational_comment_filter(classification):
    """Filtro de Jinja2 para generar comentarios motivacionales"""
    return get_motivational_comment(classification)

# =============================================================================
# MODELOS DE BASE DE DATOS
# =============================================================================

class User(db.Model):
    """Modelo de usuario del sistema - EXTENDIDO para gestión completa"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student')  # admin, tech, student
    email = db.Column(db.String(120))
    full_name = db.Column(db.String(100))
    profile_image = db.Column(db.String(255))  # 🆕 Ruta de la imagen de perfil
    bio = db.Column(db.Text)  # 🆕 Biografía del usuario
    specialization = db.Column(db.String(50))  # 🆕 Especialización (Estudiante, Fisioterapeuta, etc.)
    
    # 🆕 CAMPOS BIOMECÁNICOS
    height_cm = db.Column(db.Float, default=170.0)  # Altura en centímetros
    date_of_birth = db.Column(db.Date)  # 🆕 Fecha de nacimiento
    
    # 🆕 CAMPOS DE GESTIÓN
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    phone = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(100))
    medical_notes = db.Column(db.Text)  # Notas médicas opcionales
    
    # 🆕 CAMPOS DE AUDITORÍA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin que lo creó
    last_login = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modified_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Último admin que modificó
    
    # Relaciones
    analyses = db.relationship('Analysis', backref='user', lazy=True)
    created_users = db.relationship('User', remote_side=[id], foreign_keys=[created_by], 
                                   backref='creator', lazy=True)
    modified_users = db.relationship('User', remote_side=[id], foreign_keys=[modified_by], 
                                    backref='modifier', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def height(self):
        """📏 Alias para height_cm (compatibilidad con código existente)"""
        return self.height_cm
    
    def get_shoulder_height(self):
        """📏 Calcular altura del hombro usando fórmula Drillis-Contini"""
        return round(self.height_cm * 0.818, 1)
    
    def get_camera_recommendations(self, joint_type):
        """📱 Obtener recomendaciones de posición de cámara"""
        if joint_type == 'shoulder':
            shoulder_height = self.get_shoulder_height()
            return {
                'height_cm': shoulder_height,
                'distance_cm': 150,  # 1.5 metros
                'position': 'lateral',  # De perfil para flexión
                'instructions': f'Coloca la cámara a {shoulder_height}cm del suelo, de perfil al ejercicio'
            }
        # Expandir para otros joints después
        return {'height_cm': 100, 'distance_cm': 150, 'position': 'frontal'}
    
    # 🆕 MÉTODOS DE GESTIÓN DE USUARIOS
    def get_age(self):
        """📅 Calcular edad del usuario"""
        if not self.date_of_birth:
            return None
        today = datetime.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def is_active(self):
        """✅ Verificar si el usuario está activo"""
        return self.status == 'active'
    
    def can_login(self):
        """🔐 Verificar si el usuario puede iniciar sesión"""
        return self.status in ['active']
    
    def deactivate(self, admin_id):
        """⏸️ Soft delete - desactivar usuario"""
        self.status = 'inactive'
        self.modified_by = admin_id
        self.modified_at = datetime.utcnow()
        
    def reactivate(self, admin_id):
        """▶️ Reactivar usuario desactivado"""
        self.status = 'active'
        self.modified_by = admin_id
        self.modified_at = datetime.utcnow()
        
    def to_dict(self, include_sensitive=False):
        """📊 Convertir usuario a diccionario para API"""
        data = {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'height_cm': self.height_cm,
            'age': self.get_age(),
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'total_analyses': len(self.analyses) if self.analyses else 0
        }
        
        if include_sensitive:
            data.update({
                'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
                'emergency_contact': self.emergency_contact,
                'medical_notes': self.medical_notes,
                'created_by': self.created_by,
                'modified_at': self.modified_at.isoformat() if self.modified_at else None,
                'modified_by': self.modified_by
            })
            
        return data

# 🆕 MODELO DE AUDITORÍA PARA TRAZABILIDAD
class UserAuditLog(db.Model):
    """Registro de auditoría para cambios en usuarios"""
    __tablename__ = 'user_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    changed_fields = db.Column(db.Text)  # JSON con campos modificados
    old_values = db.Column(db.Text)  # JSON con valores anteriores
    new_values = db.Column(db.Text)  # JSON con valores nuevos
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv4/IPv6
    
    # Relaciones
    target_user = db.relationship('User', foreign_keys=[user_id], backref='audit_logs')
    performer = db.relationship('User', foreign_keys=[performed_by], backref='performed_audits')

class Analysis(db.Model):
    """Modelo para almacenar análisis realizados"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joint_type = db.Column(db.String(20), nullable=False)  # neck, shoulder, elbow, hip, knee, ankle
    exercise_type = db.Column(db.String(20), nullable=False, default='flexion')  # flexion, abduction, rotation
    exercise_name = db.Column(db.String(100), nullable=False)
    
    # Datos del análisis básico
    current_angle = db.Column(db.Float, nullable=False)
    max_angle = db.Column(db.Float, default=0)
    min_angle = db.Column(db.Float, default=0)
    avg_angle = db.Column(db.Float, default=0)
    total_measurements = db.Column(db.Integer, default=1)
    
    # 🆕 CAMPOS ROM ESPECÍFICOS
    max_rom_achieved = db.Column(db.Float, default=0)  # ROM máximo alcanzado en la sesión
    max_rom_side = db.Column(db.String(10), default='ninguno')  # 🆕 Lado que alcanzó ROM máximo
    calibration_angle = db.Column(db.Float, default=0)  # Ángulo de calibración (posición anatómica)
    rom_classification = db.Column(db.String(20), default='unknown')  # excellent/good/needs_work/limited
    best_frame_data = db.Column(db.Text)  # Base64 de la imagen del mejor frame
    
    # Estado del análisis
    is_within_normal_range = db.Column(db.Boolean, default=False)
    quality_score = db.Column(db.Float, default=0)  # 0-100
    duration_seconds = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Datos adicionales en JSON
    analysis_metadata = db.Column(db.Text)  # JSON con datos extra
    
    def get_rom_classification_info(self):
        """📊 Obtener información detallada de clasificación ROM (español + hipermobilidad)"""
        classifications = {
            'hipermóvil': {'label': 'Hipermóvil', 'color': 'info', 'description': 'Supera rango normal (>150°)'},  # 🆕
            'óptimo': {'label': 'Óptimo', 'color': 'success', 'description': 'ROM completo (140-150°)'},
            'bueno': {'label': 'Bueno', 'color': 'primary', 'description': 'Rango funcional (130-139°)'},
            'necesita mejorar': {'label': 'Necesita mejorar', 'color': 'warning', 'description': 'Funcional mínimo (100-129°)'},
            'limitado': {'label': 'Limitado', 'color': 'danger', 'description': 'ROM restringido (<100°)'},
            'desconocido': {'label': 'Desconocido', 'color': 'secondary', 'description': 'Valor fuera del rango esperado - Verificar medición'},  # 🆕 Terminología clínica correcta
            # 🔄 BACKWARD COMPATIBILITY (inglés antiguo)
            'excellent': {'label': 'Óptimo', 'color': 'success', 'description': 'ROM completo'},
            'good': {'label': 'Bueno', 'color': 'primary', 'description': 'Rango funcional'},
            'needs_work': {'label': 'Necesita mejorar', 'color': 'warning', 'description': 'ROM limitado'},
            'limited': {'label': 'Limitado', 'color': 'danger', 'description': 'Consultar profesional'},
            'unknown': {'label': 'Sin clasificar', 'color': 'secondary', 'description': 'Datos insuficientes'}
        }
        return classifications.get(self.rom_classification, classifications['unknown'])
    
    def calculate_rom_percentage(self, exercise_config):
        """📊 Calcular porcentaje ROM respecto al rango normal"""
        if not exercise_config or self.max_rom_achieved <= 0:
            return 0
        normal_max = exercise_config.get('normal_range', {}).get('max', 180)
        return min(100, round((self.max_rom_achieved / normal_max) * 100, 1))

class AlturaReferencia(db.Model):
    """
    📏 Modelo para almacenar alturas de referencia según Drillis & Contini
    Almacena altura calculada de segmentos corporales por usuario
    """
    __tablename__ = 'altura_referencia'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    segmento = db.Column(db.String(20), nullable=False)  # shoulder, elbow, hip, knee, ankle
    altura_usuario_cm = db.Column(db.Float, nullable=False)  # Altura total del usuario
    altura_calculada_cm = db.Column(db.Float, nullable=False)  # Altura del segmento según Drillis-Contini
    porcentaje_drillis = db.Column(db.Float, nullable=False)  # % usado para cálculo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice único para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('user_id', 'segmento', name='_user_segmento_uc'),
    )
    
    @staticmethod
    def calcular_altura_segmento(altura_usuario_cm, segmento):
        """
        📐 Calcular altura de segmento según Drillis & Contini (1966)
        
        Fórmulas basadas en porcentajes de altura total:
        - Hombro (acromion): 81.8% H
        - Codo: 63.0% H
        - Muñeca: 48.5% H
        - Cadera (trocánter mayor): 53.0% H
        - Rodilla: 28.5% H
        - Tobillo (maléolo): 3.9% H
        
        Referencias:
        - Drillis, R., & Contini, R. (1966). Body Segment Parameters. 
          Tech. Rep. 1166-03, School of Engineering and Science, 
          New York University.
        """
        porcentajes = {
            'shoulder': 0.818,  # 81.8%
            'elbow': 0.630,     # 63.0%
            'wrist': 0.485,     # 48.5%
            'hip': 0.530,       # 53.0%
            'knee': 0.285,      # 28.5%
            'ankle': 0.039,     # 3.9%
            'neck': 0.870       # 87.0% (approx - altura ojos/cabeza)
        }
        
        porcentaje = porcentajes.get(segmento, 0.5)
        altura_calculada = altura_usuario_cm * porcentaje
        
        return {
            'altura_calculada_cm': round(altura_calculada, 1),
            'porcentaje': porcentaje,
            'formula': f'{porcentaje*100}% × {altura_usuario_cm} cm'
        }
    
    @staticmethod
    def obtener_o_crear(user_id, segmento):
        """
        Obtener altura de referencia existente o crear nueva
        """
        # ✅ NO usar import - User ya está definido en este archivo
        
        # Buscar registro existente
        altura_ref = AlturaReferencia.query.filter_by(
            user_id=user_id, 
            segmento=segmento
        ).first()
        
        if altura_ref:
            return altura_ref
        
        # Crear nuevo si no existe
        user = User.query.get(user_id)
        if not user or not user.height:
            return None
        
        calculo = AlturaReferencia.calcular_altura_segmento(user.height, segmento)
        
        altura_ref = AlturaReferencia(
            user_id=user_id,
            segmento=segmento,
            altura_usuario_cm=user.height,
            altura_calculada_cm=calculo['altura_calculada_cm'],
            porcentaje_drillis=calculo['porcentaje']
        )
        
        db.session.add(altura_ref)
        db.session.commit()
        
        return altura_ref

# =============================================================================
# CONFIGURACIÓN DE ARTICULACIONES
# =============================================================================

JOINT_CONFIGS = {
    'neck': {
        'name': 'Cuello',
        'icon': 'person-up',
        'description': 'Análisis de flexión cervical anterior y posterior',
        'normal_range': {'min': 0, 'max': 60},
        'optimal_range': {'min': 10, 'max': 50},
        'instructions': {
            'position': 'Mantente de pie, mirando al frente con los hombros relajados',
            'movement': 'Inclina la cabeza lentamente hacia adelante y luego hacia atrás',
            'warning': 'Evita movimientos bruscos. Detente si sientes dolor.'
        },
        'reference_points': [
            {'id': 'ear', 'name': 'Oreja'},
            {'id': 'shoulder', 'name': 'Hombro'},
            {'id': 'neck', 'name': 'Base del cuello'}
        ]
    },
    'shoulder': {
        'name': 'Hombro',
        'icon': 'shoulder_1.png',
        'description': 'Flexión, Extensión y Abducción',
        'normal_range': {'min': 0, 'max': 180},
        'optimal_range': {'min': 30, 'max': 150},
        'instructions': {
            'position': 'Mantente de pie con el brazo extendido a lo largo del cuerpo',
            'movement': 'Eleva el brazo lentamente hacia adelante hasta donde puedas',
            'warning': 'No fuerces el movimiento. Mantén el brazo extendido durante el ejercicio.'
        },
        'reference_points': [
            {'id': 'shoulder', 'name': 'Hombro'},
            {'id': 'elbow', 'name': 'Codo'},
            {'id': 'wrist', 'name': 'Muñeca'}
        ]
    },
    'elbow': {
        'name': 'Codo',
        'icon': 'elbow_1.png',
        'description': 'Flexión, Extensión y Extensión sobre la cabeza',
        'normal_range': {'min': 0, 'max': 150, 'hypermobility_threshold': 155},  # 🔧 Actualizado Norkin & White 2016
        'optimal_range': {'min': 30, 'max': 140},  # 🔧 Ajustado
        'instructions': {
            'position': 'Mantente de pie con el brazo extendido hacia abajo',
            'movement': 'Dobla el codo llevando la mano hacia el hombro',
            'warning': 'Mantén el brazo superior estático, solo mueve el antebrazo.'
        },
        'reference_points': [
            {'id': 'shoulder', 'name': 'Hombro'},
            {'id': 'elbow', 'name': 'Codo'},
            {'id': 'wrist', 'name': 'Muñeca'}
        ]
    },
    'hip': {
        'name': 'Cadera',
        'icon': 'hips_1.png',
        'description': 'Flexión, Abducción y Aducción',
        'normal_range': {'min': 0, 'max': 120},
        'optimal_range': {'min': 15, 'max': 100},
        'instructions': {
            'position': 'Mantente de pie con las piernas separadas al ancho de los hombros',
            'movement': 'Eleva una pierna hacia adelante manteniendo la rodilla recta',
            'warning': 'Mantén el equilibrio apoyándote si es necesario.'
        },
        'reference_points': [
            {'id': 'hip', 'name': 'Cadera'},
            {'id': 'knee', 'name': 'Rodilla'},
            {'id': 'ankle', 'name': 'Tobillo'}
        ]
    },
    'knee': {
        'name': 'Rodilla',
        'icon': 'knee_1.png',
        'description': 'Flexión y Extensión',
        'normal_range': {'min': 0, 'max': 135},
        'optimal_range': {'min': 10, 'max': 120},
        'instructions': {
            'position': 'Mantente de pie con las piernas ligeramente separadas',
            'movement': 'Dobla la rodilla llevando el talón hacia el glúteo',
            'warning': 'Mantén el equilibrio y evita movimientos bruscos.'
        },
        'reference_points': [
            {'id': 'hip', 'name': 'Cadera'},
            {'id': 'knee', 'name': 'Rodilla'},
            {'id': 'ankle', 'name': 'Tobillo'}
        ]
    },
    'ankle': {
        'name': 'Tobillo',
        'icon': 'ankle_1.png',
        'description': 'Flexión plantar, Dorsiflexión e Inversión',
        'normal_range': {'min': 75, 'max': 120},
        'optimal_range': {'min': 85, 'max': 110},
        'instructions': {
            'position': 'Siéntate con la pierna extendida o mantente de pie',
            'movement': 'Mueve el pie hacia arriba y hacia abajo',
            'warning': 'Mantén la pierna estable, solo mueve el pie.'
        },
        'reference_points': [
            {'id': 'knee', 'name': 'Rodilla'},
            {'id': 'ankle', 'name': 'Tobillo'},
            {'id': 'foot', 'name': 'Pie'}
        ]
    }
}

# =============================================================================
# CONFIGURACIÓN ESCALABLE DE EJERCICIOS
# =============================================================================

def load_exercise_configuration(segment, exercise):
    """📋 Cargar configuración específica de ejercicio desde JSON escalable"""
    try:
        config_path = os.path.join(app.root_path, 'config', 'exercises.json')
        
        if not os.path.exists(config_path):
            print(f"❌ Archivo de configuración no encontrado: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        
        # Validar estructura
        if 'segments' not in configs:
            print("❌ Estructura JSON inválida: falta 'segments'")
            return None
        
        segment_config = configs['segments'].get(segment)
        if not segment_config:
            print(f"❌ Segmento '{segment}' no encontrado en configuración")
            return None
            
        exercise_config = segment_config['exercises'].get(exercise)
        if not exercise_config:
            print(f"❌ Ejercicio '{exercise}' no encontrado para segmento '{segment}'")
            return None
        
        # Combinar información del segmento y ejercicio
        combined_config = {
            # Información del segmento
            'segment': segment,
            'segment_name': segment_config['name'],
            'segment_description': segment_config['description'],
            'segment_icon': segment_config['icon'],
            'anatomical_info': segment_config.get('anatomical_info', {}),
            
            # Información del ejercicio
            'exercise': exercise,
            'exercise_name': exercise_config['name'],
            'exercise_description': exercise_config['description'],
            'plane': exercise_config['plane'],
            'movement_type': exercise_config['movement_type'],
            'difficulty': exercise_config['difficulty'],
            'duration_seconds': exercise_config['duration_seconds'],
            'normal_range': exercise_config['normal_range'],
            'optimal_range': exercise_config['optimal_range'],
            'calculation_method': exercise_config['calculation_method'],
            'required_landmarks': exercise_config['required_landmarks'],
            'primary_side': exercise_config['primary_side'],
            'reference_points': exercise_config['reference_points'],
            'instructions': exercise_config['instructions'],
            'biomechanical_notes': exercise_config.get('biomechanical_notes', {}),
            'camera_orientation': exercise_config.get('camera_orientation', 'sagital'),  # 🆕 FIX: Orientación de cámara requerida
            'tts_phases': exercise_config.get('tts_phases', {}),  # 🆕 Fases de texto a voz
            'rom_capture_config': exercise_config.get('rom_capture_config', {}),  # 🆕 Config de captura ROM
            
            # Configuración del sistema
            'system_config': configs.get('system_config', {})
        }
        
        print(f"✅ Configuración cargada: {segment}/{exercise}")
        return combined_config
        
    except FileNotFoundError:
        print(f"❌ Archivo exercises.json no encontrado")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return None

def get_available_exercises(segment=None):
    """📋 Obtener lista de ejercicios disponibles"""
    try:
        config_path = os.path.join(app.root_path, 'config', 'exercises.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        
        if segment:
            # Ejercicios de un segmento específico
            segment_config = configs['segments'].get(segment)
            if segment_config and 'exercises' in segment_config:
                return list(segment_config['exercises'].keys())
            return []
        else:
            # Todos los ejercicios de todos los segmentos
            all_exercises = {}
            for seg_name, seg_config in configs['segments'].items():
                all_exercises[seg_name] = list(seg_config['exercises'].keys())
            return all_exercises
            
    except Exception as e:
        print(f"❌ Error obteniendo ejercicios: {e}")
        return [] if segment else {}

# =============================================================================
# TEST DE CONFIGURACIÓN (TEMPORAL)
# =============================================================================

def test_exercise_configuration():
    """🧪 Test de la configuración escalable"""
    print("\n🧪 PROBANDO CONFIGURACIÓN ESCALABLE:")
    
    # Test 1: Cargar flexión (debe funcionar)
    flexion_config = load_exercise_configuration('shoulder', 'flexion')
    if flexion_config:
        print(f"✅ Flexión: {flexion_config['exercise_name']}")
        print(f"   📐 Plano: {flexion_config['plane']}")
        print(f"   📊 Rango: {flexion_config['normal_range']}")
    else:
        print("❌ Flexión: Error")
    
    # Test 2: Cargar abducción (nuevo)
    abduction_config = load_exercise_configuration('shoulder', 'abduction')
    if abduction_config:
        print(f"✅ Abducción: {abduction_config['exercise_name']}")
        print(f"   📐 Plano: {abduction_config['plane']}")
    else:
        print("❌ Abducción: Error")
    
    # Test 3: Cargar rotación (nuevo)
    rotation_config = load_exercise_configuration('shoulder', 'rotation')
    if rotation_config:
        print(f"✅ Rotación: {rotation_config['exercise_name']}")
        print(f"   📐 Plano: {rotation_config['plane']}")
    else:
        print("❌ Rotación: Error")
    
    # Test 4: Listar ejercicios
    exercises = get_available_exercises('shoulder')
    print(f"✅ Ejercicios disponibles: {exercises}")
    
    print("🧪 Test de configuración completado\n")

# =============================================================================
# DECORADORES Y UTILIDADES
# =============================================================================

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """🔒 Decorador para rutas que requieren rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def log_user_action(user_id, action, changed_fields=None, old_values=None, new_values=None, ip_address=None):
    """📝 Registrar acción de usuario en auditoría"""
    try:
        import json
        from flask import request
        
        # Obtener IP si no se proporciona
        if not ip_address and request:
            ip_address = request.remote_addr
        
        # Obtener el usuario que realiza la acción
        performer_id = session.get('user_id')
        if not performer_id:
            return False
        
        audit_log = UserAuditLog(
            user_id=user_id,
            action=action,
            changed_fields=json.dumps(changed_fields) if changed_fields else None,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            performed_by=performer_id,
            ip_address=ip_address
        )
        
        db.session.add(audit_log)
        db.session.commit()
        return True
    except Exception as e:
        print(f"❌ Error logging user action: {e}")
        # CRÍTICO: Hacer rollback para evitar PendingRollbackError
        try:
            db.session.rollback()
        except:
            pass
        return False

def get_user_stats(user_id):
    """📊 Obtiene estadísticas REALES del usuario con cálculos dinámicos
    
    Justificación técnica documentada en: DOCUMENTACION_TECNICA_ESTADISTICAS.md
    """
    try:
        # 1️⃣ CONTADORES BÁSICOS POR SEGMENTO (queries optimizadas)
        total_analyses = Analysis.query.filter_by(user_id=user_id).count()
        shoulder_count = Analysis.query.filter_by(user_id=user_id, joint_type='shoulder').count()
        elbow_count = Analysis.query.filter_by(user_id=user_id, joint_type='elbow').count()
        hip_count = Analysis.query.filter_by(user_id=user_id, joint_type='hip').count()
        knee_count = Analysis.query.filter_by(user_id=user_id, joint_type='knee').count()
        ankle_count = Analysis.query.filter_by(user_id=user_id, joint_type='ankle').count()
        neck_count = Analysis.query.filter_by(user_id=user_id, joint_type='neck').count()
        
        # 2️⃣ CALCULAR PORCENTAJES DE COMPLETITUD (3 ejercicios por segmento)
        # Basado en: Flexión, Abducción, Rotación por cada segmento
        EXERCISES_PER_SEGMENT = 3
        
        def calculate_segment_percentage(segment):
            """Calcula % de ejercicios únicos completados en un segmento"""
            exercises = db.session.query(Analysis.exercise_type).filter_by(
                user_id=user_id, joint_type=segment
            ).distinct().count()
            return round((exercises / EXERCISES_PER_SEGMENT) * 100, 1)
        
        shoulder_percentage = calculate_segment_percentage('shoulder')
        elbow_percentage = calculate_segment_percentage('elbow')
        hip_percentage = calculate_segment_percentage('hip')
        knee_percentage = calculate_segment_percentage('knee')
        ankle_percentage = calculate_segment_percentage('ankle')
        
        # 3️⃣ PROGRESO GENERAL (5 segmentos × 3 ejercicios = 15 total)
        TOTAL_EXERCISES = 15
        unique_exercises = db.session.query(
            Analysis.joint_type, Analysis.exercise_type
        ).filter_by(user_id=user_id).distinct().count()
        
        overall_progress = round((unique_exercises / TOTAL_EXERCISES) * 100, 1)
        
        # 4️⃣ PROMEDIO ROM (solo análisis válidos con ROM > 0)
        rom_analyses = Analysis.query.filter(
            Analysis.user_id == user_id,
            Analysis.max_rom_achieved > 0
        ).all()
        
        avg_rom = 0
        if rom_analyses:
            avg_rom = round(sum(a.max_rom_achieved for a in rom_analyses) / len(rom_analyses), 1)
        
        # 5️⃣ SISTEMA DE LOGROS (cálculo dinámico)
        achievements_unlocked = 0
        achievements_details = []
        
        # Logro 1: Primer Análisis (total >= 1)
        if total_analyses >= 1:
            achievements_unlocked += 1
            achievements_details.append('first_analysis')
        
        # Logro 2: Analista Dedicado (hombro >= 10)
        if shoulder_count >= 10:
            achievements_unlocked += 1
            achievements_details.append('dedicated_analyst')
        
        # Logro 3: Explorador (3+ segmentos diferentes)
        unique_segments = db.session.query(Analysis.joint_type).filter_by(
            user_id=user_id
        ).distinct().count()
        if unique_segments >= 3:
            achievements_unlocked += 1
            achievements_details.append('explorer')
        
        # Logro 4: Maestro (50+ análisis totales)
        if total_analyses >= 50:
            achievements_unlocked += 1
            achievements_details.append('master')
        
        # Logro 5: Perfeccionista (20+ análisis "excellent")
        excellent_count = Analysis.query.filter_by(
            user_id=user_id, rom_classification='excellent'
        ).count()
        if excellent_count >= 20:
            achievements_unlocked += 1
            achievements_details.append('perfectionist')
        
        # Logro 6: Leyenda (100+ análisis totales)
        if total_analyses >= 100:
            achievements_unlocked += 1
            achievements_details.append('legend')
        
        # 6️⃣ TIEMPO TOTAL (suma de duration_seconds)
        total_seconds = db.session.query(
            db.func.sum(Analysis.duration_seconds)
        ).filter_by(user_id=user_id).scalar() or 0
        
        total_hours = round(total_seconds / 3600, 1)
        
        # 7️⃣ ACTIVIDAD RECIENTE (últimos 5 análisis reales)
        recent_analyses = Analysis.query.filter_by(
            user_id=user_id
        ).order_by(Analysis.created_at.desc()).limit(5).all()
        
        recent_activity = []
        for analysis in recent_analyses:
            # Calcular tiempo transcurrido
            time_diff = datetime.utcnow() - analysis.created_at
            if time_diff.days > 0:
                time_ago = f"Hace {time_diff.days} día{'s' if time_diff.days > 1 else ''}"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"Hace {hours} hora{'s' if hours > 1 else ''}"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"Hace {minutes} minuto{'s' if minutes > 1 else ''}"
            
            recent_activity.append({
                'joint_type': analysis.joint_type,
                'exercise_type': analysis.exercise_type,
                'exercise_name': analysis.exercise_name,
                'rom': analysis.max_rom_achieved,
                'classification': analysis.rom_classification,
                'time_ago': time_ago,
                'duration': analysis.duration_seconds
            })
        
        # 8️⃣ RETORNAR ESTADÍSTICAS COMPLETAS
        return {
            # Contadores básicos
            'total_analyses': total_analyses,
            'shoulder_analyses': shoulder_count,
            'elbow_analyses': elbow_count,
            'hip_analyses': hip_count,
            'knee_analyses': knee_count,
            'ankle_analyses': ankle_count,
            'neck_analyses': neck_count,
            
            # Porcentajes de completitud
            'shoulder_percentage': shoulder_percentage,
            'elbow_percentage': elbow_percentage,
            'hip_percentage': hip_percentage,
            'knee_percentage': knee_percentage,
            'ankle_percentage': ankle_percentage,
            
            # Progreso general
            'overall_progress': overall_progress,
            'unique_exercises': unique_exercises,
            'total_possible_exercises': TOTAL_EXERCISES,
            
            # Métricas ROM
            'avg_rom': avg_rom,
            
            # Sistema de logros
            'achievements': achievements_unlocked,
            'achievements_details': achievements_details,
            'unique_segments': unique_segments,  # Para tooltip "Explorador"
            'excellent_count': excellent_count,  # Para tooltip "Perfeccionista"
            
            # Tiempo total
            'total_time': total_hours,
            
            # Actividad reciente
            'recent_activity': recent_activity
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de usuario {user_id}: {e}")
        import traceback
        traceback.print_exc()
        # Retornar estructura vacía pero válida
        return {
            'total_analyses': 0,
            'shoulder_analyses': 0,
            'elbow_analyses': 0,
            'hip_analyses': 0,
            'knee_analyses': 0,
            'ankle_analyses': 0,
            'neck_analyses': 0,
            'shoulder_percentage': 0,
            'elbow_percentage': 0,
            'hip_percentage': 0,
            'knee_percentage': 0,
            'ankle_percentage': 0,
            'overall_progress': 0,
            'unique_exercises': 0,
            'total_possible_exercises': 15,
            'avg_rom': 0,
            'achievements': 0,
            'achievements_details': [],
            'unique_segments': 0,
            'excellent_count': 0,
            'total_time': 0,
            'recent_activity': []
        }

# =============================================================================
# RUTAS PRINCIPALES
# =============================================================================

@app.route('/')
def index():
    """Página de inicio - TEMPORAL: siempre mostrar login"""
    return redirect(url_for('login'))  # Forzar login siempre

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, completa todos los campos', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # 🔒 Verificar si el usuario puede iniciar sesión
            if not user.can_login():
                flash(f'Tu cuenta está {user.status}. Contacta al administrador.', 'error')
                log_user_action(user.id, 'LOGIN_DENIED')
                return render_template('login.html')
            
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['profile_image'] = getattr(user, 'profile_image', None)  # 🆕 Seguro: None si no existe columna
            
            # Actualizar último login
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # 📝 Log de acceso exitoso (sin bloquear el login)
                log_user_action(user.id, 'LOGIN')
                
            except Exception as e:
                print(f"⚠️ Error actualizando último login: {e}")
                # Hacer rollback y continuar con el login
                try:
                    db.session.rollback()
                except:
                    pass
            
            flash(f'¡Bienvenido {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del usuario"""
    user_stats = get_user_stats(session['user_id'])
    return render_template('dashboard.html', stats=user_stats)

@app.route('/audio-test')
def audio_test():
    """🔊 Página de test para el sistema de audio biomecánico"""
    return render_template('audio_test.html')

@app.route('/tts-demo')
def tts_demo():
    """🎙️ Demo del nuevo sistema de TTS con secuencias"""
    return render_template('tts_sequence_demo.html')

@app.route('/exercises')
@login_required
def exercises():
    """Lista de ejercicios disponibles"""
    # Filtrar ejercicio de cuello (temporalmente oculto por CSS)
    filtered_configs = {k: v for k, v in JOINT_CONFIGS.items() if k != 'neck'}
    return render_template('exercises.html', joint_configs=filtered_configs)

# 🚨 DEBUG ROUTE: Página de diagnóstico JavaScript
@app.route('/debug/js')
def debug_js():
    """🔍 Página de diagnóstico para JavaScript"""
    return render_template('debug_js.html')

# 🚨 DEBUG ROUTE: Test stream endpoint
@app.route('/debug/stream-test/<segment>/<exercise>')
def debug_stream_test(segment, exercise):
    """🔍 Test si el endpoint de stream está siendo accedido"""
    print("🚨🚨🚨 DEBUG STREAM TEST ACCEDIDO 🚨🚨🚨")
    logger.info(f"🔍 DEBUG: Test stream para {segment}/{exercise}")
    return jsonify({
        'success': True,
        'message': f'Debug stream test para {segment}/{exercise}',
        'timestamp': datetime.now().isoformat(),
        'handlers_available': list(AVAILABLE_HANDLERS.keys()) if 'AVAILABLE_HANDLERS' in globals() else []
    })

# 📡 RUTA: Panel de control Bluetooth ESP32
@app.route('/bluetooth_control')
@login_required
def bluetooth_control():
    """🎛️ Panel de control para ESP32 vía Web Serial API"""
    return render_template('test_bluetooth_serial.html')

# � RUTA: Control público remoto ESP32
@app.route('/bluetooth_public')
def bluetooth_public():
    """🎮 Control público remoto para ESP32 (sin login requerido)"""
    return render_template('bluetooth_public.html')

# �🔄 REST API SIMPLE: Control remoto ESP32 sin WebSocket
# Variable global para almacenar el último comando
esp32_last_command = {'command': None, 'timestamp': None}

@app.route('/api/esp32_command', methods=['POST'])
def esp32_command_post():
    """📤 Endpoint para ENVIAR comandos desde el control público"""
    global esp32_last_command
    try:
        data = request.get_json()
        command = data.get('command')
        
        if not command:
            return jsonify({'success': False, 'error': 'No command provided'}), 400
        
        # Almacenar comando con timestamp
        esp32_last_command = {
            'command': command,
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }
        
        print(f"📨 Comando ESP32 recibido: {command}")
        return jsonify({'success': True, 'message': f'Comando {command} almacenado'})
    
    except Exception as e:
        print(f"❌ Error en esp32_command_post: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/esp32_command', methods=['GET'])
def esp32_command_get():
    """📥 Endpoint para OBTENER comandos desde el controlador PC"""
    global esp32_last_command
    try:
        # Si hay comando pendiente, devolverlo y limpiarlo
        if esp32_last_command['command']:
            command = esp32_last_command['command']
            esp32_last_command = {'command': None, 'timestamp': None}
            print(f"📤 Comando ESP32 entregado: {command}")
            return jsonify({'success': True, 'command': command})
        else:
            # No hay comandos pendientes
            return jsonify({'success': True, 'command': None})
    
    except Exception as e:
        print(f"❌ Error en esp32_command_get: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 🎯 RUTA PRINCIPAL: Mantener compatibilidad total con sistema existente
@app.route('/analysis/<joint_type>')
@login_required
def analysis(joint_type):
    """🔄 Ruta original RESTAURADA - Redirige según el segmento"""
    if joint_type not in JOINT_CONFIGS:
        flash(f'Tipo de articulación "{joint_type}" no válida', 'error')
        return redirect(url_for('exercises'))
    
    # 🎯 TODOS LOS SEGMENTOS VAN AL SELECTOR DE EJERCICIOS
    # Comportamiento unificado para mejor experiencia de usuario
    return redirect(url_for('exercise_selector', joint_type=joint_type))

# 🆕 RUTA NUEVA: Selector de ejercicios para un segmento
@app.route('/exercises/<joint_type>')
@login_required
def exercise_selector(joint_type):
    """🎯 Página de selección de ejercicios para un segmento específico"""
    if joint_type not in JOINT_CONFIGS:
        flash(f'Tipo de articulación "{joint_type}" no válida', 'error')
        return redirect(url_for('exercises'))
    
    # Obtener ejercicios disponibles para este segmento
    available_exercises = get_available_exercises(joint_type)
    
    # Cargar configuraciones de ejercicios desde JSON
    exercises_config = []
    for exercise in available_exercises:
        config = load_exercise_configuration(joint_type, exercise)
        if config:
            exercises_config.append(config)
    
    joint_config = JOINT_CONFIGS[joint_type]
    
    # 📏 CALCULAR ALTURA DE CÁMARA usando Drillis & Contini
    current_user = User.query.get(session['user_id'])
    camera_height_info = AlturaReferencia.calcular_altura_segmento(
        current_user.height_cm, 
        joint_type
    )
    
    # 📊 CALCULAR PROGRESO REAL del usuario en este segmento
    try:
        # Obtener ejercicios únicos completados por el usuario
        completed_exercises = db.session.query(Analysis.exercise_type).filter_by(
            user_id=current_user.id,
            joint_type=joint_type
        ).distinct().all()
        completed_count = len(completed_exercises)
    except Exception as e:
        print(f"⚠️ Error al calcular progreso: {e}")
        completed_count = 0
    
    total_exercises = len(available_exercises)
    completion_percentage = round((completed_count / total_exercises * 100), 1) if total_exercises > 0 else 0
    
    return render_template('exercise_selector.html', 
                         joint_type=joint_type,
                         joint_config=joint_config,
                         exercises=exercises_config,
                         available_exercises=available_exercises,
                         camera_height_info=camera_height_info,
                         completed_count=completed_count,
                         total_exercises=total_exercises,
                         completion_percentage=completion_percentage)

# 🆕 RUTA NUEVA: Análisis con ejercicio específico
@app.route('/analysis/<joint_type>/<exercise>')
@login_required
def analysis_with_exercise(joint_type, exercise):
    """🎯 Página de análisis para una articulación y ejercicio específicos"""
    if joint_type not in JOINT_CONFIGS:
        flash(f'Tipo de articulación "{joint_type}" no válida', 'error')
        return redirect(url_for('exercises'))
    
    # 🔍 Verificar que el ejercicio sea válido para este segmento
    valid_exercises = get_available_exercises(joint_type)
    if exercise not in valid_exercises:
        flash(f'Ejercicio "{exercise}" no válido para {joint_type}', 'error')
        return redirect(url_for('exercise_selector', joint_type=joint_type))
    
    joint_config = JOINT_CONFIGS[joint_type]
    
    # 👤 Obtener datos del usuario para cálculos biomecánicos
    current_user = User.query.get(session['user_id'])
    
    # 📋 Obtener lista completa de ejercicios disponibles para el menú dropdown
    available_exercises = get_available_exercises(joint_type)
    
    # ✅ Cargar configuración específica del ejercicio desde JSON
    try:
        exercise_config = load_exercise_configuration(joint_type, exercise)
        if exercise_config:
            print(f"✅ Configuración cargada: {joint_type}/{exercise}")
        else:
            # 🔄 Fallback con configuración básica
            exercise_config = {
                'segment': joint_type,
                'segment_name': joint_config['name'],
                'segment_description': joint_config['description'],
                'segment_icon': joint_config.get('icon', 'circle'),
                'exercise': exercise,
                'exercise_name': f"{exercise.title()} de {joint_config['name']}",
                'exercise_description': f"Análisis de {exercise} de {joint_config['name'].lower()}",
                'plane': 'sagital',  # Default
                'movement_type': 'flexion_extension',
                'difficulty': 'easy',
                'duration_seconds': 30,
                'normal_range': joint_config['normal_range'],
                'optimal_range': joint_config.get('optimal_range', joint_config['normal_range']),
                'instructions': joint_config['instructions'],
                'biomechanical_notes': {},
                'system_config': {}
            }
            print(f"⚠️ Usando fallback para {joint_type}/{exercise}")
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        flash('Error cargando configuración del ejercicio', 'error')
        return redirect(url_for('exercise_selector', joint_type=joint_type))
    
    return render_template('analysis.html', 
                         joint_type=joint_type,
                         exercise=exercise,
                         joint_config=joint_config,
                         exercise_config=exercise_config,
                         available_exercises=available_exercises,
                         user=current_user)

@app.route('/profile')
@login_required
def profile():
    """Perfil del usuario"""
    user_stats = get_user_stats(session['user_id'])
    user = User.query.get(session['user_id'])  # 🆕 Obtener datos del usuario
    return render_template('profile.html', user_stats=user_stats, user=user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """✏️ Actualizar información del perfil del usuario"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'email' in data:
            user.email = data['email'].strip() if data['email'] else None
        
        if 'full_name' in data:
            user.full_name = data['full_name'].strip() if data['full_name'] else None
        
        if 'bio' in data:
            user.bio = data['bio'].strip() if data['bio'] else None
        
        if 'specialization' in data:
            user.specialization = data['specialization'].strip() if data['specialization'] else None
        
        # Guardar cambios
        db.session.commit()
        logger.info(f"✅ Perfil actualizado para usuario {user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Perfil actualizado correctamente',
            'data': {
                'email': user.email,
                'full_name': user.full_name,
                'bio': user.bio,
                'specialization': user.specialization
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error actualizando perfil: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/run_migration_profile_image')
@admin_required
def run_migration_profile_image():
    """🔧 TEMPORAL: Ejecutar migración de profile_image manualmente (solo admin)"""
    try:
        # Verificar si ya existe
        inspector = sqla_inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'profile_image' in columns:
            return jsonify({
                'success': True,
                'message': 'La columna profile_image ya existe en la base de datos'
            })
        
        # Detectar tipo de DB
        db_type = db.engine.dialect.name
        
        # Agregar columna
        if db_type == 'postgresql':
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN profile_image VARCHAR(255)'))
        else:
            db.session.execute(text('ALTER TABLE user ADD COLUMN profile_image VARCHAR(255)'))
        
        db.session.commit()
        
        logger.info("✅ Migración ejecutada manualmente por admin")
        
        return jsonify({
            'success': True,
            'message': 'Migración ejecutada exitosamente. La columna profile_image ha sido agregada.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error en migración manual: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al ejecutar migración: {str(e)}'
        }), 500

@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    """📸 Subir/actualizar imagen de perfil del usuario"""
    import os
    from werkzeug.utils import secure_filename
    
    try:
        # ✅ VERIFICAR QUE LA COLUMNA EXISTE EN LA BASE DE DATOS (no solo en el modelo)
        inspector = sqla_inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'profile_image' not in columns:
            return jsonify({
                'success': False, 
                'message': '⚠️ La funcionalidad de foto de perfil no está configurada. El administrador debe ejecutar: /admin/run_migration_profile_image'
            }), 503
        
        if 'profile_image' not in request.files:
            return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
        
        file = request.files['profile_image']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        # Validar extensión
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Formato de archivo no permitido. Use PNG, JPG, JPEG, GIF o WEBP'}), 400
        
        # Obtener usuario actual - AHORA ES SEGURO porque ya verificamos que la columna existe
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Crear directorio si no existe
        upload_folder = os.path.join(app.static_folder, 'uploads', 'profiles')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generar nombre único para el archivo
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"user_{user.id}_{int(datetime.now().timestamp())}.{file_extension}"
        filepath = os.path.join(upload_folder, filename)
        
        # Eliminar imagen anterior si existe (usando getattr para seguridad)
        old_image = getattr(user, 'profile_image', None)
        if old_image:
            old_filepath = os.path.join(app.static_folder, old_image.lstrip('/'))
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar imagen anterior: {e}")
        
        # Guardar nueva imagen
        file.save(filepath)
        
        # Actualizar ruta en base de datos (ruta relativa desde static/) - De forma segura
        try:
            setattr(user, 'profile_image', f"uploads/profiles/{filename}")
            user.modified_at = datetime.utcnow()
            db.session.commit()
            
            # Actualizar session también
            session['profile_image'] = f"uploads/profiles/{filename}"
            
            logger.info(f"✅ Imagen de perfil actualizada para usuario {user.username}")
            
            return jsonify({
                'success': True,
                'message': 'Imagen de perfil actualizada correctamente',
                'image_url': url_for('static', filename=f"uploads/profiles/{filename}")
            })
        except Exception as db_error:
            # Si falla al guardar en DB, al menos guardamos la imagen
            logger.warning(f"⚠️ No se pudo guardar en DB (columna no existe aún): {db_error}")
            db.session.rollback()
            
            # Retornar éxito parcial (imagen guardada, pero no en DB)
            return jsonify({
                'success': False,
                'message': 'La funcionalidad de foto de perfil no está completamente configurada. Contacte al administrador para ejecutar las migraciones de base de datos.'
            }), 503
        
    except Exception as e:
        logger.error(f"❌ Error al subir imagen de perfil: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al subir imagen: {str(e)}'}), 500

@app.route('/reports')
@login_required
def reports():
    """📊 Reportes del usuario - historial completo por ejercicio"""
    user_id = session['user_id']
    
    # Obtener análisis agrupados por segmento y ejercicio
    analyses_by_segment = {}
    for segment in ['shoulder', 'elbow', 'hip', 'knee', 'ankle', 'neck']:
        segment_analyses = Analysis.query.filter_by(
            user_id=user_id, 
            joint_type=segment
        ).order_by(Analysis.created_at.desc()).all()
        
        # Agrupar por ejercicio
        exercises = {}
        for analysis in segment_analyses:
            exercise = analysis.exercise_type
            if exercise not in exercises:
                exercises[exercise] = []
            exercises[exercise].append(analysis)
        
        if exercises:
            analyses_by_segment[segment] = exercises
    
    return render_template('reports.html', analyses_by_segment=analyses_by_segment)

# =============================================================================
# 🔒 RUTAS DE ADMINISTRACIÓN (SOLO ADMIN)
# =============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """🏠 Panel de administración"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(status='active').count(),
        'inactive_users': User.query.filter_by(status='inactive').count(),
        'total_analyses': Analysis.query.count(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
        'recent_logins': User.query.filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).limit(10).all()
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/users')
@admin_required
def admin_users():
    """👥 Gestión de usuarios"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    query = User.query
    
    # Filtros
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.full_name.contains(search),
                User.email.contains(search)
            )
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users, status_filter=status_filter, search=search)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    """➕ Crear nuevo usuario"""
    if request.method == 'POST':
        try:
            # Validar datos
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role', 'student')
            height_cm = float(request.form.get('height_cm', 170.0))
            phone = request.form.get('phone', '').strip()
            emergency_contact = request.form.get('emergency_contact', '').strip()
            medical_notes = request.form.get('medical_notes', '').strip()
            
            # Fecha de nacimiento
            date_of_birth = None
            if request.form.get('date_of_birth'):
                from datetime import datetime
                date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
            
            # Validaciones
            if not username or not password:
                flash('Usuario y contraseña son obligatorios', 'error')
                return render_template('admin/create_user.html')
            
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya existe', 'error')
                return render_template('admin/create_user.html')
            
            # Crear usuario
            new_user = User(
                username=username,
                full_name=full_name,
                email=email,
                role=role,
                height_cm=height_cm,
                date_of_birth=date_of_birth,
                phone=phone,
                emergency_contact=emergency_contact,
                medical_notes=medical_notes,
                created_by=session['user_id'],
                status='active'
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log de auditoría
            log_user_action(new_user.id, 'CREATE', 
                          new_values=new_user.to_dict(include_sensitive=True))
            
            flash(f'Usuario {username} creado exitosamente', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creando usuario: {str(e)}', 'error')
    
    return render_template('admin/create_user.html')

@app.route('/admin/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    """👤 Detalle de usuario específico"""
    user = User.query.get_or_404(user_id)
    user_stats = get_user_stats(user_id)
    
    # Historial de auditoría
    audit_logs = UserAuditLog.query.filter_by(user_id=user_id).order_by(
        UserAuditLog.performed_at.desc()
    ).limit(50).all()
    
    return render_template('admin/user_detail.html', 
                         user=user, 
                         user_stats=user_stats, 
                         audit_logs=audit_logs)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """✏️ Editar usuario"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Capturar valores anteriores para auditoría
            old_values = user.to_dict(include_sensitive=True)
            
            # Actualizar campos
            user.full_name = request.form.get('full_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.role = request.form.get('role', user.role)
            user.height_cm = float(request.form.get('height_cm', user.height_cm))
            user.phone = request.form.get('phone', '').strip()
            user.emergency_contact = request.form.get('emergency_contact', '').strip()
            user.medical_notes = request.form.get('medical_notes', '').strip()
            
            # Fecha de nacimiento
            if request.form.get('date_of_birth'):
                user.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
            
            # Nueva contraseña (opcional)
            if request.form.get('new_password'):
                user.set_password(request.form.get('new_password'))
            
            user.modified_by = session['user_id']
            user.modified_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log de auditoría
            new_values = user.to_dict(include_sensitive=True)
            changed_fields = [k for k, v in old_values.items() if new_values.get(k) != v]
            
            log_user_action(user_id, 'UPDATE', 
                          changed_fields=changed_fields,
                          old_values=old_values,
                          new_values=new_values)
            
            flash(f'Usuario {user.username} actualizado exitosamente', 'success')
            return redirect(url_for('admin_user_detail', user_id=user_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error actualizando usuario: {str(e)}', 'error')
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    """⏸️▶️ Activar/Desactivar usuario (soft delete)"""
    user = User.query.get_or_404(user_id)
    
    # No permitir desactivar al propio admin
    if user_id == session['user_id']:
        flash('No puedes desactivar tu propia cuenta', 'error')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    
    try:
        old_status = user.status
        
        if user.status == 'active':
            user.deactivate(session['user_id'])
            action = 'DEACTIVATE'
            message = f'Usuario {user.username} desactivado'
        else:
            user.reactivate(session['user_id'])
            action = 'REACTIVATE'
            message = f'Usuario {user.username} reactivado'
        
        db.session.commit()
        
        # Log de auditoría
        log_user_action(user_id, action, 
                      changed_fields=['status'],
                      old_values={'status': old_status},
                      new_values={'status': user.status})
        
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cambiando estado: {str(e)}', 'error')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """🔑 Resetear contraseña de usuario"""
    user = User.query.get_or_404(user_id)
    
    try:
        new_password = request.form.get('new_password')
        if not new_password:
            flash('La nueva contraseña es obligatoria', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        user.set_password(new_password)
        user.modified_by = session['user_id']
        user.modified_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log de auditoría (sin incluir la contraseña)
        log_user_action(user_id, 'PASSWORD_RESET', 
                      changed_fields=['password'])
        
        flash(f'Contraseña de {user.username} restablecida exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error restableciendo contraseña: {str(e)}', 'error')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/download-database')
@admin_required
def admin_download_database():
    """💾 Descargar backup de la base de datos SQLite (solo admin)"""
    try:
        # Ruta local de la base de datos
        db_path = os.path.join(app.instance_path, 'biomech_system.db')
        
        if not os.path.exists(db_path):
            flash('Base de datos no encontrada', 'error')
            return redirect(url_for('admin_panel'))
        
        # Generar nombre con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'biomech_backup_{timestamp}.db'
        
        print(f'📥 Admin {session.get("username")} descargando backup: {download_name}')
        
        return send_file(
            db_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/x-sqlite3'
        )
        
    except Exception as e:
        print(f'❌ Error descargando base de datos: {str(e)}')
        flash(f'Error al descargar la base de datos: {str(e)}', 'error')
        return redirect(url_for('admin_panel'))

@app.route('/api/admin/check-frames', methods=['GET'])
@admin_required
def check_saved_frames():
    """🔍 DIAGNÓSTICO: Verificar cuántos análisis tienen capturas guardadas"""
    try:
        # Total de análisis
        total_analyses = Analysis.query.count()
        
        # Análisis CON captura (best_frame_data no es NULL y no está vacío)
        with_frames = Analysis.query.filter(
            Analysis.best_frame_data.isnot(None),
            Analysis.best_frame_data != ''
        ).count()
        
        # Análisis SIN captura
        without_frames = total_analyses - with_frames
        
        # Porcentaje de completitud
        percentage_complete = round((with_frames / total_analyses * 100), 1) if total_analyses > 0 else 0
        
        # Análisis recientes (últimos 10) para ver ejemplos
        recent_analyses = Analysis.query.order_by(Analysis.created_at.desc()).limit(10).all()
        recent_samples = []
        
        for analysis in recent_analyses:
            has_frame = bool(analysis.best_frame_data and len(analysis.best_frame_data) > 0)
            frame_size = len(analysis.best_frame_data) if has_frame else 0
            
            recent_samples.append({
                'id': analysis.id,
                'exercise': analysis.exercise_name,
                'date': analysis.created_at.strftime('%Y-%m-%d %H:%M'),
                'has_frame': has_frame,
                'frame_size_kb': round(frame_size / 1024, 1) if has_frame else 0
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_analyses': total_analyses,
                'with_frames': with_frames,
                'without_frames': without_frames,
                'percentage_complete': percentage_complete
            },
            'recent_samples': recent_samples,
            'recommendation': (
                '✅ Listo para PDFs con capturas' if percentage_complete >= 80 
                else '⚠️ Muchos análisis sin captura - Mejorar guardado antes de PDFs'
            )
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# 📄 ENDPOINT: Descargar reporte PDF del usuario
@app.route('/download-report/<int:user_id>')
@login_required
def download_user_report(user_id):
    """
    📥 Descargar reporte completo del usuario en PDF
    Incluye capturas si están disponibles, texto informativo si no
    """
    try:
        # Verificar que el usuario solo pueda descargar su propio reporte
        # O que sea admin
        if session['user_id'] != user_id and not session.get('is_admin', False):
            flash('No tienes permiso para descargar este reporte', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener datos del usuario
        user = User.query.get_or_404(user_id)
        user_data = {
            'name': user.full_name,
            'email': user.email,
            'total_analyses': Analysis.query.filter_by(user_id=user_id).count()
        }
        
        # Obtener todos los análisis del usuario
        analyses = Analysis.query.filter_by(user_id=user_id).order_by(Analysis.created_at.desc()).all()
        
        # Preparar datos de análisis para el PDF
        analyses_data = []
        for analysis in analyses:
            # Obtener clasificación y comentario
            rom_classification = analysis.rom_classification or 'desconocido'
            
            # Preparar datos del análisis con valores por defecto seguros
            analysis_dict = {
                'id': analysis.id,
                'exercise_name': get_exercise_display_name(analysis.joint_type, analysis.exercise_type),
                'date': analysis.created_at.strftime('%d/%m/%Y %H:%M'),
                'segment': get_joint_display_name(analysis.joint_type),
                'max_rom': analysis.max_rom_achieved if analysis.max_rom_achieved is not None else 0,
                'rom_classification': rom_classification,
                'side': analysis.max_rom_side or 'N/A',
                'has_frame': bool(analysis.best_frame_data),
                'frame_data': analysis.best_frame_data if analysis.best_frame_data else None
            }
            analyses_data.append(analysis_dict)
        
        # Generar PDF
        pdf_generator = BiomechanicalPDFGenerator()
        pdf_buffer = pdf_generator.generate_user_report(user_data, analyses_data)
        
        # Nombre del archivo
        filename = f"reporte_{user.full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Enviar archivo
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        print(f"❌ Error generando PDF: {str(e)}")
        print(traceback.format_exc())
        flash(f'Error generando reporte: {str(e)}', 'error')
        return redirect(url_for('reports'))


def get_exercise_display_name(joint_type, exercise_type):
    """Obtener nombre en español del ejercicio"""
    exercise_names = {
        'shoulder': {
            'flexion': 'Flexión de Hombro',
            'extension': 'Extensión de Hombro',
            'abduction': 'Abducción de Hombro',
            'adduction': 'Aducción de Hombro'
        },
        'elbow': {
            'flexion': 'Flexión de Codo',
            'extension': 'Extensión de Codo'
        },
        'hip': {
            'flexion': 'Flexión de Cadera',
            'extension': 'Extensión de Cadera',
            'abduction': 'Abducción de Cadera'
        },
        'knee': {
            'flexion': 'Flexión de Rodilla',
            'extension': 'Extensión de Rodilla'
        },
        'ankle': {
            'dorsiflexion': 'Dorsiflexión de Tobillo',
            'plantarflexion': 'Flexión Plantar de Tobillo'
        }
    }
    return exercise_names.get(joint_type, {}).get(exercise_type, f'{joint_type} - {exercise_type}')


def get_joint_display_name(joint_type):
    """Obtener nombre en español del segmento"""
    joint_names = {
        'shoulder': 'Hombro',
        'elbow': 'Codo',
        'hip': 'Cadera',
        'knee': 'Rodilla',
        'ankle': 'Tobillo',
        'neck': 'Cuello'
    }
    return joint_names.get(joint_type, joint_type.capitalize())


# 🆕 RUTA NUEVA: Resultados consolidados por segmento
@app.route('/results/<joint_type>')
@login_required
def segment_results(joint_type):
    """🎯 Página de resultados consolidados para un segmento específico"""
    if joint_type not in JOINT_CONFIGS:
        flash(f'Tipo de articulación "{joint_type}" no válida', 'error')
        return redirect(url_for('exercises'))
    
    user_id = session['user_id']
    joint_config = JOINT_CONFIGS[joint_type]
    
    # Obtener ejercicios disponibles para este segmento
    available_exercises = get_available_exercises(joint_type)
    
    # Obtener estadísticas y resultados por ejercicio
    results_by_exercise = {}
    
    for exercise in available_exercises:
        # Obtener análisis de este ejercicio específico
        analyses = Analysis.query.filter_by(
            user_id=user_id,
            joint_type=joint_type,
            exercise_type=exercise
        ).order_by(Analysis.created_at.desc()).all()
        
        # Calcular estadísticas del ejercicio
        if analyses:
            angles = [a.current_angle for a in analyses]
            exercise_stats = {
                'total_attempts': len(analyses),
                'best_angle': max(angles),
                'latest_angle': angles[0],
                'average_angle': round(sum(angles) / len(angles), 1),
                'latest_analysis': analyses[0],
                'all_analyses': analyses[:10],  # Últimos 10
                'has_data': True
            }
        else:
            exercise_stats = {
                'total_attempts': 0,
                'best_angle': 0,
                'latest_angle': 0,
                'average_angle': 0,
                'latest_analysis': None,
                'all_analyses': [],
                'has_data': False
            }
        
        # Cargar configuración del ejercicio
        exercise_config = load_exercise_configuration(joint_type, exercise)
        exercise_stats['config'] = exercise_config
        
        results_by_exercise[exercise] = exercise_stats
    
    # Calcular progreso general del segmento
    completed_exercises = sum(1 for stats in results_by_exercise.values() if stats['has_data'])
    general_stats = {
        'completed_exercises': completed_exercises,
        'total_exercises': len(available_exercises),
        'completion_percentage': round((completed_exercises / len(available_exercises)) * 100, 1),
        'total_attempts': sum(stats['total_attempts'] for stats in results_by_exercise.values())
    }
    
    return render_template('segment_results.html',
                         joint_type=joint_type,
                         joint_config=joint_config,
                         results_by_exercise=results_by_exercise,
                         general_stats=general_stats,
                         available_exercises=available_exercises)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/exercises_config', methods=['GET'])
def api_exercises_config():
    """
    🆕 API para obtener la configuración completa de exercises.json
    Usado por el sistema de audio guide para cargar instrucciones TTS
    """
    try:
        config_path = os.path.join(app.root_path, 'config', 'exercises.json')
        
        if not os.path.exists(config_path):
            logger.error(f"❌ exercises.json no encontrado en: {config_path}")
            return jsonify({
                'success': False,
                'error': 'Archivo de configuración no encontrado'
            }), 404
        
        with open(config_path, 'r', encoding='utf-8') as f:
            exercises_config = json.load(f)
        
        logger.info(f"✅ exercises.json servido correctamente")
        return jsonify({
            'success': True,
            'config': exercises_config
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando exercises.json: {e}")
        return jsonify({
            'success': False,
            'error': f'Error de sintaxis JSON: {str(e)}'
        }), 500
        
    except Exception as e:
        logger.error(f"❌ Error leyendo exercises.json: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save_measurement', methods=['POST'])
@login_required
def api_save_measurement():
    """API para guardar mediciones con soporte multi-ejercicio"""
    try:
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['joint_type', 'current_angle']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # 🆕 Extraer tipo de ejercicio (con fallback)
        exercise_type = data.get('exercise_type', 'flexion')
        joint_type = data['joint_type']
        
        # 🆕 Generar nombre descriptivo del ejercicio DESDE exercises.json
        exercise_config = load_exercise_configuration(joint_type, exercise_type)
        if exercise_config and 'exercise_name' in exercise_config:
            # Usar el nombre real del ejercicio (e.g., "Extensión de Hombro")
            exercise_name = exercise_config['exercise_name']
        elif joint_type in JOINT_CONFIGS:
            # Fallback: generar nombre genérico
            joint_name = JOINT_CONFIGS[joint_type]['name']
            exercise_name = f"{exercise_type.title()} de {joint_name}"
        else:
            exercise_name = f"Análisis de {joint_type}/{exercise_type}"
        
        # Crear nuevo análisis
        analysis = Analysis(
            user_id=session['user_id'],
            joint_type=joint_type,
            exercise_type=exercise_type,  # 🆕 Campo nuevo
            exercise_name=exercise_name,  # 🆕 Nombre descriptivo
            current_angle=data['current_angle'],
            max_angle=data.get('max_angle', data['current_angle']),
            min_angle=data.get('min_angle', data['current_angle']),
            avg_angle=data.get('avg_angle', data['current_angle']),
            total_measurements=data.get('total_measurements', 1),
            is_within_normal_range=data.get('is_normal', True),
            quality_score=data.get('quality', 85),
            duration_seconds=data.get('duration', 30),
            analysis_metadata=json.dumps(data.get('metadata', {}))
        )
        
        db.session.add(analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Medición guardada correctamente',
            'analysis_id': analysis.id
        })
        
    except Exception as e:
        print(f"Error guardando medición: {e}")
        db.session.rollback()
        return jsonify({'error': 'Error guardando medición'}), 500

# =============================================================================
# 📷 API PARA GESTIÓN DE CÁMARAS
# =============================================================================

@app.route('/api/preload_cameras', methods=['POST'])
@login_required
def preload_cameras():
    """
    🚀 Pre-cargar cámaras disponibles al abrir página
    SESSION 2: Respeta preferencia guardada en LocalStorage
    - Si viene preferred_camera_id → valida solo esa cámara
    - Si falla o no viene → escaneo completo
    """
    try:
        from biomechanical_analysis.core.camera_manager import preload_cameras_at_startup, validate_single_camera
        
        # 🔍 SESSION 2: Verificar si viene cámara preferida desde LocalStorage
        data = request.get_json(silent=True) or {}
        preferred_camera_id = data.get('preferred_camera_id')
        
        if preferred_camera_id is not None:
            logger.info(f"🎯 SESSION 2: LocalStorage solicita cámara {preferred_camera_id}")
            
            # Validar solo esa cámara
            camera = validate_single_camera(preferred_camera_id)
            
            if camera:
                logger.info(f"✅ Cámara guardada válida: {camera.get('display_name')}")
                camera_list = [{
                    'id': camera['id'],
                    'name': camera.get('display_name', f'Cámara {camera["id"]}'),
                    'resolution': camera.get('resolution', 'Unknown'),
                    'fps': camera.get('fps', 0),
                    'recommended': True,  # Siempre recomendada si es válida
                    'camera_type': camera.get('camera_type', 'unknown'),
                    'from_cache': True  # 🆕 Indicador de que viene de LocalStorage
                }]
                
                return jsonify({
                    'success': True,
                    'cameras': camera_list,
                    'from_cache': True
                }), 200
            else:
                logger.warning(f"⚠️ Cámara guardada {preferred_camera_id} NO disponible, escaneando todas...")
        
        # 🔄 Escaneo completo (fallback o primera vez)
        logger.info("🔍 Iniciando pre-carga de cámaras...")
        cameras = preload_cameras_at_startup()
        
        if cameras:
            # Convertir dict de cámaras a lista
            camera_list = [
                {
                    'id': cam['id'],
                    'name': cam.get('display_name', f'Cámara {cam["id"]}'),
                    'resolution': cam.get('resolution', 'Unknown'),
                    'fps': cam.get('fps', 0),
                    'recommended': cam.get('recommended', False),
                    'camera_type': cam.get('camera_type', 'unknown'),
                    'from_cache': False
                }
                for cam in cameras.values()
            ]
            
            logger.info(f"✅ Pre-carga exitosa: {len(camera_list)} cámaras detectadas")
            
            return jsonify({
                'success': True,
                'cameras': camera_list,
                'from_cache': False,
                'message': f'{len(camera_list)} cámaras detectadas y mejor cámara auto-seleccionada'
            })
        else:
            logger.warning("⚠️ No se detectaron cámaras")
            return jsonify({
                'success': False,
                'error': 'No cameras found',
                'message': 'No se detectaron cámaras disponibles'
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Error pre-cargando cámaras: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error al detectar cámaras'
        }), 500

@app.route('/api/set_preselected_camera/<joint_type>', methods=['POST'])
@login_required
def set_preselected_camera(joint_type):
    """
    🎯 Configurar cámara seleccionada manualmente
    IMPORTANTE: Detiene stream activo ANTES de cambiar cámara
    """
    try:
        data = request.json
        camera_id = data.get('camera_id')
        camera_info = data.get('camera_info', {})
        
        if camera_id is None:
            return jsonify({'error': 'camera_id requerido'}), 400
        
        logger.info(f"🎯 Usuario cambió cámara a: {camera_id} para {joint_type}")
        
        # 🧹 CRÍTICO: Detener stream activo ANTES de cambiar cámara
        try:
            from handlers.stream_manager import stream_manager
            
            # Mapeo de joint_type a handler_id
            handler_map = {
                'shoulder': 'shoulder',
                'elbow': 'elbow',
                'hip': 'hip',
                'knee': 'knee',
                'ankle': 'ankle',
                'neck': 'neck'
            }
            
            handler_id = handler_map.get(joint_type)
            
            if handler_id:
                if stream_manager.is_stream_active(handler_id):
                    logger.info(f"🧹 Deteniendo stream activo de {handler_id} antes de cambiar cámara")
                    stream_manager.stop_stream(handler_id)
                    
                    # Dar tiempo a liberar cámara
                    import time
                    time.sleep(0.5)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo detener stream (puede no estar activo): {e}")
        
        # 💾 Guardar nueva selección en bypass global
        from handlers.camera_bypass import set_preselected_camera_global
        
        # Agregar metadatos
        camera_info['source'] = 'USER_MANUAL_SELECTION'
        camera_info['timestamp'] = datetime.now().timestamp()
        camera_info['joint_type'] = joint_type
        
        set_preselected_camera_global(camera_id, camera_info)
        
        logger.info(f"✅ Cámara {camera_id} preseleccionada para {joint_type}")
        
        return jsonify({
            'success': True,
            'message': f'Cámara {camera_id} configurada. Inicie el análisis para usarla.',
            'camera_id': camera_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error configurando cámara: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# 📏 API ALTURA DRILLIS-CONTINI (SERVO CAMERA POSITIONING)
# =============================================================================

@app.route('/api/altura/<segmento>', methods=['GET'])
def get_altura_referencia(segmento):
    """
    📏 Obtener altura de referencia para posicionamiento de cámara
    Basado en fórmulas de Drillis & Contini (1966)
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user or not user.height:
            return jsonify({
                'error': 'Usuario no tiene altura registrada',
                'needs_height': True
            }), 400
        
        # Obtener o crear registro de altura
        altura_ref = AlturaReferencia.obtener_o_crear(user_id, segmento)
        
        if not altura_ref:
            return jsonify({'error': 'Error calculando altura'}), 500
        
        return jsonify({
            'success': True,
            'segmento': segmento,
            'altura_usuario_cm': altura_ref.altura_usuario_cm,
            'altura_calculada_cm': altura_ref.altura_calculada_cm,
            'porcentaje_drillis': altura_ref.porcentaje_drillis * 100,
            'formula': f'{altura_ref.porcentaje_drillis * 100}% × {altura_ref.altura_usuario_cm} cm',
            'instruccion': f'Coloca la cámara a {altura_ref.altura_calculada_cm:.1f} cm del suelo',
            'created_at': altura_ref.created_at.isoformat() if altura_ref.created_at else None
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo altura: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/altura/<segmento>/actualizar', methods=['POST'])
def actualizar_altura_referencia(segmento):
    """
    📏 Actualizar altura cuando el usuario cambia su altura registrada
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user or not user.height:
            return jsonify({'error': 'Usuario sin altura registrada'}), 400
        
        # Buscar registro existente
        altura_ref = AlturaReferencia.query.filter_by(
            user_id=user_id,
            segmento=segmento
        ).first()
        
        # Recalcular
        calculo = AlturaReferencia.calcular_altura_segmento(user.height, segmento)
        
        if altura_ref:
            # Actualizar existente
            altura_ref.altura_usuario_cm = user.height
            altura_ref.altura_calculada_cm = calculo['altura_calculada_cm']
            altura_ref.porcentaje_drillis = calculo['porcentaje']
            altura_ref.updated_at = datetime.utcnow()
        else:
            # Crear nuevo
            altura_ref = AlturaReferencia(
                user_id=user_id,
                segmento=segmento,
                altura_usuario_cm=user.height,
                altura_calculada_cm=calculo['altura_calculada_cm'],
                porcentaje_drillis=calculo['porcentaje']
            )
            db.session.add(altura_ref)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Altura actualizada',
            'altura_calculada_cm': altura_ref.altura_calculada_cm
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error actualizando altura: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# ✅ STREAMS USANDO HANDLERS MODULARES
# =============================================================================

import sys
import logging

# Configurar logging para que funcione con Gunicorn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Forzar flush de stdout para Railway logs
sys.stdout.flush()

logger.info("\n" + "="*70)
logger.info("📦 IMPORTANDO HANDLERS...")
logger.info("="*70)
sys.stdout.flush()

# Los handlers se agregarán a AVAILABLE_HANDLERS (ya definido al inicio)

try:
    from handlers.shoulder_handler import shoulder_handler
    if shoulder_handler and hasattr(shoulder_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['shoulder'] = shoulder_handler
        logger.info("✅ Shoulder handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning("⚠️ Shoulder handler importado pero no tiene generate_frames")
        sys.stdout.flush()
        shoulder_handler = None
except ImportError as e:
    logger.error(f"❌ Error importando shoulder handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    shoulder_handler = None
except Exception as e:
    logger.error(f"❌ Error inesperado con shoulder handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    shoulder_handler = None

try:
    from handlers.elbow_handler import elbow_handler
    if elbow_handler and hasattr(elbow_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['elbow'] = elbow_handler
        logger.info("✅ Elbow handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning("⚠️ Elbow handler importado pero no tiene generate_frames")
        sys.stdout.flush()
        elbow_handler = None
except ImportError as e:
    logger.error(f"❌ Error importando elbow handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    elbow_handler = None
except Exception as e:
    logger.error(f"❌ Error inesperado con elbow handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    elbow_handler = None

try:
    from handlers.neck_handler import neck_handler
    if neck_handler and hasattr(neck_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['neck'] = neck_handler
        logger.info("✅ Neck handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning("⚠️ Neck handler importado pero no tiene generate_frames")
        sys.stdout.flush()
        neck_handler = None
except ImportError as e:
    logger.error(f"❌ Error importando neck handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    neck_handler = None
except Exception as e:
    logger.error(f"❌ Error inesperado con neck handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    neck_handler = None

try:
    from handlers.hip_handler import hip_handler
    if hip_handler and hasattr(hip_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['hip'] = hip_handler
        logger.info("✅ Hip handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning("⚠️ Hip handler importado pero no tiene generate_frames")
        sys.stdout.flush()
        hip_handler = None
except ImportError as e:
    logger.error(f"❌ Error importando hip handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    hip_handler = None
except Exception as e:
    logger.error(f"❌ Error inesperado con hip handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    hip_handler = None

logger.info("🔍 INTENTANDO IMPORTAR KNEE HANDLER...")
sys.stdout.flush()
try:
    logger.info("🔍 Step 1: Importando módulo knee_handler...")
    sys.stdout.flush()
    from handlers.knee_handler import knee_handler
    logger.info(f"🔍 Step 2: knee_handler importado: {knee_handler}")
    sys.stdout.flush()
    if knee_handler and hasattr(knee_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['knee'] = knee_handler
        logger.info("✅ Knee handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning(f"⚠️ Knee handler importado pero no tiene generate_frames. Tiene: {dir(knee_handler)}")
        sys.stdout.flush()
        knee_handler = None
except ImportError as e:
    logger.error(f"❌ ImportError en knee handler: {e}")
    logger.error(f"❌ Tipo de error: {type(e).__name__}")
    logger.error(f"❌ Args: {e.args}")
    import traceback
    logger.error("❌ TRACEBACK COMPLETO:")
    traceback.print_exc()
    sys.stdout.flush()
    knee_handler = None
except Exception as e:
    logger.error(f"❌ Exception inesperada en knee handler: {e}")
    logger.error(f"❌ Tipo de error: {type(e).__name__}")
    logger.error(f"❌ Args: {e.args if hasattr(e, 'args') else 'No args'}")
    import traceback
    logger.error("❌ TRACEBACK COMPLETO:")
    traceback.print_exc()
    sys.stdout.flush()
    knee_handler = None
logger.info(f"🔍 KNEE HANDLER FINAL: {knee_handler}")
sys.stdout.flush()

try:
    from handlers.ankle_handler import ankle_handler
    if ankle_handler and hasattr(ankle_handler, 'generate_frames'):
        AVAILABLE_HANDLERS['ankle'] = ankle_handler
        logger.info("✅ Ankle handler importado y validado")
        sys.stdout.flush()
    else:
        logger.warning("⚠️ Ankle handler importado pero no tiene generate_frames")
        sys.stdout.flush()
        ankle_handler = None
except ImportError as e:
    logger.error(f"❌ Error importando ankle handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    ankle_handler = None
except Exception as e:
    logger.error(f"❌ Error inesperado con ankle handler: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    ankle_handler = None

# 🌐 ESP32 PROXY HANDLER - Soluciona Mixed Content (HTTPS → HTTP)
try:
    from handlers.esp32_proxy import esp32_proxy
    app.register_blueprint(esp32_proxy)
    logger.info("✅ ESP32 Proxy handler registrado")
    sys.stdout.flush()
except Exception as e:
    logger.error(f"❌ Error registrando ESP32 proxy: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

logger.info("="*70)
logger.info(f"📊 Handlers disponibles: {list(AVAILABLE_HANDLERS.keys())}")
logger.info(f"📊 Total: {len(AVAILABLE_HANDLERS)}/6")
logger.info("="*70 + "\n")
sys.stdout.flush()

# 🔐 IMPORTAR STREAM MANAGER para control de concurrencia
try:
    from handlers.stream_manager import stream_manager
    logger.info("✅ StreamManager importado correctamente")
    sys.stdout.flush()
    
    # 🧹 REGISTRAR CLEANUP AL APAGAR SERVIDOR
    def cleanup_streams_on_shutdown():
        """Limpia todos los streams cuando el servidor se apaga"""
        logger.info("🧹 Limpiando streams al apagar servidor...")
        if stream_manager:
            stream_manager.stop_all_streams()
            logger.info("✅ Todos los streams detenidos")
        sys.stdout.flush()
    
    atexit.register(cleanup_streams_on_shutdown)
    logger.info("✅ Cleanup hook registrado con atexit")
    sys.stdout.flush()
    
except Exception as e:
    logger.error(f"❌ Error importando StreamManager: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    stream_manager = None

@app.route('/api/stream/shoulder')
def stream_shoulder_analysis():
    """🎯 STREAM DE HOMBRO usando handler"""
    logger.info(f"🎯 [LEGACY] Stream shoulder accedido (sin ejercicio específico)")
    
    if not shoulder_handler or not shoulder_handler.available:
        logger.error(f"❌ Shoulder handler no disponible en legacy endpoint")
        return "Error: Shoulder handler no disponible", 500
    
    logger.info(f"✅ [LEGACY] Iniciando stream shoulder legacy")
    return Response(
        shoulder_handler.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/stop_stream/shoulder', methods=['POST'])
@login_required
def stop_shoulder_stream():
    """⏹️ DETENER stream de hombro"""
    if shoulder_handler:
        shoulder_handler.stop()
    return jsonify({'success': True, 'message': 'Stream hombro detenido'})

# =============================================================================
# 🔍 DEBUG ENDPOINTS - ADMIN ONLY (Validación de Ángulos)
# =============================================================================

@app.route('/api/debug/enable/<segment>/<exercise>', methods=['POST'])
@login_required
@admin_required
def enable_debug_mode(segment, exercise):
    """🔍 ACTIVAR modo debug para validación de ángulos (SOLO ADMIN)"""
    try:
        # Obtener el handler correspondiente
        handler_map = {
            'shoulder': shoulder_handler,
            'elbow': elbow_handler,
            'hip': hip_handler,
            'knee': knee_handler,
            'ankle': ankle_handler
        }
        
        handler = handler_map.get(segment)
        if not handler:
            return jsonify({
                'success': False,
                'error': f'Handler no disponible para segmento: {segment}'
            }), 404
        
        if not hasattr(handler, 'enable_debug'):
            return jsonify({
                'success': False,
                'error': f'Handler de {segment} no soporta debugging'
            }), 400
        
        # Activar debug mode
        handler.enable_debug()
        
        # Obtener username para logging
        user = User.query.get(session['user_id'])
        logger.info(f"🔍 [ADMIN] Debug activado: {segment} - {exercise} por {user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Debug activado para {segment} - {exercise}',
            'segment': segment,
            'exercise': exercise,
            'debug_mode': True
        })
        
    except Exception as e:
        logger.error(f"❌ Error activando debug: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug/disable/<segment>/<exercise>', methods=['POST'])
@login_required
@admin_required
def disable_debug_mode(segment, exercise):
    """⏹️ DESACTIVAR modo debug (SOLO ADMIN)"""
    try:
        # Obtener el handler correspondiente
        handler_map = {
            'shoulder': shoulder_handler,
            'elbow': elbow_handler,
            'hip': hip_handler,
            'knee': knee_handler,
            'ankle': ankle_handler
        }
        
        handler = handler_map.get(segment)
        if not handler:
            return jsonify({
                'success': False,
                'error': f'Handler no disponible para segmento: {segment}'
            }), 404
        
        if not hasattr(handler, 'disable_debug'):
            return jsonify({
                'success': False,
                'error': f'Handler de {segment} no soporta debugging'
            }), 400
        
        # Desactivar debug mode
        handler.disable_debug()
        
        # Obtener username para logging
        user = User.query.get(session['user_id'])
        logger.info(f"⏹️ [ADMIN] Debug desactivado: {segment} - {exercise} por {user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Debug desactivado para {segment} - {exercise}',
            'segment': segment,
            'exercise': exercise,
            'debug_mode': False
        })
        
    except Exception as e:
        logger.error(f"❌ Error desactivando debug: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug/capture/<segment>/<exercise>', methods=['POST'])
@login_required
@admin_required
def capture_debug_snapshot(segment, exercise):
    """📸 CAPTURAR snapshot con validación manual (SOLO ADMIN)"""
    try:
        # Obtener ángulo manual del cuerpo de la petición (opcional)
        data = request.get_json() or {}
        manual_angle = data.get('manual_angle', None)
        
        # Validar ángulo manual si se proporciona
        if manual_angle is not None:
            try:
                manual_angle = float(manual_angle)
                if not (0 <= manual_angle <= 360):
                    return jsonify({
                        'success': False,
                        'error': 'Ángulo manual debe estar entre 0 y 360 grados'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Ángulo manual inválido'
                }), 400
        
        # Obtener el handler correspondiente
        handler_map = {
            'shoulder': shoulder_handler,
            'elbow': elbow_handler,
            'hip': hip_handler,
            'knee': knee_handler,
            'ankle': ankle_handler
        }
        
        handler = handler_map.get(segment)
        if not handler:
            return jsonify({
                'success': False,
                'error': f'Handler no disponible para segmento: {segment}'
            }), 404
        
        if not hasattr(handler, 'capture_debug_snapshot'):
            return jsonify({
                'success': False,
                'error': f'Handler de {segment} no soporta capture de debug'
            }), 400
        
        # Capturar snapshot
        result = handler.capture_debug_snapshot(manual_angle)
        
        if result['success']:
            # Obtener username para logging
            user = User.query.get(session['user_id'])
            logger.info(f"📸 [ADMIN] Snapshot capturado: {segment} - {exercise} por {user.username}")
            if manual_angle is not None:
                logger.info(f"   Ángulo manual: {manual_angle}°")
                if 'error_deg' in result:
                    logger.info(f"   Error: {result['error_deg']:.2f}° ({result['error_percent']:.1f}%)")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error capturando snapshot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stream/elbow')
def stream_elbow_analysis():
    """🎯 STREAM DE CODO usando handler"""
    logger.info(f"🎯 [LEGACY] Stream elbow accedido")
    
    if not elbow_handler or not elbow_handler.available:
        logger.error(f"❌ Elbow handler no disponible en legacy endpoint")
        return "Error: Elbow handler no disponible", 500
    
    logger.info(f"✅ [LEGACY] Iniciando stream elbow legacy")
    return Response(
        elbow_handler.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/stop_stream/elbow', methods=['POST'])
@login_required
def stop_elbow_stream():
    """⏹️ DETENER stream de codo"""
    if elbow_handler:
        elbow_handler.stop()
    return jsonify({'success': True, 'message': 'Stream codo detenido'})

# =============================================================================
# 🎯 ENDPOINTS DINÁMICOS MULTI-EJERCICIO - LEGACY ELIMINADO
# =============================================================================

# ❌ ENDPOINT LEGACY ELIMINADO - CAUSABA CONFLICTO CON ROUTING
# El endpoint `/api/stream/<joint_type>/<exercise>` ha sido eliminado
# porque Flask priorizaba este endpoint sobre el más completo `stream_dynamic_analysis`
# Ahora solo usamos el endpoint moderno que maneja todos los casos correctamente


@app.route('/api/stop_stream/<joint_type>', methods=['POST'])
@login_required  
def stop_stream_dynamic(joint_type):
    """⏹️ DETENER stream dinámico - LEGACY REDIRECTED"""
    
    # ❌ ENDPOINT LEGACY - REDIRIGIR AL MODERNO
    logger.info(f"⚠️ Endpoint legacy stop_stream_dynamic llamado para {joint_type}")
    logger.info("   Redirigiendo al endpoint moderno stop_dynamic_stream")
    
    # Usar el endpoint moderno directamente
    return stop_dynamic_stream(joint_type, 'flexion')  # Default exercise

# =============================================================================
# 🆕 RUTAS DINÁMICAS ESCALABLES - MULTI-EJERCICIO
# =============================================================================

@app.route('/api/stream/<segment>/<exercise>')
def stream_dynamic_analysis(segment, exercise):
    """
    🎯 STREAM DINÁMICO con DETECCIÓN DE CONCURRENCIA
    
    - Si hay 1 usuario → Server-side streaming (rápido)
    - Si hay 2+ usuarios → Forzar client-side streaming (sin conflictos)
    """
    
    # 🚨 LOGS MÚLTIPLES PARA DETECTAR ACCESO AL ENDPOINT
    print("=" * 100)
    print(f"🎯🎯🎯 STREAM ENDPOINT ACCEDIDO: {segment}/{exercise} 🎯🎯🎯")
    print("=" * 100)
    
    logger.info("=" * 80)
    logger.info(f"🎯 Stream solicitado: {segment}/{exercise}")
    logger.info(f"🌐 User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    logger.info(f"🔗 Referer: {request.headers.get('Referer', 'Unknown')}")
    logger.info(f"📍 Remote Address: {request.remote_addr}")
    logger.info("=" * 80)
    
    # Log adicional
    print(f"🎯 [FLASK] Stream request: {segment}/{exercise}")
    
    # 🔍 Validar segmento
    if segment not in JOINT_CONFIGS:
        logger.error(f"❌ Segmento no válido: {segment}")
        logger.error(f"   Segmentos disponibles: {list(JOINT_CONFIGS.keys())}")
        return jsonify({'error': f'Segmento {segment} no válido'}), 400
    
    # 🔍 Validar ejercicio para el segmento
    valid_exercises = get_available_exercises(segment)
    if exercise not in valid_exercises:
        logger.error(f"❌ Ejercicio no válido: {exercise} para {segment}")
        logger.error(f"   Ejercicios disponibles para {segment}: {valid_exercises}")
        return jsonify({'error': f'Ejercicio {exercise} no válido para {segment}'}), 400
    
    # 🔍 Verificar handler disponible
    if segment not in AVAILABLE_HANDLERS:
        logger.error(f"❌ Handler de {segment} NO está disponible")
        logger.error(f"   Handlers disponibles: {list(AVAILABLE_HANDLERS.keys())}")
        return jsonify({
            'error': f'Handler de {segment} no disponible',
            'mode': 'CLIENT_SIDE_REQUIRED',
            'reason': 'Handler not initialized',
            'message': 'El módulo no se pudo importar. Use client-side streaming.'
        }), 503
    
    handler = AVAILABLE_HANDLERS[segment]
    logger.info(f"✅ Handler encontrado para {segment}")
    
    # 🔐 DETECCIÓN DE CONCURRENCIA - NUEVO
    active_streams = 0
    if stream_manager:
        active_streams = stream_manager.count_active_streams()
        logger.info(f"📊 Streams activos detectados: {active_streams}")
    
    # ⚠️ SI HAY OTROS USUARIOS ACTIVOS → FORZAR CLIENT-SIDE
    if active_streams > 0:
        logger.warning(f"⚠️ CONCURRENCIA DETECTADA: {active_streams} stream(s) activo(s)")
        logger.warning(f"   → Forzando CLIENT-SIDE streaming para evitar conflictos")
        return jsonify({
            'error': 'Multiple users detected',
            'mode': 'CLIENT_SIDE_REQUIRED',
            'reason': f'{active_streams} active streams',
            'message': f'Usando modo client-side para evitar conflictos de cámara ({active_streams} usuario(s) activo(s))',
            'active_count': active_streams
        }), 503
    
    # ✅ SOLO 1 USUARIO → PERMITIR SERVER-SIDE (más rápido)
    logger.info(f"✅ Usuario único detectado, usando SERVER-SIDE streaming")
    
    # 🔐 VERIFICAR si ya hay un stream activo para ESTE segmento (advertencia)
    if stream_manager and stream_manager.is_stream_active(segment):
        logger.warning(f"⚠️ Ya existe un stream activo para {segment}")
        logger.warning(f"   El StreamManager se encargará de detenerlo automáticamente")
        # No retornamos error - dejamos que StreamManager lo maneje
    
    # 🎯 SEGMENTOS IMPLEMENTADOS: Shoulder, Elbow, Hip, Knee, Ankle (patrón común Railway)
    if segment in ['shoulder', 'elbow', 'hip', 'knee', 'ankle']:
        logger.info(f"✅ Usando {segment} handler")
        logger.info(f"   Handler disponible: {handler is not None}")
        logger.info(f"   Tiene generate_frames: {hasattr(handler, 'generate_frames')}")
        logger.info(f"   Tiene available: {hasattr(handler, 'available')}")
        
        if not handler:
            logger.error(f"❌ Handler es None")
            return jsonify({
                'error': f'{segment.title()} handler es None',
                'details': 'El handler no está inicializado'
            }), 503
            
        if not hasattr(handler, 'available'):
            logger.warning(f"⚠️ Handler no tiene atributo 'available', asumiendo disponible")
        elif not handler.available:
            logger.error(f"❌ {segment.title()} handler available=False")
            return jsonify({
                'error': f'{segment.title()} handler no disponible',
                'details': 'El handler existe pero no está listo para streaming'
            }), 503
        
        # ✅ Configurar el ejercicio específico en el handler
        if hasattr(handler, 'set_current_exercise'):
            handler.set_current_exercise(exercise)
            logger.info(f"✅ {segment.title()} configurado para ejercicio: {exercise}")
        else:
            logger.warning(f"⚠️ {segment.title()} handler no tiene set_current_exercise, usando default")
        
        # 🔐 REGISTRAR STREAM EN STREAM MANAGER (CRÍTICO)
        if stream_manager:
            try:
                # Registrar stream ANTES de generar frames
                stream_manager.start_stream(segment, handler, exercise)
                logger.info(f"✅ Stream registrado en StreamManager para {segment}/{exercise}")
            except Exception as e:
                logger.error(f"⚠️ Error registrando stream en StreamManager: {e}")
                # No es crítico si falla el registro, continuar
        
        try:
            logger.info(f"🎥 Iniciando stream de frames...")
            if not hasattr(handler, 'generate_frames'):
                logger.error(f"❌ Handler no tiene método generate_frames")
                return jsonify({
                    'error': 'Handler sin generate_frames',
                    'mode': 'CLIENT_SIDE_REQUIRED',
                    'reason': 'Handler missing generate_frames method',
                    'message': 'El handler no implementa el método requerido. Use client-side streaming.'
                }), 503
                
            logger.info(f"🚀 Llamando handler.generate_frames()...")
            return Response(
                handler.generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        except Exception as e:
            logger.error(f"❌ Error al generar frames: {e}")
            import traceback
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            
            # Si falla server-side, forzar client-side como fallback
            return jsonify({
                'error': 'Server-side stream failed',
                'mode': 'CLIENT_SIDE_REQUIRED',
                'reason': str(e),
                'message': 'Error en server-side streaming. Cambiando automáticamente a client-side.',
                'traceback': traceback.format_exc() if app.debug else None
            }), 503
    
    # 🔄 OTROS SEGMENTOS: Preparar para expansión futura (neck, hip, knee, ankle)
    else:
        logger.error(f"⚠️ Segmento {segment} aún no implementado")
        return f"Error: Segmento {segment} en desarrollo", 501

@app.route('/api/stop_stream/<segment>/<exercise>', methods=['POST'])
@login_required
def stop_dynamic_stream(segment, exercise):
    """⏹️ DETENER stream dinámico"""
    
    print(f"\n{'='*70}")
    print(f"🛑 Solicitud de detener stream: {segment}/{exercise}")
    print(f"{'='*70}")
    
    # Verificar si el handler existe
    if segment not in AVAILABLE_HANDLERS:
        print(f"❌ Handler de {segment} no encontrado en AVAILABLE_HANDLERS")
        print(f"   Handlers disponibles: {list(AVAILABLE_HANDLERS.keys())}")
        return jsonify({
            'success': False, 
            'message': f'Handler de {segment} no encontrado',
            'available_handlers': list(AVAILABLE_HANDLERS.keys())
        }), 404
    
    handler = AVAILABLE_HANDLERS[segment]
    
    # Verificar que el handler tenga el método stop
    if not hasattr(handler, 'stop'):
        print(f"⚠️ Handler de {segment} no tiene método stop()")
        return jsonify({
            'success': False,
            'message': f'Handler de {segment} no soporta detención'
        }), 400
    
    try:
        # 🔐 USAR STREAM MANAGER para detener el stream
        if stream_manager:
            stopped = stream_manager.stop_stream(segment)
            if stopped:
                print(f"✅ Stream {segment}/{exercise} detenido vía StreamManager")
            else:
                print(f"⚠️ No había stream activo para {segment}/{exercise}")
        else:
            # Fallback: Llamar directamente al handler si StreamManager no está disponible
            print(f"⚠️ StreamManager no disponible, usando método directo")
            handler.stop()
        
        print(f"✅ Stream {segment}/{exercise} detenido correctamente")
        return jsonify({
            'success': True, 
            'message': f'Stream {segment}/{exercise} detenido'
        })
    except Exception as e:
        print(f"❌ Error al detener stream: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error deteniendo stream',
            'error': str(e)
        }), 500

@app.route('/api/set_preselected_camera/<segment>/<exercise>', methods=['POST'])
def set_preselected_camera_dynamic(segment, exercise):
    """🎯 CONFIGURAR cámara para segmento/ejercicio específico"""
    try:
        data = request.json
        camera_id = data.get('camera_id')
        camera_info = data.get('camera_info', {})
        
        print(f"🎯 RECIBIDO: camera_id={camera_id} para {segment}/{exercise}")
        print(f"🎯 Camera info: {camera_info}")
        
        # ✅ USAR FUNCIÓN GLOBAL COMPARTIDA (mantener compatibilidad)
        from handlers.camera_bypass import set_preselected_camera_global
        
        # ✅ LLAMAR función global con los parámetros correctos
        result = set_preselected_camera_global(camera_id, camera_info)
        
        print(f"✅ Cámara {camera_id} configurada para {segment}/{exercise}")
        
        return jsonify({
            'success': True,
            'message': f'Cámara {camera_id} preseleccionada para {segment}/{exercise}',
            'camera_id': camera_id,
            'camera_label': camera_info.get('label', 'Desconocida'),
            'segment': segment,
            'exercise': exercise,
            'result': result
        })
        
    except Exception as e:
        print(f"❌ Error configurando cámara dinámica: {e}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'message': f'Error configurando cámara para {segment}/{exercise}'
        }), 500

# =============================================================================
# ✅ MANTENER RUTAS ESTÁTICAS PARA COMPATIBILIDAD
# =============================================================================

# ✅ ESTAS RUTAS SIGUEN FUNCIONANDO (no romper nada):
# /api/stream/shoulder
# /api/stop_stream/shoulder
# /api/set_preselected_camera/shoulder

# =============================================================================
# � ENDPOINTS PARA STREAMING DESDE CLIENTE (RAILWAY MODE)
# =============================================================================

@app.route('/api/upload_frame/<segment>/<exercise>', methods=['POST'])
def upload_client_frame(segment, exercise):
    """📡 SISTEMA ÚNICO: Upload directo al client_frame_receiver"""
    try:
        # 🛡️ VALIDACIÓN INICIAL DEL REQUEST
        if not request.is_json:
            logger.error("❌ Request no es JSON")
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json(silent=True)
        
        if data is None:
            logger.error("❌ No se pudo parsear JSON - posible payload muy grande")
            return jsonify({'success': False, 'error': 'Invalid JSON or payload too large'}), 400
        
        if 'frame' not in data:
            logger.error("❌ No hay campo 'frame' en el JSON")
            return jsonify({'success': False, 'error': 'Missing frame field'}), 400
        
        frame_data = data['frame']
        timestamp = data.get('timestamp', None)
        
        # 🎥 METADATA DE CÁMARA para detección inteligente de mirror
        camera_metadata = {
            'width': data.get('width', 0),
            'height': data.get('height', 0),
            'device_label': data.get('device_label', '')
        }
        
        # 📊 LOG REDUCIDO para evitar spam (solo cada 10 frames)
        frame_size_kb = len(frame_data) / 1024 if frame_data else 0
        
        # Usar SOLO client_frame_receiver (sistema unificado)
        from handlers.client_frame_receiver import client_frame_receiver
        
        # 🚀 AUTO-ACTIVAR receiver si no está activo
        if not client_frame_receiver.is_active:
            logger.info("🔄 Auto-activando client_frame_receiver")
            client_frame_receiver.start_receiving()
        
        # Enviar frame con metadata para detección de tipo de cámara
        success = client_frame_receiver.receive_frame(frame_data, timestamp, camera_metadata)
        
        if success:
            stats = client_frame_receiver.get_stats()
            # LOG cada 10 frames para reducir spam
            if stats['frame_count'] % 10 == 0:
                logger.info(f"✅ Frame {stats['frame_count']}: {frame_size_kb:.1f} KB")
            
            return jsonify({
                'success': True, 
                'count': stats['frame_count'],
                'active': stats['is_active']
            })
        else:
            logger.error(f"❌ Error procesando frame en client_receiver")
            return jsonify({'success': False, 'error': 'Receiver failed'}), 500
            
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/prepare_client_receiver/<segment>/<exercise>', methods=['POST'])
def prepare_client_receiver(segment, exercise):
    """🚀 Pre-activar client_frame_receiver antes de uploads"""
    try:
        logger.info(f"🚀 [PREP] Preparando receiver para {segment}/{exercise}")
        
        from handlers.client_frame_receiver import client_frame_receiver
        
        if not client_frame_receiver.is_active:
            client_frame_receiver.start_receiving()
            logger.info("✅ Client receiver activado exitosamente")
        else:
            logger.info("✅ Client receiver ya estaba activo")
        
        stats = client_frame_receiver.get_stats()
        return jsonify({
            'success': True,
            'message': 'Receiver preparado',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error preparando receiver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client_frame_stats', methods=['GET'])
def get_client_frame_stats():
    """📊 Obtener estadísticas del receptor de frames del cliente"""
    try:
        from handlers.client_frame_receiver import client_frame_receiver
        stats = client_frame_receiver.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/environment_info', methods=['GET'])
def get_environment_info():
    """🌍 Obtener información del entorno (local vs Railway)"""
    try:
        from handlers.environment_detector import get_current_environment
        env_info = get_current_environment()
        
        return jsonify({
            'success': True,
            'environment': env_info
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo environment info: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# =============================================================================
# 🔧 DEBUG ENDPOINTS PARA RAILWAY - VER LOGS EN TIEMPO REAL
# =============================================================================

@app.route('/api/debug/logs', methods=['GET'])
def get_debug_logs():
    """🔍 Ver logs recientes para debugging"""
    try:
        # Logs básicos sin imports complejos
        recent_logs = [
            {'timestamp': 'now', 'level': 'INFO', 'message': 'Debug endpoint funcionando'},
            {'timestamp': 'now', 'level': 'INFO', 'message': f'Handlers: {len(AVAILABLE_HANDLERS)} disponibles'}
        ]
        
        return jsonify({
            'success': True,
            'logs': recent_logs,
            'handlers': list(AVAILABLE_HANDLERS.keys()) if 'AVAILABLE_HANDLERS' in globals() else []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/test_upload', methods=['POST'])
def test_upload_debug():
    """🧪 Test específico para upload de frames"""
    try:
        logger.info("🧪 TEST: Iniciando test de upload")
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data'}), 400
            
        if 'frame' not in data:
            return jsonify({'success': False, 'error': 'No frame in data'}), 400
        
        frame_data = data['frame']
        frame_size = len(frame_data) if frame_data else 0
        
        logger.info(f"🧪 TEST: Frame size: {frame_size}")
        
        # Test básico de decodificación
        import base64
        if 'data:image' in frame_data:
            frame_data = frame_data.split(',')[1]
        
        try:
            frame_bytes = base64.b64decode(frame_data)
            decoded_size = len(frame_bytes)
            logger.info(f"🧪 TEST: Decoded OK: {decoded_size} bytes")
            
            return jsonify({
                'success': True,
                'frame_size': frame_size,
                'decoded_size': decoded_size,
                'message': 'Decode successful'
            })
        except Exception as decode_error:
            logger.error(f"🧪 TEST: Decode error: {decode_error}")
            return jsonify({
                'success': False,
                'error': f'Decode failed: {str(decode_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"🧪 TEST ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# 🆕 ENDPOINTS API ROM SYSTEM
# =============================================================================

@app.route('/api/rom/start_calibration/<segment>/<exercise>', methods=['POST'])
@login_required
def start_rom_calibration(segment, exercise):
    """📏 Iniciar calibración ROM para segmento/ejercicio"""
    try:
        logger.info(f"🔔 ROM CALIBRATION REQUEST: {segment}/{exercise}")
        
        # Verificar handler disponible
        if segment not in AVAILABLE_HANDLERS:
            logger.error(f"❌ Handler {segment} no encontrado")
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        logger.info(f"✅ Handler {segment} encontrado: {type(handler).__name__}")
        
        # Verificar que el handler tenga métodos ROM
        if not hasattr(handler, 'start_rom_calibration'):
            logger.error(f"❌ Handler {segment} no tiene start_rom_calibration")
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no soporta ROM tracking'
            }), 400
            
        # Configurar ejercicio y iniciar calibración
        logger.info(f"🎯 Configurando ejercicio: {exercise}")
        handler.set_current_exercise(exercise)
        
        logger.info(f"📏 Llamando start_rom_calibration()...")
        status = handler.start_rom_calibration()
        
        logger.info(f"✅ Calibración ROM iniciada: {segment}/{exercise} - Status: {status}")
        
        return jsonify({
            'success': True,
            'message': 'Calibración iniciada',
            'status': status,
            'segment': segment,
            'exercise': exercise
        })
        
    except Exception as e:
        logger.error(f"❌ Error iniciando calibración ROM: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rom/calibrate/<segment>/<exercise>', methods=['POST'])
@login_required
def calibrate_rom_position(segment, exercise):
    """⚖️ Calibrar posición anatómica ROM"""
    try:
        logger.info(f"🔔 ROM CALIBRATE REQUEST: {segment}/{exercise}")
        data = request.json
        angle = data.get('angle')
        
        logger.info(f"📐 Ángulo recibido: {angle}")
        
        if angle is None:
            logger.error("❌ Ángulo no proporcionado")
            return jsonify({
                'success': False,
                'error': 'Ángulo requerido para calibración'
            }), 400
            
        # Verificar handler
        if segment not in AVAILABLE_HANDLERS:
            logger.error(f"❌ Handler {segment} no encontrado")
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        logger.info(f"✅ Handler {segment} encontrado")
        
        # Calibrar
        logger.info(f"⚖️ Llamando calibrate_rom({angle})...")
        status = handler.calibrate_rom(angle)
        
        logger.info(f"✅ ROM calibrado: {segment}/{exercise} = {angle}° - Status: {status}")
        
        return jsonify({
            'success': True,
            'message': 'Calibración completada',
            'status': status,
            'calibration_angle': angle
        })
        
    except Exception as e:
        logger.error(f"❌ Error calibrando ROM: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rom/start_session/<segment>/<exercise>', methods=['POST'])
@login_required
def start_rom_session(segment, exercise):
    """🚀 Iniciar sesión de medición ROM"""
    try:
        logger.info(f"🔔 ROM START_SESSION REQUEST: {segment}/{exercise}")
        
        # Verificar handler
        if segment not in AVAILABLE_HANDLERS:
            logger.error(f"❌ Handler {segment} no encontrado")
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        logger.info(f"✅ Handler {segment} encontrado")
        
        # Iniciar sesión
        logger.info(f"🚀 Llamando start_rom_session()...")
        result = handler.start_rom_session()
        
        logger.info(f"✅ Sesión ROM iniciada: {segment}/{exercise} - Result: {result}")
        
        # ✅ MANEJAR DIFERENTES FORMATOS DE RETORNO (bool o dict)
        if isinstance(result, bool):
            # Formato antiguo (knee/hip retornan bool)
            success = result
            status = 'session_started' if result else 'error'
        elif isinstance(result, dict):
            # Formato nuevo (ankle/shoulder retornan dict)
            success = result.get('success', True)  # Default True si no está
            status = result.get('status', 'session_started')
        else:
            success = True
            status = 'session_started'
        
        return jsonify({
            'success': success,
            'message': 'Sesión ROM iniciada' if success else 'Error iniciando sesión',
            'status': status,
            'result': result if isinstance(result, dict) else {},
            'segment': segment,
            'exercise': exercise
        })
        
    except Exception as e:
        logger.error(f"❌ Error iniciando sesión ROM: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rom/end_session/<segment>/<exercise>', methods=['POST'])
@login_required
def end_rom_session(segment, exercise):
    """⏹️ Finalizar sesión ROM y guardar resultados"""
    try:
        # Verificar handler
        if segment not in AVAILABLE_HANDLERS:
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        
        # Finalizar sesión
        results = handler.end_rom_session()
        
        if results is None:
            return jsonify({
                'success': False,
                'error': 'No hay sesión ROM activa'
            }), 400
            
        # 🆕 GUARDAR EN BASE DE DATOS
        try:
            # Crear nuevo análisis con datos ROM - USAR NOMBRE REAL DEL EJERCICIO
            exercise_config = load_exercise_configuration(segment, exercise)
            if exercise_config and 'exercise_name' in exercise_config:
                exercise_name = exercise_config['exercise_name']
            else:
                exercise_name = f"{exercise.title()} de {segment.title()}"
            
            # ✅ SOPORTE PARA DIFERENTES FORMATOS DE HANDLERS
            analysis = Analysis(
                user_id=session['user_id'],
                joint_type=segment,
                exercise_type=exercise,
                exercise_name=exercise_name,
                current_angle=results.get('max_rom', 0),
                max_rom_achieved=results.get('max_rom', 0),
                max_rom_side=results.get('max_rom_side', 'ninguno'),
                calibration_angle=results.get('calibration_angle', 0),
                rom_classification=results.get('classification', 'unknown'),
                best_frame_data=results.get('best_frame', ''),
                total_measurements=results.get('total_measurements', 0),
                duration_seconds=int(results.get('session_duration', results.get('duration', 0))),
                quality_score=85,  # Default
                analysis_metadata=json.dumps({
                    'rom_results': results,
                    'exercise_config': exercise,
                    'classification_info': results.get('classification_info', {})
                })
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            logger.info(f"✅ Análisis ROM guardado: {segment}/{exercise} - {results['max_rom']}°")
            
        except Exception as db_error:
            logger.error(f"❌ Error guardando en DB: {db_error}")
            db.session.rollback()
            # Continuar sin fallar - datos temporales disponibles
            
        return jsonify({
            'success': True,
            'message': 'Sesión ROM finalizada',
            'results': results,
            'analysis_id': analysis.id if 'analysis' in locals() else None
        })
        
    except Exception as e:
        logger.error(f"❌ Error finalizando sesión ROM: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rom/cancel/<segment>/<exercise>', methods=['POST'])
@login_required
def cancel_rom_session(segment, exercise):
    """🛑 Cancelar sesión ROM activa sin guardar datos"""
    try:
        logger.info(f"🛑 ROM CANCEL REQUEST: {segment}/{exercise}")
        
        # Verificar handler
        if segment not in AVAILABLE_HANDLERS:
            logger.error(f"❌ Handler {segment} no encontrado")
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        logger.info(f"✅ Handler {segment} encontrado")
        
        # Detener ROM tracker si existe
        if hasattr(handler, 'rom_tracker') and handler.rom_tracker:
            logger.info("🛑 Deteniendo ROM tracker...")
            handler.rom_tracker.stop_capture()
            handler.rom_tracker = None
            logger.info("✅ ROM tracker detenido")
        
        # Resetear analyzer si existe
        if hasattr(handler, 'analyzer') and handler.analyzer:
            logger.info("🔄 Reseteando analyzer...")
            # No hay método reset específico, pero limpiamos referencias
            handler.analyzer = None
            logger.info("✅ Analyzer reseteado")
        
        # Limpiar estado del handler
        if hasattr(handler, 'current_segment'):
            handler.current_segment = None
        if hasattr(handler, 'current_exercise'):
            handler.current_exercise = None
            
        logger.info(f"✅ Sesión ROM cancelada exitosamente: {segment}/{exercise}")
        
        return jsonify({
            'success': True,
            'message': 'Sesión ROM cancelada exitosamente',
            'segment': segment,
            'exercise': exercise
        })
        
    except Exception as e:
        logger.error(f"❌ Error cancelando sesión ROM: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rom/status/<segment>/<exercise>', methods=['GET'])
@login_required
def get_rom_status(segment, exercise):
    """📊 Obtener estado actual de la sesión ROM"""
    try:
        # Verificar handler
        if segment not in AVAILABLE_HANDLERS:
            return jsonify({
                'success': False,
                'error': f'Handler {segment} no disponible'
            }), 404
            
        handler = AVAILABLE_HANDLERS[segment]
        
        # Obtener estado
        status = handler.get_rom_status()
        
        # Obtener recomendaciones de cámara para el usuario
        user = User.query.get(session['user_id'])
        camera_recommendations = user.get_camera_recommendations(segment) if user else {}
        
        return jsonify({
            'success': True,
            'status': status,
            'camera_recommendations': camera_recommendations,
            'segment': segment,
            'exercise': exercise
        })
        
    except Exception as e:
        error_str = str(e)
        
        # 🚨 MIGRACIÓN DE EMERGENCIA: Si falla por columnas faltantes
        if "no such column" in error_str and ("height_cm" in error_str or "rom" in error_str.lower()):
            logger.error(f"🚨 EJECUTANDO MIGRACIÓN DE EMERGENCIA por: {error_str}")
            
            try:
                # Ejecutar migración de emergencia
                with app.app_context():
                    auto_migrate_database()  # ✅ Usar función existente
                
                # Reintentar la operación
                logger.info("🔄 Reintentando después de migración de emergencia...")
                user = User.query.get(session['user_id'])
                camera_recommendations = user.get_camera_recommendations(segment) if user else {}
                status = handler.get_rom_status()
                
                return jsonify({
                    'success': True,
                    'status': status,
                    'camera_recommendations': camera_recommendations,
                    'segment': segment,
                    'exercise': exercise,
                    'migration_executed': True
                })
                
            except Exception as migration_error:
                logger.error(f"❌ Falló migración de emergencia: {migration_error}")
                return jsonify({
                    'success': False, 
                    'error': 'Database migration required - please redeploy',
                    'original_error': error_str
                }), 500
        
        logger.error(f"❌ Error obteniendo estado ROM: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/history/<segment>/<exercise>', methods=['GET'])
@login_required
def get_analysis_history(segment, exercise):
    """📊 Obtener historial de análisis del usuario - VERSIÓN DEFENSIVA"""
    try:
        user_id = session['user_id']
        limit = request.args.get('limit', 10, type=int)
        
        # 🔍 VERIFICAR SI EXISTEN ANÁLISIS PRIMERO
        total_count = Analysis.query.filter_by(
            user_id=user_id,
            joint_type=segment,
            exercise_type=exercise
        ).count()
        
        if total_count == 0:
            return jsonify({
                'success': True,
                'history': [],
                'total_analyses': 0,
                'message': 'No hay análisis previos para este ejercicio'
            })
        
        # Obtener análisis recientes del usuario para este segmento/ejercicio
        analyses = Analysis.query.filter_by(
            user_id=user_id,
            joint_type=segment,
            exercise_type=exercise
        ).order_by(Analysis.created_at.desc()).limit(limit).all()
        
        # 🛡️ FORMATEAR RESULTADOS CON VERIFICACIÓN DEFENSIVA
        history = []
        for analysis in analyses:
            try:
                # Verificar campos obligatorios
                if not hasattr(analysis, 'created_at') or not analysis.created_at:
                    continue
                    
                # 🔧 ACCESO SEGURO A CAMPOS ROM (pueden no existir)
                max_rom = getattr(analysis, 'max_rom_achieved', None) or getattr(analysis, 'max_angle', 0)
                max_rom_side = getattr(analysis, 'max_rom_side', 'ninguno')  # 🆕 Lado ROM
                rom_classification = getattr(analysis, 'rom_classification', 'unknown')
                quality_score = getattr(analysis, 'quality_score', 0)
                duration = getattr(analysis, 'duration_seconds', 0)
                
                # BILATERAL: Extraer max_rom_details de metadata si existe
                max_rom_details = None
                try:
                    if analysis.analysis_metadata:
                        metadata = json.loads(analysis.analysis_metadata)
                        rom_results = metadata.get('rom_results', {})
                        max_rom_details = rom_results.get('max_rom_details', None)
                        if max_rom_details and 'abduccion' in analysis.exercise_name.lower():
                            logger.info(f"DEBUG HISTORIAL - ID:{analysis.id}, max_rom_details={max_rom_details}")
                except Exception as e:
                    logger.error(f"Error extrayendo max_rom_details: {e}")
                    max_rom_details = None  # Fallback si no existe o hay error JSON
                
                # �🇧🇴 Convertir UTC a horario de Bolivia (UTC-4)
                bolivia_tz = pytz.timezone('America/La_Paz')
                if analysis.created_at.tzinfo is None:
                    # Si no tiene timezone, asumir que es UTC
                    utc_dt = pytz.utc.localize(analysis.created_at)
                else:
                    utc_dt = analysis.created_at.astimezone(pytz.utc)
                bolivia_dt = utc_dt.astimezone(bolivia_tz)
                
                history_item = {
                    'id': analysis.id,
                    'date': bolivia_dt.strftime('%Y-%m-%d %H:%M'),  # 🇧🇴 Horario de Bolivia
                    'exercise_name': analysis.exercise_name or f"{exercise.title()} de {segment.title()}",  # 🆕 Nombre del ejercicio
                    'max_rom': float(max_rom) if max_rom is not None else 0.0,
                    'max_rom_side': max_rom_side,  # 🆕 Incluir lado en respuesta
                    'rom_classification': rom_classification,
                    'current_angle': float(analysis.current_angle) if analysis.current_angle else 0.0,
                    'quality_score': float(quality_score) if quality_score else 0.0,
                    'duration': int(duration) if duration else 0
                }
                
                # 🆕 AGREGAR max_rom_details SOLO SI EXISTE (para abduction)
                if max_rom_details:
                    history_item['max_rom_details'] = max_rom_details
                
                history.append(history_item)
            except Exception as item_error:
                logger.warning(f"⚠️ Error procesando análisis {analysis.id}: {item_error}")
                continue
        
        return jsonify({
            'success': True,
            'history': history,
            'total_analyses': len(history)
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        # 🛡️ RESPUESTA DEFENSIVA: No romper el frontend
        return jsonify({
            'success': False, 
            'error': 'Error interno del servidor',
            'history': [],
            'total_analyses': 0,
            'debug_error': str(e) if app.debug else None
        }), 200  # ⚠️ 200 en lugar de 500 para no romper frontend

@app.route('/api/admin/force-migration', methods=['GET', 'POST'])
def force_migration():
    """🚨 ENDPOINT SIMPLE: Verificar/forzar migración"""
    try:
        from sqlalchemy import text
        
        with app.app_context():
            migration_log = []
            
            # 1. Crear tablas que no existen
            db.create_all()
            migration_log.append("✅ db.create_all() ejecutado")
            
            # 2. Agregar columna height_cm si no existe
            try:
                # Probar si existe
                db.session.execute(text("SELECT height_cm FROM user LIMIT 1"))
                migration_log.append("✅ user.height_cm ya existe")
            except:
                # No existe, agregarla
                db.session.execute(text("ALTER TABLE user ADD COLUMN height_cm REAL DEFAULT 170.0"))
                db.session.commit()
                migration_log.append("➕ user.height_cm AGREGADA")
            
            # 3. Agregar columnas ROM si no existen
            rom_columns = [
                ("max_rom_achieved", "REAL DEFAULT 0"),
                ("max_rom_side", "VARCHAR(10) DEFAULT 'ninguno'"),  # 🆕 Lado ROM
                ("calibration_angle", "REAL DEFAULT 0"), 
                ("rom_classification", "VARCHAR(20) DEFAULT 'unknown'"),
                ("best_frame_data", "TEXT")
            ]
            
            for col_name, col_def in rom_columns:
                try:
                    db.session.execute(text(f"SELECT {col_name} FROM analysis LIMIT 1"))
                    migration_log.append(f"✅ analysis.{col_name} ya existe")
                except:
                    db.session.execute(text(f"ALTER TABLE analysis ADD COLUMN {col_name} {col_def}"))
                    db.session.commit()
                    migration_log.append(f"➕ analysis.{col_name} AGREGADA")
            
            # 4. Crear admin si no existe
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', role='admin', height_cm=170.0)
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                migration_log.append("👤 Usuario admin CREADO")
            else:
                # Actualizar altura si es None
                if admin.height_cm is None:
                    admin.height_cm = 170.0
                    db.session.commit()
                    migration_log.append(f"📏 Admin altura actualizada: {admin.height_cm}")
                else:
                    migration_log.append(f"👤 Admin existe: altura={admin.height_cm}")
            
            # 5. Verificar funcionamiento
            user_count = User.query.count()
            
            return jsonify({
                'success': True,
                'message': 'Migración completada exitosamente',
                'user_count': user_count,
                'admin_height': admin.height_cm,
                'migration_log': migration_log
            })
                
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e),
            'migration_log': migration_log if 'migration_log' in locals() else []
        }), 500

# =============================================================================
# 🚀 INICIO DEL SERVIDOR
# =============================================================================

# =============================================================================
# ✅ APLICACIÓN LISTA - El servidor se inicia desde run.py
# =============================================================================
# 
# Para iniciar el servidor, ejecuta desde la raíz del proyecto:
#   python run.py
#
# El archivo run.py se encarga de:
# - Configurar el servidor Flask
# - Inicializar la base de datos
# - Crear usuarios de prueba
# - Manejar entornos (desarrollo/producción)
# ============================================================================="
# =============================================================================
# 🎛️ API PARA CONTROL DE SERVOS ESP32
# =============================================================================

@app.route('/api/servo/status', methods=['GET'])
@login_required
def get_servo_status():
    """Estado actual del sistema servo (mock/real)"""
    try:
        # En producción, esto consultaría el ESP32 real
        # Por ahora retornamos estado mock
        return jsonify({
            'status': 'connected',
            'tilt': 0,
            'pan': 0,
            'autoLevel': True,
            'gyroscope': {
                'x': 0.1,
                'y': -0.2,
                'z': 9.8
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servo/move', methods=['POST'])
@login_required 
def move_servo():
    """Mover servo específico"""
    try:
        data = request.get_json()
        servo_type = data.get('servo')  # 'pan' o 'tilt'
        direction = data.get('direction')  # 'left', 'right', 'up', 'down'
        continuous = data.get('continuous', False)
        
        # Log de la acción
        print(f"🎛️ Moviendo servo {servo_type} hacia {direction}")
        
        # En producción, aquí se enviaría comando al ESP32
        # Por ahora retornamos éxito
        return jsonify({
            'success': True,
            'servo': servo_type,
            'direction': direction,
            'message': f'Servo {servo_type} movido hacia {direction}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servo/position', methods=['POST'])
@login_required
def set_servo_position():
    """Establecer posición específica del servo"""
    try:
        data = request.get_json()
        servo_type = data.get('servo')
        angle = data.get('angle')
        
        # Validar rangos
        if servo_type == 'pan':
            angle = max(-90, min(90, angle))
        elif servo_type == 'tilt':
            angle = max(-30, min(30, angle))
        
        print(f"🎯 Estableciendo {servo_type} a {angle}°")
        
        # En producción, comando al ESP32
        return jsonify({
            'success': True,
            'servo': servo_type,
            'angle': angle,
            'message': f'Servo {servo_type} posicionado a {angle}°'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servo/auto-level', methods=['POST'])
@login_required
def toggle_auto_level():
    """Activar/desactivar nivelación automática"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        print(f"🎚️ Nivelación automática: {'ON' if enabled else 'OFF'}")
        
        return jsonify({
            'success': True,
            'autoLevel': enabled,
            'message': f'Nivelación automática {"activada" if enabled else "desactivada"}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servo/reset', methods=['POST'])
@login_required
def reset_servos():
    """Resetear servos a posición inicial"""
    try:
        print("🔄 Reseteando servos a posición inicial")
        
        return jsonify({
            'success': True,
            'pan': 0,
            'tilt': 0,
            'autoLevel': True,
            'message': 'Servos reseteados a posición inicial'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/biomech/height-recommendations', methods=['GET'])
@login_required
def get_height_recommendations():
    """Calcular alturas recomendadas según Drillis-Contini"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user or not user.height_cm:
            return jsonify({'error': 'Altura de usuario no disponible'}), 400
        
        height = user.height_cm
        
        # Fórmulas de Drillis & Contini (1966)
        recommendations = {
            'user_height': height,
            'segments': {
                'shoulder': {
                    'height_cm': round(height * 0.818),
                    'ratio': 0.818,
                    'description': 'Altura del hombro (acromion)'
                },
                'elbow': {
                    'height_cm': round(height * 0.630),
                    'ratio': 0.630,
                    'description': 'Altura del codo (epicóndilo lateral)'
                },
                'hip': {
                    'height_cm': round(height * 0.530),
                    'ratio': 0.530,
                    'description': 'Altura de la cadera (trocánter mayor)'
                },
                'knee': {
                    'height_cm': round(height * 0.285),
                    'ratio': 0.285,
                    'description': 'Altura de la rodilla (cóndilo lateral)'
                },
                'ankle': {
                    'height_cm': round(height * 0.039),
                    'ratio': 0.039,
                    'description': 'Altura del tobillo (maléolo lateral)'
                },
                'neck': {
                    'height_cm': round(height * 0.900),
                    'ratio': 0.900,
                    'description': 'Base del cuello (C7)'
                }
            },
            'reference': 'Drillis, R., & Contini, R. (1966). Body segment parameters. Technical Report 1166-03, NYU School of Engineering and Science.',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify(recommendations)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# ✅ FIN DE LA APLICACIÓN
# =============================================================================
#
# Este módulo define la aplicación Flask y todas sus rutas.
# Para iniciar el servidor, ejecuta: python run.py
#
# Desarrollado por: Equipo BioTrack
# Fecha: 2025
# =============================================================================

