/**
 * CAMERA SETTINGS MANAGER
 * Sistema de configuracion de camara para Railway streaming
 * Permite ajustar resolucion, FPS, calidad JPEG y seleccion de camara
 */

// =============================================================================
// 🚀 FUNCIÓN DE PRE-CARGA DE CÁMARAS AL ABRIR PÁGINA
// =============================================================================
// IMPORTANTE: Esto NO inicia ningún stream, solo detecta hardware disponible
// El stream SOLO se inicia cuando el usuario presiona "Iniciar Análisis"

// Variable global para almacenar cámaras detectadas
window.availableCameras = [];
window.cameraPreloadDone = false;

/**
 * 🔍 Pre-cargar cámaras al abrir la página
 * Detecta hardware y auto-selecciona la mejor cámara
 * NO INICIA STREAM - Solo prepara hardware para análisis posterior
 */
async function preloadCamerasOnPageLoad() {
    // 🔒 SESSION 4 FIX: Prevenir ejecuciones múltiples
    if (window.cameraScanning) {
        console.log('⏭️ [PRE-LOAD] Escaneo ya en progreso, omitiendo duplicado...');
        return window.availableCameras || [];
    }
    
    // 🆕 VERIFICAR SI YA TENEMOS CÁMARAS CARGADAS EN MEMORIA
    if (window.availableCameras && window.availableCameras.length > 0 && window.cameraPreloadDone) {
        console.log('✅ [PRE-LOAD SKIP] Cámaras ya cargadas en memoria:', window.availableCameras.length);
        updateStartButtonStatus('ready');
        return window.availableCameras;
    }
    
    console.log("🔍 [PRE-LOAD] Iniciando detección de cámaras...");
    
    // 🚀 SESSION 4: Marcar como "escaneando" para que botón espere
    window.cameraScanning = true;
    updateStartButtonStatus('scanning');
    
    // 🎯 SESSION 2: Verificar si hay cámara guardada en LocalStorage
    try {
        const storageKey = 'biomech_camera_settings';
        const savedData = localStorage.getItem(storageKey);
        
        if (savedData) {
            const settings = JSON.parse(savedData);
            const savedDeviceId = settings.deviceId;
            
            // 🆕 VERIFICAR TIMESTAMP - Solo usar si es reciente (< 10 minutos)
            const now = Date.now();
            const savedTimestamp = settings.timestamp || 0;
            
            // 🛡️ VALIDAR que el timestamp es válido (no puede ser más reciente que ahora, ni de hace más de 1 día)
            const ONE_DAY = 24 * 60 * 60 * 1000;
            if (savedTimestamp > now || savedTimestamp < (now - ONE_DAY)) {
                console.warn(`⚠️ [PRE-LOAD] Timestamp corrupto (${savedTimestamp}), limpiando localStorage...`);
                localStorage.removeItem(storageKey);
                // Continuar con escaneo completo
            } else {
                const cameraAge = now - savedTimestamp;
                const TEN_MINUTES = 10 * 60 * 1000;
                
                if (cameraAge > TEN_MINUTES) {
                    console.log(`⏰ [PRE-LOAD] Cámara guardada expiró (${Math.floor(cameraAge/1000/60)} min), reescaneando...`);
                    localStorage.removeItem(storageKey);  // 🧹 Limpiar datos expirados
                    // Continuar con escaneo completo
                } else if (savedDeviceId !== null && 
                    savedDeviceId !== undefined && 
                    savedDeviceId !== 'undefined' &&
                    savedDeviceId !== 'auto') {
                    
                    // ✅ HAY CÁMARA GUARDADA RECIENTE - USARLA DIRECTAMENTE SIN ESCANEAR
                    console.log(`✅ [PRE-LOAD CACHE] Usando cámara de localStorage: ${settings.deviceLabel} (ID: ${savedDeviceId})`);
                    console.log(`   ⏱️ Guardada hace ${Math.floor(cameraAge/1000)} segundos (válida por 10 min)`);
                    
                    // Crear objeto de cámara desde localStorage
                    const cachedCamera = {
                        id: parseInt(savedDeviceId),
                        pythonCameraId: parseInt(savedDeviceId),
                        name: settings.deviceLabel || `Cámara ${savedDeviceId}`,
                        recommended: true,
                        from_cache: true
                    };
                    
                    window.availableCameras = [cachedCamera];
                    window.cameraPreloadDone = true;
                    window.cameraScanning = false;
                    
                    showCameraStatus('success', `✅ Cámara lista: ${cachedCamera.name} (caché)`);
                    updateStartButtonStatus('ready');
                    
                    return [cachedCamera];
                }
            }
        } else {
            console.log('ℹ️ [PRE-LOAD] No hay cámara guardada en localStorage, escaneando...');
        }
    } catch (e) {
        console.warn('⚠️ [PRE-LOAD] Error con SESSION 2:', e);
        showCameraStatus('error', 'Error al validar cámara guardada, escaneando...');
    }
    
    // 🔄 ESCANEO COMPLETO (primera vez o fallback)
    try {
        // 🎨 SESSION 3: UI Feedback - Escaneando (REMOVIDO - usuario no quiere ver esto)
        // showCameraStatus('info', '🔍 Escaneando cámaras disponibles...');
        
        const response = await fetch('/api/preload_cameras', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.cameras) {
            window.availableCameras = data.cameras;
            window.cameraPreloadDone = true;
            window.cameraScanning = false;  // 🚀 SESSION 4: Escaneo completado
            
            console.log(`✅ [PRE-LOAD] ${data.cameras.length} cámaras detectadas:`, data.cameras);
            
            // 🆕 FIX: Buscar CUALQUIER cámara, no solo "recomendadas" (puede que todas sean baja resolución)
            const cameraToSave = data.cameras.find(cam => cam.recommended) || data.cameras[0];
            
            if (cameraToSave) {
                const isRecommended = cameraToSave.recommended ? '✅ RECOMENDADA' : '⚠️ resolución baja pero funcional';
                console.log(`🎯 [PRE-LOAD] Cámara auto-seleccionada (${isRecommended}): ${cameraToSave.name} (ID: ${cameraToSave.id})`);
                showCameraStatus('success', `✅ Cámara detectada: ${cameraToSave.name}`);
                
                // 💾 GUARDAR en LocalStorage para evitar re-escaneos
                try {
                    const storageKey = 'biomech_camera_settings';
                    const cameraSettings = {
                        deviceId: cameraToSave.pythonCameraId || cameraToSave.id,
                        deviceLabel: cameraToSave.name || `Cámara ${cameraToSave.id}`,
                        isAutomatic: true,  // Marca que fue seleccionada automáticamente
                        timestamp: Date.now()
                    };
                    
                    console.log(`💾 [PRE-LOAD] Intentando guardar en localStorage:`, cameraSettings);
                    localStorage.setItem(storageKey, JSON.stringify(cameraSettings));
                    
                    // 🧪 VERIFICAR que se guardó correctamente
                    const verify = localStorage.getItem(storageKey);
                    if (verify) {
                        console.log(`✅ [PRE-LOAD] Cámara guardada EXITOSAMENTE en localStorage`);
                        console.log(`   📦 Verificación:`, JSON.parse(verify));
                    } else {
                        console.error(`❌ [PRE-LOAD] FALLÓ el guardado en localStorage (verify = null)`);
                    }
                } catch (e) {
                    console.error('❌ [PRE-LOAD] ERROR guardando en localStorage:', e);
                    console.error('   Stack:', e.stack);
                }
            } else {
                console.error('❌ [PRE-LOAD] No se detectaron cámaras para guardar');
            }
            
            // Actualizar UI si existe el dropdown de cámaras
            updateCameraDropdownIfExists(data.cameras);
            
            // 🆕 HABILITAR BOTÓN DE INICIO después de pre-carga exitosa
            updateStartButtonStatus('ready');
            
            return data.cameras;
            
        } else {
            // 🎨 SESSION 3: Error handling - No cameras found
            console.warn(`⚠️ [PRE-LOAD] No se detectaron cámaras: ${data.message}`);
            showCameraStatus('error', '❌ No se detectaron cámaras disponibles');
            showRetryButton();  // 🆕 Mostrar botón de retry
            window.availableCameras = [];
            window.cameraScanning = false;  // 🚀 SESSION 4: Escaneo completado (con error)
            
            // 🆕 HABILITAR BOTÓN incluso sin cámaras (usará fallback)
            updateStartButtonStatus('ready');
            
            return [];
        }
        
    } catch (error) {
        // 🎨 SESSION 3: Error handling - Network or server error
        console.error("❌ [PRE-LOAD] Error detectando cámaras:", error);
        showCameraStatus('error', '❌ Error de conexión al detectar cámaras');
        showRetryButton();  // 🆕 Mostrar botón de retry
        window.availableCameras = [];
        window.cameraScanning = false;  // 🚀 SESSION 4: Escaneo completado (con error)
        
        // 🆕 HABILITAR BOTÓN incluso con error (usará fallback cámara 0)
        updateStartButtonStatus('ready');
        
        return [];
    }
}

/**
 * 🔄 Actualizar dropdown de cámaras si existe en la UI
 */
function updateCameraDropdownIfExists(cameras) {
    // Buscar dropdown de cámaras (puede variar según UI)
    const cameraSelect = document.querySelector('#cameraSelect, select[name="camera"], .camera-selector');
    
    if (!cameraSelect) {
        console.log("ℹ️ [PRE-LOAD] No se encontró dropdown de cámaras (puede estar en modal)");
        return;
    }
    
    // Limpiar opciones actuales
    cameraSelect.innerHTML = '';
    
    // Agregar opción de automático
    const autoOption = document.createElement('option');
    autoOption.value = 'auto';
    autoOption.textContent = '🎯 Automático (Recomendado)';
    cameraSelect.appendChild(autoOption);
    
    // Agregar cada cámara detectada
    cameras.forEach(camera => {
        const option = document.createElement('option');
        option.value = camera.id;
        option.textContent = `${camera.recommended ? '⭐ ' : ''}${camera.name} (${camera.resolution})`;
        
        if (camera.recommended) {
            option.selected = true;
        }
        
        cameraSelect.appendChild(option);
    });
    
    console.log("✅ [PRE-LOAD] Dropdown de cámaras actualizado");
}

/**
 * 🎯 Cambiar cámara manualmente (llamado desde UI, ej: gear icon)
 */
async function changeCameraManually(cameraId, jointType) {
    console.log(`🎯 [CAMBIO MANUAL] Usuario selecciona cámara ${cameraId} para ${jointType}`);
    
    try {
        const response = await fetch(`/api/set_preselected_camera/${jointType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                camera_id: cameraId,
                camera_info: {
                    source: 'USER_MANUAL_SELECTION',
                    timestamp: Date.now(),
                    joint_type: jointType
                }
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ [CAMBIO MANUAL] Cámara cambiada: ${data.message}`);
            
            // Mostrar notificación al usuario
            showCameraChangeNotification(data.message);
            
            return true;
        } else {
            console.error(`❌ [CAMBIO MANUAL] Error: ${data.error}`);
            showCameraChangeNotification(`Error: ${data.error}`, 'error');
            return false;
        }
        
    } catch (error) {
        console.error("❌ [CAMBIO MANUAL] Error cambiando cámara:", error);
        showCameraChangeNotification("Error de conexión al cambiar cámara", 'error');
        return false;
    }
}

/**
 * 📢 Mostrar notificación de cambio de cámara
 */
function showCameraChangeNotification(message, type = 'success') {
    // Buscar contenedor de notificaciones (puede variar según UI)
    let notification = document.querySelector('.camera-notification');
    
    if (!notification) {
        // Crear notificación si no existe
        notification = document.createElement('div');
        notification.className = 'camera-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            background: ${type === 'success' ? '#00f5d4' : '#ff6b6b'};
            color: #0a0a0a;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);
    }
    
    notification.textContent = message;
    notification.style.display = 'block';
    
    // Auto-ocultar después de 3 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            notification.style.display = 'none';
        }, 300);
    }, 3000);
}

/**
 * ✅ Habilitar botón de inicio después de pre-carga
 */
function enableStartButton() {
    updateStartButtonStatus('ready');
}

/**
 * 🚀 SESSION 4: Actualizar estado del botón "Iniciar Análisis"
 * @param {string} status - 'scanning' | 'ready' | 'disabled'
 */
function updateStartButtonStatus(status) {
    const startBtn = document.getElementById('startAnalysisBtn');
    
    if (!startBtn) return;
    
    switch (status) {
        case 'scanning':
            startBtn.disabled = true;
            startBtn.style.opacity = '0.6';
            startBtn.style.cursor = 'wait';
            startBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Detectando cámaras...';
            console.log("⏳ [SESSION 4] Botón de inicio: Esperando detección de cámaras");
            break;
            
        case 'ready':
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
            startBtn.style.cursor = 'pointer';
            startBtn.innerHTML = '<i class="bi bi-play-circle"></i> Iniciar Análisis';
            console.log("✅ [SESSION 4] Botón de inicio HABILITADO - Cámaras listas");
            break;
            
        case 'disabled':
            startBtn.disabled = true;
            startBtn.style.opacity = '0.5';
            startBtn.style.cursor = 'not-allowed';
            startBtn.innerHTML = '<i class="bi bi-exclamation-circle"></i> No disponible';
            console.log("❌ [SESSION 4] Botón de inicio DESHABILITADO");
            break;
    }
}

// =============================================================================
// 🎬 INICIALIZACIÓN AUTOMÁTICA AL CARGAR PÁGINA
// =============================================================================
// EJECUTAR PRE-CARGA SOLO UNA VEZ cuando la página termina de cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log("📄 [PAGE LOAD] Página cargada, iniciando pre-carga de cámaras...");
        preloadCamerasOnPageLoad();
    });
} else {
    // Página ya cargada, ejecutar inmediatamente
    console.log("📄 [PAGE LOAD] Página ya cargada, iniciando pre-carga de cámaras...");
    preloadCamerasOnPageLoad();
}

// =============================================================================
// 📷 CLASE CAMERA SETTINGS (CÓDIGO EXISTENTE)
// =============================================================================

class CameraSettings {
    constructor() {
        this.storageKey = 'biomech_camera_settings';
        this.version = '1.0';
        
        // CONSTANTES - Accesibles desde la instancia
        this.RESOLUTION_OPTIONS = {
            '360p': { width: 480, height: 360 },
            '480p': { width: 640, height: 480 },
            '720p': { width: 1280, height: 720 },
            '1080p': { width: 1920, height: 1080 }
        };
        
        this.FPS_OPTIONS = [1, 2, 3, 5, 10, 15, 20, 25, 30];
        
        this.QUALITY_OPTIONS = [40, 50, 60, 70, 80, 90, 100];
        
        this.CAMERA_PRESETS = {
            slow: {
                name: 'Red Lenta',
                resolution: '360p',
                fps: 1,
                quality: 50
            },
            standard: {
                name: 'Estandar',
                resolution: '480p',
                fps: 25,
                quality: 60
            },
            high: {
                name: 'Alta Calidad',
                resolution: '720p',
                fps: 30,
                quality: 80
            },
            custom: {
                name: 'Personalizado',
                custom: true
            }
        };
        
        // Cargar configuracion guardada o usar defaults
        this.settings = this.loadSettings();
        
        // Detectar si es movil (para defaults diferentes)
        this.isMobile = this.detectMobile();
    }
    
    /**
     * Detectar si es dispositivo movil
     */
    detectMobile() {
        const userAgent = navigator.userAgent || navigator.vendor || window.opera;
        const mobileIndicators = [
            /Android/i, /webOS/i, /iPhone/i, /iPad/i, /iPod/i,
            /BlackBerry/i, /Windows Phone/i, /Mobile/i
        ];
        
        const isMobileUA = mobileIndicators.some(indicator => indicator.test(userAgent));
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isSmallScreen = window.screen.width <= 768;
        
        return isMobileUA || (isTouchDevice && isSmallScreen);
    }
    
    /**
     * Obtener configuracion por defecto (valores actuales del sistema)
     */
    getDefaultSettings() {
        return {
            version: this.version,
            deviceId: null,
            deviceLabel: 'Automatico',
            resolution: {
                value: '480p',
                width: 640,
                height: 480
            },
            fps: this.isMobile ? 2 : 25,  // Actual: 2 movil, 25 desktop
            quality: this.isMobile ? 50 : 60,  // Actual: 50% movil, 60% desktop
            preset: 'standard',
            lastUpdated: new Date().toISOString()
        };
    }
    
    /**
     * Cargar configuracion desde LocalStorage
     */
    loadSettings() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            
            if (!saved) {
                return this.getDefaultSettings();
            }
            
            const parsed = JSON.parse(saved);
            
            // MIGRACIÓN FORZADA: Si quality está en escala antigua (0-1), migrar SIEMPRE
            if (typeof parsed.quality === 'number' && parsed.quality < 1) {
                console.warn('🔧 MIGRACIÓN FORZADA: Detectada calidad antigua (0-1)');
                return this.migrateSettings(parsed);
            }
            
            // Validar version
            if (parsed.version !== this.version) {
                return this.migrateSettings(parsed);
            }
            
            // Validar estructura
            if (!this.validateSettings(parsed)) {
                console.warn('Configuracion invalida, usando defaults');
                return this.getDefaultSettings();
            }
            
            return parsed;
            
        } catch (error) {
            console.error('Error cargando configuracion:', error);
            return this.getDefaultSettings();
        }
    }
    
    /**
     * Guardar configuracion en LocalStorage
     */
    saveSettings(newSettings) {
        try {
            // Validar antes de guardar
            if (!this.validateSettings(newSettings)) {
                throw new Error('Configuracion invalida');
            }
            
            // Actualizar timestamp
            newSettings.lastUpdated = new Date().toISOString();
            newSettings.version = this.version;
            
            // Guardar
            localStorage.setItem(this.storageKey, JSON.stringify(newSettings));
            this.settings = newSettings;
            
            return true;
            
        } catch (error) {
            console.error('Error guardando configuracion:', error);
            return false;
        }
    }
    
    /**
     * Validar estructura de configuracion
     */
    validateSettings(settings) {
        if (!settings || typeof settings !== 'object') return false;
        if (!settings.resolution || !settings.resolution.width || !settings.resolution.height) return false;
        if (typeof settings.fps !== 'number' || settings.fps < 1 || settings.fps > 30) return false;
        if (typeof settings.quality !== 'number' || settings.quality < 40 || settings.quality > 100) return false;
        
        return true;
    }
    
    /**
     * Migrar configuracion de versiones antiguas
     */
    migrateSettings(oldSettings) {
        const migrated = { ...oldSettings };
        
        // MIGRACIÓN CRÍTICA: Escala de calidad 0-1 → 0-100
        if (typeof migrated.quality === 'number' && migrated.quality < 1) {
            console.warn('⚠️ Detectada calidad antigua (0-1), convirtiendo a escala 0-100');
            migrated.quality = Math.round(migrated.quality * 100);
        }
        
        // Validar que quality esté en rango correcto
        if (migrated.quality < 40 || migrated.quality > 100) {
            console.warn('⚠️ Calidad fuera de rango, usando default');
            migrated.quality = this.isMobile ? 50 : 60;
        }
        
        // Actualizar version
        migrated.version = this.version;
        
        return migrated;
    }
    
    /**
     * Obtener configuracion actual
     */
    getSettings() {
        return this.settings;
    }
    
    /**
     * Restablecer a defaults
     */
    resetToDefaults() {
        const defaults = this.getDefaultSettings();
        this.saveSettings(defaults);
        return defaults;
    }
    
    /**
     * Listar camaras disponibles
     */
    async getCameraList() {
        try {
            // Solicitar permiso primero (necesario para labels)
            const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
            tempStream.getTracks().forEach(track => track.stop());
            
            // Ahora listar camaras
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(d => d.kind === 'videoinput');
            
            return videoDevices.map(device => ({
                id: device.deviceId,
                label: device.label || `Camara ${device.deviceId.substring(0, 8)}`,
                isCamo: device.label.toLowerCase().includes('camo'),
                isRear: device.label.toLowerCase().includes('back') || 
                       device.label.toLowerCase().includes('rear'),
                isWebcam: device.label.toLowerCase().includes('webcam') ||
                         device.label.toLowerCase().includes('integrated') ||
                         device.label.toLowerCase().includes('built-in')
            }));
            
        } catch (error) {
            console.error('Error obteniendo lista de camaras:', error);
            return [];
        }
    }
    
    /**
     * Calcular ancho de banda estimado
     */
    calculateBandwidth(resolution, fps, quality) {
        // Tabla de tamanos base (KB) con calidad 60% como referencia
        const baseSizes = {
            '360p': 15,
            '480p': 50,
            '720p': 120,
            '1080p': 300
        };
        
        const baseSize = baseSizes[resolution.value] || 50;
        
        // Factor de calidad (normalizado a 60 = 1.0)
        const qualityFactor = quality / 60;
        
        // Tamano de frame ajustado
        const frameSize = baseSize * qualityFactor;
        
        // Ancho de banda
        const bandwidthKBps = frameSize * fps;
        const bandwidthMbps = (bandwidthKBps * 8) / 1024;  // KB/s a Mbps
        
        return {
            frameSize: Math.round(frameSize),
            bandwidthKBps: Math.round(bandwidthKBps),
            bandwidthMbps: bandwidthMbps.toFixed(2),
            level: this.getBandwidthLevel(bandwidthMbps)
        };
    }
    
    /**
     * Clasificar nivel de ancho de banda
     */
    getBandwidthLevel(mbps) {
        if (mbps <= 1) return 'low';      // Verde - Red lenta OK
        if (mbps <= 3) return 'medium';   // Amarillo - Red media
        if (mbps <= 5) return 'high';     // Naranja - Red rapida
        return 'extreme';                 // Rojo - Requiere excelente conexion
    }
    
    /**
     * Validar configuracion y generar warnings
     */
    validateConfiguration(settings) {
        const warnings = [];
        const bandwidth = this.calculateBandwidth(
            settings.resolution, 
            settings.fps, 
            settings.quality
        );
        
        // Warning 1: Ancho de banda muy alto
        if (bandwidth.bandwidthMbps > 5) {
            warnings.push({
                level: 'warning',
                message: 'Configuracion requiere mas de 5 Mbps, puede causar lag en Railway'
            });
        }
        
        // Warning 2: Calidad muy baja en alta resolucion
        if ((settings.resolution.value === '720p' || settings.resolution.value === '1080p') 
            && settings.quality < 60) {
            warnings.push({
                level: 'info',
                message: 'Calidad baja en alta resolucion puede afectar deteccion MediaPipe'
            });
        }
        
        // Warning 3: FPS muy bajo
        if (settings.fps < 2) {
            warnings.push({
                level: 'info',
                message: 'FPS bajo puede hacer movimiento menos fluido'
            });
        }
        
        // Warning 4: Frame muy grande (excede limite Railway teorico)
        if (bandwidth.frameSize > 300) {
            warnings.push({
                level: 'error',
                message: 'Frame muy grande, puede exceder limite de Railway (5MB)'
            });
        }
        
        return warnings;
    }
}

// CONSTANTES DE OPCIONES (valores validados cientificamente)

const RESOLUTION_OPTIONS = [
    // MINIMO PRACTICO (MediaPipe estable)
    {
        value: '360p',
        width: 480,
        height: 360,
        label: '360p - Baja',
        description: 'Minimo para deteccion estable',
        minBandwidth: '0.1 Mbps',
        recommended: 'red-lenta'
    },
    
    // ESTANDAR (ACTUAL DEL SISTEMA)
    {
        value: '480p',
        width: 640,
        height: 480,
        label: '480p - Estandar',
        description: 'Balance perfecto (ACTUAL)',
        minBandwidth: '0.5 Mbps',
        recommended: 'general',
        default: true,  // Configuracion actual
        current: true
    },
    
    // ALTA CALIDAD
    {
        value: '720p',
        width: 1280,
        height: 720,
        label: '720p - Alta',
        description: 'Mayor precision de landmarks',
        minBandwidth: '2 Mbps',
        recommended: 'red-rapida'
    },
    
    // MAXIMO PRACTICO
    {
        value: '1080p',
        width: 1920,
        height: 1080,
        label: '1080p - Muy Alta',
        description: 'Maxima calidad (solo redes rapidas)',
        minBandwidth: '5 Mbps',
        recommended: 'fibra',
        warning: 'Puede causar lag en redes lentas'
    }
];

const FPS_OPTIONS = [
    // MINIMO FUNCIONAL
    {
        value: 1,
        label: '1 FPS',
        description: 'Minimo (redes muy lentas)',
        interval: 1000,
        bandwidth: 'muy-baja',
        warning: 'Movimiento poco fluido'
    },
    
    // BAJO
    {
        value: 2,
        label: '2 FPS',
        description: 'Bajo (actual para moviles)',
        interval: 500,
        bandwidth: 'baja',
        currentMobile: true  // Actual movil
    },
    
    // MEDIO
    {
        value: 3,
        label: '3 FPS',
        description: 'Medio',
        interval: 333,
        bandwidth: 'media'
    },
    
    // ALTO
    {
        value: 5,
        label: '5 FPS',
        description: 'Alto',
        interval: 200,
        bandwidth: 'alta'
    },
    
    // MUY ALTO
    {
        value: 10,
        label: '10 FPS',
        description: 'Muy alto',
        interval: 100,
        bandwidth: 'muy-alta'
    },
    
    // OPTIMO
    {
        value: 15,
        label: '15 FPS',
        description: 'Optimo',
        interval: 67,
        bandwidth: 'muy-alta'
    },
    
    // FLUIDO
    {
        value: 20,
        label: '20 FPS',
        description: 'Fluido',
        interval: 50,
        bandwidth: 'extrema'
    },
    
    // ESTANDAR DESKTOP (ACTUAL)
    {
        value: 25,
        label: '25 FPS',
        description: 'Estandar desktop (ACTUAL)',
        interval: 40,
        bandwidth: 'extrema',
        default: true,
        currentDesktop: true,
        current: true
    },
    
    // MAXIMO
    {
        value: 30,
        label: '30 FPS',
        description: 'Maximo',
        interval: 33,
        bandwidth: 'extrema',
        warning: 'Requiere excelente conexion'
    }
];

const QUALITY_OPTIONS = [
    // MINIMA FUNCIONAL
    {
        value: 40,
        label: 'Muy Baja (40%)',
        description: 'Maxima compresion',
        bandwidth: 'minima',
        sizeReduction: '~70%',
        warning: 'Puede afectar deteccion en 720p+'
    },
    
    // BAJA (ACTUAL MOVIL)
    {
        value: 50,
        label: 'Baja (50%)',
        description: 'Alta compresion (ACTUAL MOVIL)',
        bandwidth: 'baja',
        sizeReduction: '~60%',
        recommended: 'red-lenta',
        currentMobile: true  // Actual movil confirmado
    },
    
    // MEDIA (ACTUAL DESKTOP)
    {
        value: 60,
        label: 'Media (60%)',
        description: 'Balance compresion/calidad (ACTUAL DESKTOP)',
        bandwidth: 'media',
        sizeReduction: '~40%',
        recommended: 'general',
        default: true,  // Actual desktop confirmado
        currentDesktop: true,
        current: true
    },
    
    // ALTA
    {
        value: 70,
        label: 'Alta (70%)',
        description: 'Buena calidad',
        bandwidth: 'alta',
        sizeReduction: '~30%'
    },
    
    // MUY ALTA
    {
        value: 80,
        label: 'Muy Alta (80%)',
        description: 'Excelente calidad',
        bandwidth: 'muy-alta',
        sizeReduction: '~20%'
    },
    
    // MAXIMA
    {
        value: 90,
        label: 'Maxima (90%)',
        description: 'Casi sin compresion',
        bandwidth: 'muy-alta',
        sizeReduction: '~10%'
    },
    
    // SIN COMPRESION
    {
        value: 100,
        label: 'Sin Compresion (100%)',
        description: 'Calidad maxima absoluta',
        bandwidth: 'extrema',
        sizeReduction: '0%',
        warning: 'Requiere conexion excelente'
    }
];

// PRESETS DE CONFIGURACION
const CAMERA_PRESETS = {
    slow: {
        name: 'Red Lenta',
        description: 'Optimizado para conexiones lentas (1-2 Mbps)',
        icon: 'wifi-off',
        settings: {
            resolution: RESOLUTION_OPTIONS.find(r => r.value === '360p'),
            fps: 1,
            quality: 50
        }
    },
    
    standard: {
        name: 'Estandar',
        description: 'Balance perfecto - 480p @ 25 FPS',
        icon: 'wifi',
        default: true,
        settings: {
            resolution: RESOLUTION_OPTIONS.find(r => r.value === '480p'),
            fps: 25,
            quality: 60
        }
    },
    
    high: {
        name: 'Alta Calidad',
        description: 'Mayor precision, requiere buena conexion',
        icon: 'wifi-2',
        settings: {
            resolution: RESOLUTION_OPTIONS.find(r => r.value === '720p'),
            fps: 30,
            quality: 80
        }
    },
    
    custom: {
        name: 'Personalizado',
        description: 'Ajusta manualmente cada parametro',
        icon: 'sliders',
        custom: true
    }
};

// Instancia global
window.cameraSettings = new CameraSettings();

// ========================================
// 🎨 SESSION 3: UI FEEDBACK HELPERS
// ========================================

/**
 * Mostrar estado de detección de cámaras en UI
 * @param {string} type - 'info', 'success', 'warning', 'error'
 * @param {string} message - Mensaje a mostrar
 */
function showCameraStatus(type, message) {
    // 🎯 SESSION 3 FIX: Usar contenedor fijo que siempre está visible
    let statusContainer = document.getElementById('camera-status-message');
    
    if (!statusContainer) {
        // ℹ️ SESSION 4 FIX: Silencioso - normal en páginas sin UI de análisis
        console.debug('ℹ️ [UI] Elementos de feedback no disponibles (normal fuera de /analysis)');
        return;
    }
    
    // Aplicar estilo según tipo
    const styles = {
        info: { bg: '#e3f2fd', color: '#1976d2', border: '#1976d2' },
        success: { bg: '#e8f5e9', color: '#388e3c', border: '#388e3c' },
        warning: { bg: '#fff3e0', color: '#f57c00', border: '#f57c00' },
        error: { bg: '#ffebee', color: '#d32f2f', border: '#d32f2f' }
    };
    
    const style = styles[type] || styles.info;
    
    // Aplicar estilos completos (incluye base + color)
    statusContainer.style.cssText = `
        display: block;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 500;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        background-color: ${style.bg};
        color: ${style.color};
        border: 2px solid ${style.border};
        pointer-events: auto;
    `;
    statusContainer.textContent = message;
    
    // 🆕 SESSION 3 FIX: Auto-ocultar mensajes de éxito e info
    if (type === 'success' || type === 'info') {
        const delay = type === 'success' ? 3000 : 2000; // Success 3s, Info 2s
        setTimeout(() => {
            statusContainer.style.opacity = '0';
            setTimeout(() => {
                statusContainer.style.display = 'none';
                statusContainer.style.opacity = '1';
            }, 300);
        }, delay);
    }
}

/**
 * Mostrar botón de retry cuando falla detección
 */
function showRetryButton() {
    let retryBtn = document.getElementById('camera-retry-button');
    
    // 🔇 COMENTADO - Botón "Reintentar Detección" causaba problemas
    // Usuario reportó: "no esta funcionando bien y por ahora quisiera que lo comentemos"
    /*
    if (!retryBtn) {
        const retryContainer = document.getElementById('camera-retry-container');
        if (retryContainer) {
            retryBtn = document.createElement('button');
            retryBtn.id = 'camera-retry-button';
            retryBtn.textContent = '🔄 Reintentar Detección';
            retryBtn.style.cssText = `
                margin-top: 15px;
                padding: 12px 24px;
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
                box-shadow: 0 4px 8px rgba(255, 107, 53, 0.4);
                animation: pulse 2s ease-in-out infinite;
            `;
            
            // Añadir animación de pulso
            if (!document.getElementById('retry-pulse-animation')) {
                const style = document.createElement('style');
                style.id = 'retry-pulse-animation';
                style.textContent = `
                    @keyframes pulse {
                        0%, 100% { transform: scale(1); box-shadow: 0 4px 8px rgba(255, 107, 53, 0.4); }
                        50% { transform: scale(1.05); box-shadow: 0 6px 12px rgba(255, 107, 53, 0.6); }
                    }
                `;
                document.head.appendChild(style);
            }
            
            retryBtn.onmouseover = () => {
                retryBtn.style.backgroundColor = '#ff5722';
                retryBtn.style.transform = 'scale(1.1)';
            };
            retryBtn.onmouseout = () => {
                retryBtn.style.backgroundColor = '#ff6b35';
                retryBtn.style.transform = 'scale(1)';
            };
            
            retryBtn.onclick = async () => {
                retryBtn.disabled = true;
                retryBtn.textContent = '🔄 Reintentando...';
                showCameraStatus('info', '🔄 Reintentando detección de cámaras...');
                
                // Limpiar LocalStorage para forzar re-escaneo
                try {
                    localStorage.removeItem('biomech_camera_settings');
                    console.log('🗑️ LocalStorage limpiado para retry');
                } catch (e) {
                    console.warn('⚠️ Error limpiando LocalStorage:', e);
                }
                
                // 🎯 MEJORADO: Detectar si estamos en página inicial o en análisis activo
                const isInAnalysisModal = document.getElementById('analysisModal')?.classList.contains('active');
                
                if (isInAnalysisModal) {
                    // 🔴 ESTAMOS EN ANÁLISIS ACTIVO - Reiniciar análisis completo
                    console.log('🔄 Retry desde análisis activo - Reiniciando análisis...');
                    
                    // Remover botón inmediatamente
                    retryBtn.remove();
                    
                    // Detener análisis actual
                    if (typeof stopAnalysisCompletely === 'function') {
                        stopAnalysisCompletely();
                    }
                    
                    // Esperar 1 segundo y reiniciar
                    setTimeout(async () => {
                        // Re-escanear cámaras
                        await preloadCamerasOnPageLoad();
                        
                        // Reiniciar análisis
                        if (typeof startAnalysis === 'function') {
                            console.log('🚀 Reiniciando análisis con nuevas cámaras...');
                            startAnalysis();
                        }
                    }, 1000);
                    
                } else {
                    // 🟢 ESTAMOS EN PÁGINA INICIAL - Solo re-detectar
                    console.log('🔄 Retry desde página inicial - Re-escaneando...');
                    
                    // Reintentar detección
                    await preloadCamerasOnPageLoad();
                    
                    // Ocultar botón de retry si fue exitoso
                    if (window.cameraPreloadDone) {
                        retryBtn.remove();
                    } else {
                        retryBtn.disabled = false;
                        retryBtn.textContent = '🔄 Reintentar Detección';
                    }
                }
            };
            
            retryContainer.appendChild(retryBtn);

        } else {
            // ℹ️ SESSION 4 FIX: Silencioso - normal en páginas sin UI de análisis
            console.debug('ℹ️ [UI] Contenedor retry no disponible (normal fuera de /analysis)');
        }
    }
    */
    // 🔇 FIN COMENTADO - Botón "Reintentar Detección"
}
