"""
Configuración de Logging para BioTrack
======================================
Sistema de logging unificado para toda la aplicación
"""

import logging
import sys
from datetime import datetime

def setup_logger(name, level=logging.INFO):
    """
    Configura un logger con formato estándar
    
    Args:
        name: Nombre del módulo/logger
        level: Nivel de logging (default: INFO)
        
    Returns:
        Logger configurado
    """
    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicados
    if logger.handlers:
        return logger
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

# Logger por defecto para la aplicación
app_logger = setup_logger('biotrack', logging.INFO)
