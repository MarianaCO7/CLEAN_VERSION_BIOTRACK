#!/usr/bin/env python3
"""
🚀 BIOTRACK LAUNCHER
===================
Script de inicio para la aplicación BioTrack

Funcionalidades:
- Verificaciones previas del sistema
- Comprobación de base de datos
- Validación de directorios
- Información de inicio útil
- Manejo de excepciones

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# CONFIGURACIÓN DE PATHS
# ==============================================================================

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Agregar al PYTHONPATH
sys.path.insert(0, str(BASE_DIR))


# ==============================================================================
# FUNCIONES DE VERIFICACIÓN
# ==============================================================================

def check_prerequisites():
    """
    Verifica que todos los prerequisitos estén cumplidos
    
    Returns:
        bool: True si todo está OK, False si hay errores
    """
    print("="*70)
    print("🔍 VERIFICANDO PREREQUISITOS DEL SISTEMA")
    print("="*70)
    
    all_ok = True
    
    # 1. Verificar base de datos
    db_path = BASE_DIR / 'database' / 'biotrack.db'
    if db_path.exists():
        print(f"✅ Base de datos encontrada: {db_path}")
    else:
        print(f"❌ Base de datos NO encontrada: {db_path}")
        print(f"   Ejecuta: python database/init_database.py")
        all_ok = False
    
    # 2. Verificar directorios requeridos
    required_dirs = [
        'app/static/uploads',
        'app/static/css',
        'app/static/js',
        'app/static/images',
        'app/templates',
        'database',
        'logs'
    ]
    
    for dir_path in required_dirs:
        full_path = BASE_DIR / dir_path
        if full_path.exists():
            print(f"✅ Directorio OK: {dir_path}")
        else:
            print(f"⚠️  Creando directorio: {dir_path}")
            full_path.mkdir(parents=True, exist_ok=True)
    
    # 3. Verificar archivos críticos
    critical_files = [
        'app/config.py',
        'app/app.py',
        'app/routes/auth.py',
        'app/routes/main.py',
        'app/routes/api.py',
        'database/database_manager.py'
    ]
    
    for file_path in critical_files:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            print(f"✅ Archivo OK: {file_path}")
        else:
            print(f"❌ Archivo NO encontrado: {file_path}")
            all_ok = False
    
    print("="*70)
    return all_ok


def print_startup_info():
    """
    Muestra información útil de inicio
    """
    print("\n" + "="*70)
    print("🎯 BIOTRACK - SISTEMA DE ANÁLISIS BIOMECÁNICO")
    print("="*70)
    print("\n📍 INFORMACIÓN DE ACCESO:")
    print("-" * 70)
    print(f"   🌐 URL Local:      http://127.0.0.1:5000")
    print(f"   🌐 URL Red:        http://localhost:5000")
    print(f"   📁 Directorio:     {BASE_DIR}")
    print(f"   💾 Base de datos:  database/biotrack.db")
    
    print("\n🔑 CREDENCIALES DE PRUEBA:")
    print("-" * 70)
    print("   👤 Admin:        admin / test123")
    print("   👤 Estudiante:   carlos.mendez / test123")
    print("   👤 Estudiante:   ana.lopez / test123")
    print("   👤 Estudiante:   juan.garcia / test123")
    print("   👤 Estudiante:   maria.torres / test123")
    
    print("\n📊 CARACTERÍSTICAS:")
    print("-" * 70)
    print("   ✅ Análisis biomecánico con MediaPipe")
    print("   ✅ Medición de rangos articulares (ROM)")
    print("   ✅ Gestión de usuarios y sesiones")
    print("   ✅ Reportes PDF de análisis")
    print("   ✅ Control de altura de cámara (ESP32)")
    print("   ✅ Guía de voz en tiempo real")
    
    print("\n⚠️  IMPORTANTE:")
    print("-" * 70)
    print("   • Asegúrate de tener una cámara web conectada")
    print("   • Usa Chrome o Firefox para mejor compatibilidad")
    print("   • Buena iluminación mejora la detección")
    print("   • Presiona Ctrl+C para detener el servidor")
    
    print("\n" + "="*70)
    print("🚀 INICIANDO SERVIDOR...")
    print("="*70 + "\n")


def print_shutdown_info():
    """
    Muestra información al cerrar el servidor
    """
    print("\n" + "="*70)
    print("👋 BIOTRACK CERRADO")
    print("="*70)
    print("   ✅ Servidor detenido correctamente")
    print("   📁 Logs guardados en: logs/")
    print("   💾 Base de datos cerrada")
    print("\n   ¡Hasta pronto! 🏃‍♂️\n")


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """
    Función principal de inicio
    """
    try:
        # Verificar prerequisitos
        if not check_prerequisites():
            print("\n❌ ERROR: Faltan prerequisitos. Revisa los mensajes arriba.")
            print("   Ejecuta primero: python database/init_database.py\n")
            sys.exit(1)
        
        # Mostrar información de inicio
        print_startup_info()
        
        # Importar y crear aplicación Flask
        from app.app import create_app
        
        # Crear app con configuración de desarrollo
        app = create_app('development')
        
        # Configuración del servidor
        HOST = '0.0.0.0'  # Accesible desde cualquier interfaz
        PORT = 5000
        DEBUG = True
        
        # Iniciar servidor
        app.run(
            host=HOST,
            port=PORT,
            debug=DEBUG,
            use_reloader=True,  # Auto-reload en cambios de código
            threaded=True       # Permitir múltiples threads
        )
        
    except KeyboardInterrupt:
        # Ctrl+C presionado
        print_shutdown_info()
        sys.exit(0)
        
    except ImportError as e:
        print(f"\n❌ ERROR DE IMPORTACIÓN: {e}")
        print("   Asegúrate de que todas las dependencias estén instaladas:")
        print("   pip install -r requirements.txt\n")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        print("\n   Revisa los logs en: logs/errors.log\n")
        sys.exit(1)


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

if __name__ == '__main__':
    main()
