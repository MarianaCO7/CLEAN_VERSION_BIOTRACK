"""
📋 CONFIG LOADER - CARGADOR DE CONFIGURACIÓN DE EJERCICIOS
=============================================================================
Módulo compartido para cargar configuraciones de exercises.json
Evita importaciones circulares entre app.py y handlers
=============================================================================
"""

import os
import json

def load_exercise_configuration(segment, exercise, config_dir=None):
    """
    📋 Cargar configuración específica de ejercicio desde JSON escalable
    
    Args:
        segment (str): Nombre del segmento ('shoulder', 'elbow', 'hip', 'knee', 'ankle')
        exercise (str): Nombre del ejercicio ('flexion', 'extension', 'rotation', etc.)
        config_dir (str, optional): Directorio donde buscar exercises.json. 
                                   Si no se proporciona, usa el directorio actual
    
    Returns:
        dict: Configuración combinada del segmento y ejercicio, o None si no existe
    """
    try:
        # Determinar ruta del archivo de configuración
        if config_dir is None:
            # Intentar desde la ubicación del módulo
            config_dir = os.path.dirname(os.path.abspath(__file__))
        
        config_path = os.path.join(config_dir, 'exercises.json')
        
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
            'plane': exercise_config['plane'],  # ⭐ ORIENTACIÓN AUTORITARIA
            'calculation_method': exercise_config['calculation_method'],
            'normal_range': exercise_config['normal_range'],
            'landmarks': exercise_config.get('landmarks', []),
            'camera_position': exercise_config.get('camera_position', 'lateral'),
            'reference_frame': exercise_config.get('reference_frame', 'body'),
            'movement_description': exercise_config.get('movement_description', ''),
            'common_errors': exercise_config.get('common_errors', []),
            'tips': exercise_config.get('tips', [])
        }
        
        return combined_config
        
    except FileNotFoundError as e:
        print(f"❌ Error de archivo: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al cargar configuración: {e}")
        return None


def get_exercise_orientation(segment, exercise, config_dir=None):
    """
    🧭 Obtener SOLO la orientación (plane) de un ejercicio
    
    Args:
        segment (str): Nombre del segmento
        exercise (str): Nombre del ejercicio
        config_dir (str, optional): Directorio de configuración
    
    Returns:
        str: Orientación en mayúsculas ('SAGITAL', 'FRONTAL', 'TRANSVERSAL') o 'SAGITAL' por defecto
    """
    config = load_exercise_configuration(segment, exercise, config_dir)
    if config and 'plane' in config:
        return config['plane'].upper()
    return 'SAGITAL'  # Default


def get_all_exercises_for_segment(segment, config_dir=None):
    """
    📚 Obtener todos los ejercicios disponibles para un segmento
    
    Args:
        segment (str): Nombre del segmento
        config_dir (str, optional): Directorio de configuración
    
    Returns:
        dict: Diccionario con todos los ejercicios del segmento
    """
    try:
        if config_dir is None:
            config_dir = os.path.dirname(os.path.abspath(__file__))
        
        config_path = os.path.join(config_dir, 'exercises.json')
        
        if not os.path.exists(config_path):
            print(f"❌ Archivo de configuración no encontrado: {config_path}")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        
        if 'segments' not in configs:
            return {}
        
        segment_config = configs['segments'].get(segment)
        if not segment_config:
            return {}
            
        return segment_config.get('exercises', {})
        
    except Exception as e:
        print(f"❌ Error al cargar ejercicios: {e}")
        return {}
