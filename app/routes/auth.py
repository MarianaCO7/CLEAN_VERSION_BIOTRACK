"""
🔐 BLUEPRINT DE AUTENTICACIÓN - BIOTRACK
==========================================
Maneja login, logout y registro de usuarios

RUTAS:
- /login (GET, POST): Formulario de login
- /logout (GET): Cerrar sesión
- /register (GET, POST): Registro de nuevos usuarios (solo admin)

Autor: BIOTRACK Team
Fecha: 2025-11-14
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, current_app
)
from werkzeug.security import check_password_hash
from functools import wraps

# Crear blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ============================================================================
# DECORADORES
# ============================================================================

def login_required(f):
    """Decorador para requerir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador para requerir rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        
        db_manager = current_app.config.get('DB_MANAGER')
        user = db_manager.get_user_by_id(session['user_id'])
        
        if not user or user.role != 'admin':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login de usuarios
    
    GET: Muestra formulario de login
    POST: Procesa credenciales y autentica
    """
    
    # Si ya está autenticado, redirigir a dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '').strip()
        remember = request.form.get('remember', False)
        
        # Validación básica
        if not username or not password or not role:
            flash('Usuario, contraseña y rol son requeridos', 'danger')
            return render_template('auth/login.html')
        
        # Obtener database manager
        db_manager = current_app.config.get('DB_MANAGER')
        
        if not db_manager:
            flash('Error de conexión con la base de datos', 'danger')
            current_app.logger.error('DB_MANAGER no disponible en login')
            return render_template('auth/login.html')
        
        # Autenticar usuario
        user = db_manager.authenticate_user(username, password)
        
        if user:
            # Validar que el rol seleccionado coincida con el rol del usuario
            if user['role'] != role:
                flash(f'El rol seleccionado no corresponde a este usuario', 'danger')
                current_app.logger.warning(f"Intento de login con rol incorrecto: {username} (rol esperado: {user['role']}, rol seleccionado: {role})")
                return render_template('auth/login.html')
            
            # Login exitoso
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            
            # Hacer sesión permanente si marcó "recordarme"
            if remember:
                session.permanent = True
            
            # Log de actividad
            try:
                db_manager.log_action(
                    action='login',
                    user_id=user['id'],
                    details=f"Login exitoso de {username}",
                    ip_address=request.remote_addr
                )
            except Exception as e:
                current_app.logger.error(f"Error al registrar log: {e}")
            
            flash(f'Bienvenido, {user["full_name"]}!', 'success')
            current_app.logger.info(f"Login exitoso: {username} ({user['role']})")
            
            # Redirigir según rol
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            return redirect(url_for('main.dashboard'))
        
        else:
            # Login fallido
            flash('Usuario o contraseña incorrectos', 'danger')
            current_app.logger.warning(f"Intento de login fallido: {username}")
            
            # Log de intento fallido
            try:
                db_manager.log_action(
                    action='login_failed',
                    details=f"Intento de login fallido: {username}",
                    ip_address=request.remote_addr
                )
            except:
                pass
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """
    Cierra la sesión del usuario
    """
    
    # Log de logout
    if 'user_id' in session:
        db_manager = current_app.config.get('DB_MANAGER')
        try:
            db_manager.log_action(
                action='logout',
                user_id=session.get('user_id'),
                details=f"Logout de {session.get('username')}",
                ip_address=request.remote_addr
            )
        except:
            pass
    
    # Limpiar sesión
    username = session.get('username', 'Usuario')
    session.clear()
    
    flash(f'Sesión cerrada. Hasta pronto!', 'info')
    current_app.logger.info(f"Logout: {username}")
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    """
    Registro de nuevos usuarios (solo administrador)
    
    GET: Muestra formulario de registro
    POST: Crea nuevo usuario
    """
    
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'student')
        student_id = request.form.get('student_id', '').strip() or None
        program = request.form.get('program', '').strip() or None
        semester = request.form.get('semester', '') or None
        height = request.form.get('height', '') or None
        
        # Validaciones
        if not all([username, password, full_name, email]):
            flash('Todos los campos obligatorios deben ser completados', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('auth/register.html')
        
        # Obtener database manager
        db_manager = current_app.config.get('DB_MANAGER')
        
        # Verificar que no exista el usuario
        if db_manager.get_user_by_username(username):
            flash('El nombre de usuario ya existe', 'danger')
            return render_template('auth/register.html')
        
        if db_manager.get_user_by_email(email):
            flash('El email ya está registrado', 'danger')
            return render_template('auth/register.html')
        
        # Crear usuario
        try:
            user = db_manager.create_user(
                username=username,
                password=password,
                full_name=full_name,
                email=email,
                role=role,
                student_id=student_id,
                program=program,
                semester=int(semester) if semester else None,
                height=float(height) if height else None,
                created_by=session.get('user_id')
            )
            
            # Log de creación
            db_manager.log_action(
                action='create_user',
                user_id=session.get('user_id'),
                details=f"Usuario creado: {username} ({role})",
                ip_address=request.remote_addr
            )
            
            flash(f'Usuario {username} creado exitosamente', 'success')
            current_app.logger.info(f"Usuario creado: {username} por admin {session.get('username')}")
            
            return redirect(url_for('main.users'))
            
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'danger')
            current_app.logger.error(f"Error al crear usuario: {e}")
    
    return render_template('auth/register.html')
