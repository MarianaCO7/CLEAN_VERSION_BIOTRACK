"""
🔧 UTILITY: Detección de Perfil Verdadero por Profundidad Z

Funciones reutilizables para detectar si el usuario está en perfil verdadero
(un lado visible, otro oculto) usando la coordenada Z de MediaPipe.

Reutilizable por: shoulder_analyzer, elbow_analyzer, hip_analyzer, knee_analyzer
"""

def detect_profile_by_z_depth(
    point_distal_r, 
    point_distal_l, 
    point_proximal_r, 
    point_proximal_l,
    z_threshold=0.25,
    vis_threshold=0.4,
    debug=False
):
    """
    🎯 DETECCIÓN GENÉRICA de perfil verdadero usando profundidad Z
    
    Args:
        point_distal_r: Landmark distal derecho (ej: muñeca derecha)
        point_distal_l: Landmark distal izquierdo (ej: muñeca izquierda)
        point_proximal_r: Landmark proximal derecho (ej: hombro/codo derecho)
        point_proximal_l: Landmark proximal izquierdo (ej: hombro/codo izquierdo)
        z_threshold: Diferencia Z para considerar fuera de plano (default 0.25)
        vis_threshold: Threshold de visibility mínima (default 0.4)
        debug: Si True, imprime información de debugging
    
    Returns:
        str: 'RIGHT' (derecho visible), 'LEFT' (izquierdo visible), 
             'BILATERAL' (ambos visibles), 'NONE' (ninguno confiable)
    
    Lógica:
        - Calcula diferencia Z entre punto distal y proximal para cada lado
        - En perfil verdadero, lado oculto tiene Z muy diferente (> z_threshold)
        - En bilateral frontal, ambos lados tienen Z similar (< z_threshold)
    """
    
    # Calcular diferencia de profundidad normalizada
    # Z en MediaPipe: valores más negativos = más lejos de cámara
    z_diff_r = abs(point_distal_r.z - point_proximal_r.z)
    z_diff_l = abs(point_distal_l.z - point_proximal_l.z)
    
    # Verificar visibility
    vis_r = point_distal_r.visibility
    vis_l = point_distal_l.visibility
    
    # 🔇 DEBUG comentado para performance (se ejecuta cada frame)
    # if debug:
    #     print(f"🔍 DEBUG detect_profile_by_z_depth:")
    #     print(f"   point_distal_r: vis={vis_r:.2f}, z_diff={z_diff_r:.3f}")
    #     print(f"   point_distal_l: vis={vis_l:.2f}, z_diff={z_diff_l:.3f}")
    #     print(f"   thresholds: z={z_threshold}, vis={vis_threshold}")
    
    # Determinar si cada lado está en el mismo plano que su referencia
    r_in_plane = (z_diff_r < z_threshold and vis_r > vis_threshold)
    l_in_plane = (z_diff_l < z_threshold and vis_l > vis_threshold)
    
    # Decisión
    if r_in_plane and not l_in_plane:
        # if debug:
        #     print(f"   → PERFIL DERECHO detectado (izq fuera de plano z_diff={z_diff_l:.3f})")  # 🔇 Comentado - performance
        return 'RIGHT'
    elif l_in_plane and not r_in_plane:
        # if debug:
        #     print(f"   → PERFIL IZQUIERDO detectado (der fuera de plano z_diff={z_diff_r:.3f})")  # 🔇 Comentado - performance
        return 'LEFT'
    elif r_in_plane and l_in_plane:
        # if debug:
        #     print(f"   → BILATERAL detectado (ambos en plano)")  # 🔇 Comentado - performance
        return 'BILATERAL'
    else:
        # if debug:
        #     print(f"   → NINGÚN LADO CONFIABLE (ambos z_diff altos o vis bajas)")  # 🔇 Comentado - performance
        return 'NONE'


def get_z_threshold_for_joint(joint_type):
    """
    🎯 THRESHOLDS ESPECÍFICOS por tipo de articulación
    
    Args:
        joint_type: 'shoulder', 'elbow', 'hip', 'knee', 'ankle'
    
    Returns:
        float: Threshold Z óptimo para esa articulación
    
    Rationale:
        - Hombro: Alta variabilidad Z en perfil → 0.25
        - Codo: MÁS TOLERANTE que hombro (muñecas se mueven más) → 0.30
        - Cadera: Media variabilidad → 0.30 (más permisivo)
        - Rodilla/Tobillo: Baja necesidad (raramente en perfil) → 0.35
    """
    thresholds = {
        'shoulder': 0.25,  # MediaPipe detecta muñecas ocultas con Z diferente
        'elbow': 0.30,     # 🆕 MÁS TOLERANTE: Antebrazo tiene más movimiento Z natural
        'hip': 0.30,       # Caderas más estables, menos variación Z
        'knee': 0.35,      # Rodillas raramente fuera de frame en perfil
        'ankle': 0.35      # Tobillos casi siempre visibles
    }
    
    return thresholds.get(joint_type, 0.25)  # Default conservador


def should_use_profile_detection(joint_type, exercise_type):
    """
    🤔 ¿Esta combinación articulación-ejercicio NECESITA detección de perfil?
    
    Args:
        joint_type: 'shoulder', 'elbow', 'hip', 'knee', 'ankle'
        exercise_type: 'flexion', 'extension', 'abduction', etc.
    
    Returns:
        bool: True si debe usar detección de perfil, False si no aplica
    
    Rationale:
        - Flexión/Extensión de extremidades superiores: SÍ (común perfil)
        - Abducción: NO (siempre frontal)
        - Extremidades inferiores: RARO (casi siempre bilateral)
    """
    # Mapa de qué ejercicios típicamente usan perfil
    profile_exercises = {
        'shoulder': ['flexion', 'extension'],
        'elbow': ['flexion', 'extension'],
        'hip': ['flexion', 'extension'],  # A veces
        'knee': ['flexion'],               # Raramente
        'ankle': []                        # Casi nunca
    }
    
    applicable_exercises = profile_exercises.get(joint_type, [])
    return exercise_type in applicable_exercises
