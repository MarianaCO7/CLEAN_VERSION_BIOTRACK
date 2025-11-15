#!/usr/bin/env python3
"""
🗄️ DATABASE INITIALIZATION SCRIPT - SISTEMA EDUCATIVO
========================================================
Inicializa la base de datos del sistema biomecánico educativo desde cero.

ENFOQUE EDUCATIVO:
- 2 roles: admin y student
- Tabla 'subject' (no 'patient')
- Campos académicos: student_id, program, semester
- Sin información médica/clínica

Uso:
    python init_database.py [--schema-only] [--with-seeds]

Opciones:
    --schema-only   Solo crear estructura (sin datos de ejemplo)
    --with-seeds    Crear estructura + datos de ejemplo (por defecto)
    --db PATH       Ruta personalizada a la base de datos (default: instance/biotrack.db)

Ejemplos:
    python init_database.py                          # Estructura + datos de ejemplo
    python init_database.py --schema-only            # Solo estructura
    python init_database.py --db test.db --with-seeds  # BD personalizada con datos
"""

import sqlite3
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def print_header(text):
    """Imprime encabezado formateado"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"✅ {text}")


def print_error(text):
    """Imprime mensaje de error"""
    print(f"❌ {text}")


def print_info(text):
    """Imprime mensaje informativo"""
    print(f"ℹ️  {text}")


def execute_sql_file(cursor, sql_file_path):
    """
    Ejecuta un archivo SQL
    
    Args:
        cursor: Cursor de SQLite
        sql_file_path: Ruta al archivo .sql
    
    Returns:
        bool: True si se ejecutó correctamente
    """
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        cursor.executescript(sql_script)
        return True
    except FileNotFoundError:
        print_error(f"Archivo no encontrado: {sql_file_path}")
        return False
    except sqlite3.Error as e:
        print_error(f"Error SQL: {e}")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False


def create_backup(db_path):
    """
    Crea un backup de la base de datos existente
    
    Args:
        db_path: Ruta a la base de datos
    """
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{db_path}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print_success(f"Backup creado: {backup_path}")
            return backup_path
        except Exception as e:
            print_error(f"No se pudo crear backup: {e}")
            return None
    return None


def verify_database(db_path):
    """
    Verifica la estructura de la base de datos creada
    
    Args:
        db_path: Ruta a la base de datos
    """
    print_header("Verificando Base de Datos")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar tablas
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print_info(f"Tablas creadas: {table_count}")
        
        # Listar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print("\n📋 Tablas encontradas:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            row_count = cursor.fetchone()[0]
            print(f"   • {table[0]}: {row_count} registros")
        
        # Contar índices
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
        index_count = cursor.fetchone()[0]
        print_info(f"\n🔍 Índices creados: {index_count}")
        
        # Contar vistas
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        view_count = cursor.fetchone()[0]
        print_info(f"👁️  Vistas creadas: {view_count}")
        
        # Contar triggers
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
        trigger_count = cursor.fetchone()[0]
        print_info(f"⚡ Triggers creados: {trigger_count}")
        
        conn.close()
        print_success("\nBase de datos verificada correctamente")
        
    except sqlite3.Error as e:
        print_error(f"Error al verificar base de datos: {e}")


def show_test_users():
    """Muestra información de los usuarios de prueba"""
    print_header("Usuarios de Prueba Creados - Sistema Educativo")
    print("""
┌─────────────────┬───────────────────────────────┬────────────┬──────────────────────┬──────────┐
│ Usuario         │ Nombre Completo               │ Rol        │ Programa             │ Semestre │
├─────────────────┼───────────────────────────────┼────────────┼──────────────────────┼──────────┤
│ admin           │ Administrador del Sistema     │ Admin      │ -                    │ -        │
│ carlos.mendez   │ Carlos Andrés Méndez Torres   │ Estudiante │ Ing. Biomédica       │ 8        │
│ maria.rodriguez │ María Fernanda Rodríguez      │ Estudiante │ Fisioterapia         │ 6        │
│ juan.garcia     │ Juan Pablo García Ramírez     │ Estudiante │ Kinesiología         │ 5        │
│ laura.martinez  │ Laura Camila Martínez (TESIS) │ Estudiante │ Ing. Biomédica       │ 10       │
└─────────────────┴───────────────────────────────┴────────────┴──────────────────────┴──────────┘

🔑 Contraseña para todos: test123

📚 ENFOQUE EDUCATIVO:
   • Tabla 'subject' (no 'patient')
   • Campos académicos: student_id, program, semester
   • Sin información médica/clínica
   • Vista de actividad de estudiantes

⚠️  IMPORTANTE: Cambiar estas contraseñas en producción
    """)


def main():
    """Función principal"""
    # Configurar argumentos
    parser = argparse.ArgumentParser(
        description='Inicializa la base de datos del sistema biomecánico'
    )
    parser.add_argument(
        '--schema-only',
        action='store_true',
        help='Solo crear estructura (sin datos de ejemplo)'
    )
    parser.add_argument(
        '--with-seeds',
        action='store_true',
        default=True,
        help='Crear estructura + datos de ejemplo (por defecto)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='instance/biotrack.db',
        help='Ruta a la base de datos (default: instance/biotrack.db)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='No crear backup de la base de datos existente'
    )
    
    args = parser.parse_args()
    
    # Rutas a los archivos SQL
    script_dir = Path(__file__).parent
    schema_file = script_dir / 'schema.sql'
    seeds_file = script_dir / 'seeds.sql'
    
    # Ruta a la base de datos
    db_path = args.db
    db_dir = os.path.dirname(db_path)
    
    # Crear directorio si no existe
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print_success(f"Directorio creado: {db_dir}")
    
    print_header("Inicialización de Base de Datos - Sistema Biomecánico Educativo v9.5")
    print_info(f"Base de datos: {db_path}")
    print_info("Enfoque: Educativo (admin + estudiantes)")

    
    # Crear backup si existe base de datos
    if not args.no_backup:
        create_backup(db_path)
    
    # Eliminar base de datos existente
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print_success("Base de datos anterior eliminada")
        except Exception as e:
            print_error(f"No se pudo eliminar base de datos: {e}")
            return 1
    
    # Conectar a la base de datos
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print_success("Conexión establecida")
    except sqlite3.Error as e:
        print_error(f"Error al conectar: {e}")
        return 1
    
    # Ejecutar schema.sql
    print_header("Creando Estructura (schema.sql)")
    if execute_sql_file(cursor, schema_file):
        conn.commit()
        print_success("Estructura creada correctamente")
    else:
        conn.close()
        return 1
    
    # Ejecutar seeds.sql si no es --schema-only
    if not args.schema_only:
        print_header("Insertando Datos de Ejemplo (seeds.sql)")
        if execute_sql_file(cursor, seeds_file):
            conn.commit()
            print_success("Datos de ejemplo insertados correctamente")
            show_test_users()
        else:
            print_error("Error al insertar datos de ejemplo")
            conn.close()
            return 1
    
    # Cerrar conexión
    conn.close()
    
    # Verificar base de datos
    verify_database(db_path)
    
    print_header("✅ Inicialización Completada")
    print_info(f"Base de datos lista en: {db_path}")
    
    if not args.schema_only:
        print_info("Datos de ejemplo disponibles para testing educativo")
        print("\n💡 Siguiente paso:")
        print("   python app.py")
        print("   Luego inicia sesión con: admin / test123")
        print("   O como estudiante: carlos.mendez / test123")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
