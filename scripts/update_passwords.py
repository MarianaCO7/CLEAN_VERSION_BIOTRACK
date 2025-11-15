#!/usr/bin/env python3
"""
🔐 SCRIPT PARA ACTUALIZAR PASSWORDS EN LA BASE DE DATOS
========================================================
Actualiza los passwords de los usuarios de prueba con hashes válidos

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from werkzeug.security import generate_password_hash
from database.database_manager import get_db_manager

def update_passwords():
    """Actualiza todos los passwords de prueba a 'test123'"""
    
    print("=" * 70)
    print("🔐 ACTUALIZANDO PASSWORDS DE USUARIOS DE PRUEBA")
    print("=" * 70)
    
    # Obtener database manager
    db_path = BASE_DIR / 'database' / 'biotrack.db'
    db_manager = get_db_manager(str(db_path))
    
    # Password común para todos
    password = 'test123'
    password_hash = generate_password_hash(password)
    
    # Lista de usuarios a actualizar
    users = [
        {'id': 1, 'username': 'admin'},
        {'id': 2, 'username': 'carlos.mendez'},
        {'id': 3, 'username': 'ana.lopez'},
        {'id': 4, 'username': 'juan.garcia'},
        {'id': 5, 'username': 'maria.torres'}
    ]
    
    print(f"\n📝 Password a establecer: {password}")
    print(f"🔒 Hash generado: {password_hash[:50]}...")
    print("\n" + "-" * 70)
    
    # Actualizar cada usuario
    with db_manager.get_session() as session:
        for user_data in users:
            from database.database_manager import User
            user = session.query(User).filter_by(id=user_data['id']).first()
            
            if user:
                user.password_hash = password_hash
                print(f"✅ Usuario actualizado: {user_data['username']:20} (ID: {user_data['id']})")
            else:
                print(f"⚠️  Usuario no encontrado: {user_data['username']:20} (ID: {user_data['id']})")
        
        session.commit()
    
    print("-" * 70)
    print("\n✅ PASSWORDS ACTUALIZADOS EXITOSAMENTE")
    print("\n🔑 Credenciales de prueba:")
    print("-" * 70)
    for user_data in users:
        print(f"   • {user_data['username']:20} / {password}")
    print("-" * 70)
    print("\n💡 Ahora puedes iniciar sesión con estas credenciales\n")

if __name__ == '__main__':
    try:
        update_passwords()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
