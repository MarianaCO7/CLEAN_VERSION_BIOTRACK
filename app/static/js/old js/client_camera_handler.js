/**
 * CLIENT CAMERA HANDLER - Sistema híbrido de cámara para Railway
 * Maneja la captura de cámara del cliente y envío de frames al servidor
 */

class ClientCameraHandler {
    constructor() {
        this.stream = null;
        this.videoElement = null;
        this.canvas = null;
        this.ctx = null;
        this.isStreaming = false;
        this.uploadInterval = null;
        this.environmentInfo = null;
        this.frameCount = 0;
        this.lastUploadTime = Date.now();
        
        // CACHE DE METADATA (Fix #1 - Performance)
        this.cameraMetadataCache = null;
        this.metadataSent = false;
        
        // DETECCION AUTOMATICA DE MOVIL
        this.isMobile = this.detectMobile();
        
        // CARGAR CONFIGURACION GUARDADA
        // Si existe cameraSettings, usar esa configuracion
        // Si no, usar valores por defecto actuales
        if (window.cameraSettings) {
            this.settings = window.cameraSettings.getSettings();
        } else {
            // Fallback a valores actuales hardcoded
            this.settings = this.getDefaultSettings();
        }
        
        // USAR CONFIGURACION EN VEZ DE VALORES HARDCODED
        this.UPLOAD_FPS = this.settings.fps;
        this.CANVAS_WIDTH = this.settings.resolution.width;
        this.CANVAS_HEIGHT = this.settings.resolution.height;
        
        // CAPA 1: PREVENCION - Cleanup automatico al cerrar pagina
        this.setupPreventiveCleanup();
    }
    
    /**
     * Obtener configuracion por defecto (mantiene valores actuales del sistema)
     */
    getDefaultSettings() {
        if (this.isMobile) {
            return {
                deviceId: null,
                deviceLabel: 'Automatico',
                resolution: {
                    value: '360p',
                    width: 480,
                    height: 360
                },
                fps: 3,
                quality: 60,  // ESCALA 0-100
                preset: 'standard'
            };
        } else {
            return {
                deviceId: null,
                deviceLabel: 'Automatico',
                resolution: {
                    value: '480p',
                    width: 640,
                    height: 480
                },
                fps: 25,
                quality: 75,  // ESCALA 0-100
                preset: 'standard'
            };
        }
    }
    
    /**
     * Actualizar configuracion (llamado desde modal)
     */
    updateSettings(newSettings) {
        this.settings = newSettings;
        
        // Actualizar propiedades dependientes
        this.UPLOAD_FPS = newSettings.fps;
        this.CANVAS_WIDTH = newSettings.resolution.width;
        this.CANVAS_HEIGHT = newSettings.resolution.height;
        
        return true;
    }
    
    /**
     * Detectar si es dispositivo movil
     */
    detectMobile() {
        const userAgent = navigator.userAgent || navigator.vendor || window.opera;
        
        // Check múltiples indicadores móviles
        const mobileIndicators = [
            /Android/i,
            /webOS/i,
            /iPhone/i,
            /iPad/i,
            /iPod/i,
            /BlackBerry/i,
            /Windows Phone/i,
            /Mobile/i
        ];
        
        const isMobileUA = mobileIndicators.some(indicator => indicator.test(userAgent));
        
        // Check características del dispositivo
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isSmallScreen = window.screen.width <= 768 || window.innerWidth <= 768;
        
        // Combinación de factores
        const isMobile = isMobileUA || (isTouchDevice && isSmallScreen);
        
        return isMobile;
    }
    
    /**
     * 🛡️ CAPA 1: PREVENCIÓN - Cleanup automático de cámara
     * Previene el 90% de los glitches de "cámara en uso"
     */
    setupPreventiveCleanup() {
        // 🚪 Cleanup al cerrar/recargar página
        window.addEventListener('beforeunload', () => {
            if (this.stream) {
                this.stream.getTracks().forEach(track => {
                    track.stop();
                });
            }
        });
        
        // 👁️ Cleanup al cambiar de tab (opcional - libera recursos)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.stream && this.isStreaming) {
                // No detenemos el stream, solo registramos
                // Esto ayuda a debug pero no interrumpe el análisis
            }
        });
        
        // ⚠️ Cleanup en errores de página
        window.addEventListener('error', (event) => {
            if (this.stream && event.error) {
                console.warn('⚠️ [error] Error detectado - Liberando cámara por seguridad');
                this.stopCamera();
            }
        });
    }
    
    async init() {
        try {
            // Detectar entorno
            await this.detectEnvironment();
            
            // Crear elementos necesarios
            this.createElements();
            
            return true;
        } catch (error) {
            console.error('❌ Error inicializando ClientCameraHandler:', error);
            return false;
        }
    }
    
    async detectEnvironment() {
        try {
            const response = await fetch('/api/environment_info');
            const data = await response.json();
            
            if (data.success) {
                this.environmentInfo = data.environment;
            } else {
                throw new Error('Error obteniendo info del entorno');
            }
        } catch (error) {
            console.error('❌ Error detectando entorno:', error);
            // Fallback: asumir modo local si no se puede detectar
            this.environmentInfo = {
                platform: 'local',
                camera_mode: 'server_side',
                has_physical_camera: true
            };
        }
    }
    
    createElements() {
        // Crear video element (oculto)
        this.videoElement = document.createElement('video');
        this.videoElement.style.display = 'none';
        this.videoElement.autoplay = true;
        this.videoElement.playsInline = true;
        document.body.appendChild(this.videoElement);
        
        // Crear canvas (oculto)
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.CANVAS_WIDTH;
        this.canvas.height = this.CANVAS_HEIGHT;
        this.canvas.style.display = 'none';
        this.ctx = this.canvas.getContext('2d');
        document.body.appendChild(this.canvas);
    }
    
    async startCamera(segment, exercise, preferredDeviceId = null) {
        // Si estamos en modo servidor (local), no hacer nada
        if (this.environmentInfo.camera_mode === 'server_side') {
            return true;
        }

        try {
            // 🚀 PREPARAR RECEIVER ANTES DE EMPEZAR UPLOADS
            const prepResponse = await fetch(`/api/prepare_client_receiver/${segment}/${exercise}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!prepResponse.ok) {
                console.warn('⚠️ No se pudo preparar receptor, continuando...');
            }
            
            // USAR CONFIGURACION DE RESOLUCION GUARDADA
            const videoConstraints = {
                width: { ideal: this.CANVAS_WIDTH },
                height: { ideal: this.CANVAS_HEIGHT },
                facingMode: 'user',
                frameRate: { ideal: 30 }  // Stream a 30fps, uploadearemos segun settings.fps
            };
            
            // USAR CAMARA ESPECIFICA SI ESTA CONFIGURADA
            // Prioridad: 1) preferredDeviceId (parametro), 2) settings.deviceId (configurado), 3) automatico
            let targetDeviceId = preferredDeviceId || this.settings.deviceId;
            
            if (targetDeviceId) {
                videoConstraints.deviceId = { exact: targetDeviceId };
                delete videoConstraints.facingMode; // No necesario si especificamos deviceId
            }
            
            // Solicitar acceso a la camara del cliente
            try {
                this.stream = await navigator.mediaDevices.getUserMedia({
                    video: videoConstraints,
                    audio: false
                });
            } catch (cameraError) {
                // FALLBACK: Si falla camara especifica, intentar con automatica
                if (targetDeviceId && cameraError.name === 'NotFoundError') {
                    console.warn('Camara configurada no disponible, usando automatica');
                    delete videoConstraints.deviceId;
                    videoConstraints.facingMode = 'user';
                    
                    // Reintentar con automatica
                    this.stream = await navigator.mediaDevices.getUserMedia({
                        video: videoConstraints,
                        audio: false
                    });
                    
                    // Actualizar settings para reflejar el cambio
                    this.settings.deviceId = null;
                    this.settings.deviceLabel = 'Automatico';
                    
                    if (window.cameraSettings) {
                        window.cameraSettings.saveSettings(this.settings);
                    }
                } else {
                    // Error no recuperable
                    throw cameraError;
                }
            }
            
            this.videoElement.srcObject = this.stream;
            
            // VERIFICAR QUE CAMARA SE ESTA USANDO REALMENTE
            const videoTrack = this.stream.getVideoTracks()[0];
            if (videoTrack) {
                const settings = videoTrack.getSettings();
                const label = videoTrack.label;
                console.log('🎬 CÁMARA ACTIVA CONFIRMADA:');
                console.log(`   📷 Label: ${label}`);
                console.log(`   📐 Resolución: ${settings.width}x${settings.height}`);
                console.log(`   🆔 DeviceId: ${settings.deviceId}`);
                console.log(`   🎯 Es Camo?: ${label.toLowerCase().includes('camo')}`);
                
                // 🆕 CACHEAR METADATA (Fix #1 - Solo una vez)
                if (!this.cameraMetadataCache) {
                    this.cameraMetadataCache = {
                        width: settings.width || this.videoElement.videoWidth || 0,
                        height: settings.height || this.videoElement.videoHeight || 0,
                        device_label: label || ''
                    };
                    console.log('💾 Metadata cacheada:', this.cameraMetadataCache);
                }
                
                if (preferredDeviceId && settings.deviceId === preferredDeviceId) {
                    console.log('✅ ÉXITO: Usando cámara seleccionada (Camo)');
                } else if (preferredDeviceId) {
                    console.warn('⚠️ ADVERTENCIA: No se pudo usar cámara preferida, usando fallback');
                } else {
                    console.log('📷 Usando cámara por defecto');
                }
            }
            
            // Esperar a que el video esté listo
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = resolve;
            });
            
            await this.videoElement.play();
            
            // Iniciar envío de frames
            this.startFrameUpload(segment, exercise);
            
            console.log('✅ Cámara del cliente iniciada');
            return true;
            
        } catch (error) {
            console.error('❌ Error accediendo a la cámara:', error);
            
            // 🛡️ CAPA 2: AUTO-RETRY - Intentar recuperación automática
            const recovered = await this.attemptCameraRecovery(error, segment, exercise, preferredDeviceId);
            if (recovered) {
                return true;
            }
            
            this.showCameraError(error.message);
            return false;
        }
    }
    
    /**
     * 🛡️ CAPA 2: AUTO-RETRY - Recuperación automática de cámara
     * Intenta resolver glitches sin intervención del usuario
     */
    async attemptCameraRecovery(originalError, segment, exercise, preferredDeviceId, maxAttempts = 3) {
        console.log('🔄 CAPA 2: Iniciando auto-recuperación de cámara...');
        console.log(`   ❌ Error original: ${originalError.name} - ${originalError.message}`);
        
        // Solo intentar recovery en errores recuperables
        const recoverableErrors = ['NotReadableError', 'AbortError', 'NotAllowedError'];
        if (!recoverableErrors.includes(originalError.name)) {
            console.log('   ⚠️ Error no recuperable, saltando auto-retry');
            return false;
        }
        
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            console.log(`🔄 Intento ${attempt}/${maxAttempts}...`);
            
            // Esperar antes de reintentar (incrementa con cada intento)
            const delay = attempt * 1000; // 1s, 2s, 3s
            console.log(`   ⏳ Esperando ${delay}ms antes de reintentar...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            
            try {
                // 🧹 Limpiar cualquier stream previo
                if (this.stream) {
                    console.log('   🧹 Limpiando stream anterior...');
                    this.stream.getTracks().forEach(track => track.stop());
                    this.stream = null;
                }
                
                // 🎥 Reintentar getUserMedia
                console.log('   🎥 Reintentando acceso a cámara...');
                
                const videoConstraints = {
                    width: { ideal: this.CANVAS_WIDTH },
                    height: { ideal: this.CANVAS_HEIGHT },
                    facingMode: this.isMobile ? 'environment' : 'user'
                };
                
                if (preferredDeviceId) {
                    videoConstraints.deviceId = { exact: preferredDeviceId };
                    delete videoConstraints.facingMode;
                }
                
                this.stream = await navigator.mediaDevices.getUserMedia({
                    video: videoConstraints,
                    audio: false
                });
                
                this.videoElement.srcObject = this.stream;
                
                await new Promise((resolve) => {
                    this.videoElement.onloadedmetadata = resolve;
                });
                
                await this.videoElement.play();
                
                // ✅ ÉXITO - Recovery completado
                console.log('✅ CAPA 2: Recuperación exitosa en intento', attempt);
                const videoTrack = this.stream.getVideoTracks()[0];
                if (videoTrack) {
                    console.log(`   📷 Cámara recuperada: ${videoTrack.label}`);
                }
                
                // Iniciar envío de frames
                this.startFrameUpload(segment, exercise);
                
                return true;
                
            } catch (retryError) {
                console.warn(`   ❌ Intento ${attempt} falló:`, retryError.message);
                
                if (attempt === maxAttempts) {
                    console.error('❌ CAPA 2: Todos los intentos de recuperación fallaron');
                    return false;
                }
            }
        }
        
        return false;
    }
    
    startFrameUpload(segment, exercise) {
        if (this.uploadInterval) {
            clearInterval(this.uploadInterval);
        }
        
        this.isStreaming = true;
        const uploadIntervalMs = 1000 / this.UPLOAD_FPS;
        
        // 🎯 MOSTRAR CONFIGURACION ACTIVA EN CONSOLA
        const videoTrack = this.stream ? this.stream.getVideoTracks()[0] : null;
        const cameraLabel = videoTrack ? videoTrack.label : 'Desconocida';
        const isCamo = cameraLabel.toLowerCase().includes('camo');
        const deviceType = this.detectMobile() ? 'MOBILE' : 'DESKTOP';
        
        console.log('%c═══════════════════════════════════════════════════════════', 'color: #00FFFF; font-weight: bold');
        console.log('%c📊 CONFIGURACIÓN DE CÁMARA ACTIVA', 'color: #00FFFF; font-size: 16px; font-weight: bold');
        console.log('%c═══════════════════════════════════════════════════════════', 'color: #00FFFF; font-weight: bold');
        console.log(`%c🎥 FPS CONFIGURADO: %c${this.UPLOAD_FPS} fps`, 'color: #FFD700; font-weight: bold', 'color: #00FF00; font-size: 14px; font-weight: bold');
        console.log(`%c📐 Resolución: %c${this.CANVAS_WIDTH}x${this.CANVAS_HEIGHT}`, 'color: #FFD700; font-weight: bold', 'color: #FFFFFF');
        console.log(`%c🎨 Calidad JPEG: %c${this.settings.quality}%`, 'color: #FFD700; font-weight: bold', 'color: #FFFFFF');
        console.log(`%c📷 Cámara: %c${cameraLabel}`, 'color: #FFD700; font-weight: bold', 'color: #FFFFFF');
        console.log(`%c📱 Tipo dispositivo: %c${deviceType}`, 'color: #FFD700; font-weight: bold', 'color: #FFFFFF');
        console.log(`%c🎯 Camo Studio?: %c${isCamo ? 'SÍ ✓' : 'NO'}`, 'color: #FFD700; font-weight: bold', isCamo ? 'color: #00FF00; font-weight: bold' : 'color: #FF6600');
        console.log(`%c⏱️ Intervalo de subida: %c${uploadIntervalMs.toFixed(0)}ms`, 'color: #FFD700; font-weight: bold', 'color: #FFFFFF');
        console.log('%c═══════════════════════════════════════════════════════════', 'color: #00FFFF; font-weight: bold');
        
        // 🛡️ THROTTLING ADAPTATIVO para Railway
        let adaptiveFPS = this.UPLOAD_FPS;
        let consecutiveErrors = 0;
        
        this.uploadInterval = setInterval(async () => {
            try {
                await this.captureAndUploadFrame(segment, exercise);
                
                // ✅ Éxito - restaurar FPS gradualmente
                if (consecutiveErrors > 0) {
                    consecutiveErrors = Math.max(0, consecutiveErrors - 1);
                }
                
            } catch (error) {
                consecutiveErrors++;
                
                // 🚨 ADAPTACIÓN AUTOMÁTICA A CARGA SERVIDOR
                if (consecutiveErrors >= 5 && adaptiveFPS > 1) {
                    const newFPS = Math.max(1, adaptiveFPS * 0.8); // Reducir 20%
                    if (newFPS !== adaptiveFPS) {
                        adaptiveFPS = newFPS;
                        console.log(`🐌 Railway saturado - FPS adaptativo: ${adaptiveFPS}`);
                        
                        // Actualizar intervalo
                        clearInterval(this.uploadInterval);
                        this.uploadInterval = setInterval(() => {
                            this.captureAndUploadFrame(segment, exercise);
                        }, 1000 / adaptiveFPS);
                    }
                    consecutiveErrors = 0; // Reset
                }
                
                console.warn('⚠️ Error en upload adaptativo');
            }
            
        }, uploadIntervalMs);
        
        console.log(`📡 Iniciando envío de frames: ${this.UPLOAD_FPS} FPS`);
    }
    
    captureAndUploadFrame(segment, exercise) {
        if (!this.videoElement || !this.stream || !this.isStreaming) {
            return;
        }
        
        try {
            // Capturar frame del video
            this.ctx.drawImage(this.videoElement, 0, 0, this.CANVAS_WIDTH, this.CANVAS_HEIGHT);
            
            // USAR CALIDAD CONFIGURADA (convertir de 0-100 a 0-1 para canvas.toDataURL)
            const quality = this.settings.quality / 100;
            const frameData = this.canvas.toDataURL('image/jpeg', quality);
            
            // Log reducido - solo cada 60 frames (cada 12 segundos @ 5fps)
            if (this.frameCount % 60 === 0) {
                const sizeKB = Math.round((frameData.length * 0.75) / 1024);
                console.log(`Frame #${this.frameCount}: ${sizeKB}KB @ ${this.settings.quality}% quality`);
            }
            
            // Enviar al servidor SIN BLOQUEAR (fire and forget para fluidez)
            this.uploadFrame(frameData, segment, exercise).catch(() => {
                // Ignorar errores silenciosamente para no interrumpir flujo
            });
            
            this.frameCount++;
            
        } catch (error) {
            // Solo log cada 60 errores
            if (this.frameCount % 60 === 0) {
                console.error('Error capturando frame:', error);
            }
        }
    }
    
    async uploadFrame(frameData, segment, exercise) {
        try {
            // TIMEOUT OPTIMIZADO para Railway (más agresivo)
            const timeout = this.isMobile ? 8000 : 6000;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);
            
            // PAYLOAD OPTIMIZADO - Metadata solo primera vez
            const payload = {
                frame: frameData,
                timestamp: Date.now()
            };
            
            // ENVIAR METADATA SOLO EN EL PRIMER FRAME
            if (!this.metadataSent && this.cameraMetadataCache) {
                payload.width = this.cameraMetadataCache.width;
                payload.height = this.cameraMetadataCache.height;
                payload.device_label = this.cameraMetadataCache.device_label;
                
                console.log('📤 Enviando metadata (primera vez):', {
                    width: payload.width,
                    height: payload.height,
                    label: payload.device_label
                });
                this.metadataSent = true;
            }
            
            const response = await fetch(`/api/upload_frame/${segment}/${exercise}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                // MANEJO SILENCIOSO DE ERRORES RAILWAY - sin logs constantes
                if (response.status === 502 || response.status === 504) {
                    // Errores Railway comunes - ignorar silenciosamente
                    return;
                }
                // Otros errores - log solo cada 60 frames
                if (this.frameCount % 60 === 0) {
                    console.warn('Error uploading frame:', response.status);
                }
            }
            
        } catch (error) {
            // MANEJO SILENCIOSO - log solo cada 60 frames
            if (error.name === 'AbortError') {
                // Timeout - normal en Railway, ignorar
                return;
            }
            if (this.frameCount % 60 === 0) {
                console.warn('Error enviando frame:', error.message);
            }
        }
    }
    
    stopCamera() {
        console.log('⏹️ Deteniendo cámara del cliente');
        
        this.isStreaming = false;
        
        if (this.uploadInterval) {
            clearInterval(this.uploadInterval);
            this.uploadInterval = null;
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        // 🔄 RESET METADATA CACHE (Fix #1)
        this.cameraMetadataCache = null;
        this.metadataSent = false;
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        console.log('✅ Cámara del cliente detenida');
    }
    
    showCameraError(message) {
        const streamContainer = document.querySelector('.stream-container');
        if (streamContainer) {
            streamContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-camera-video-off"></i>
                    <strong>Error de Cámara:</strong> ${message}
                    <br><small>Por favor, permite el acceso a la cámara para usar el análisis biomecánico.</small>
                </div>
            `;
        }
    }
    
    getStats() {
        return {
            isStreaming: this.isStreaming,
            frameCount: this.frameCount,
            environment: this.environmentInfo,
            uploadFPS: this.UPLOAD_FPS
        };
    }
}

// Instancia global
window.clientCameraHandler = new ClientCameraHandler();

// Auto-inicializar cuando se carga la página
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Inicializando ClientCameraHandler...');
    await window.clientCameraHandler.init();
});