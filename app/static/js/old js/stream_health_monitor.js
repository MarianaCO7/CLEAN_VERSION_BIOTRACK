/**
 * ⚕️ STREAM HEALTH MONITOR - SESSION 3 EXTENSION
 * Detecta cuando el stream de video falla (pantalla negra) y toma acción automática
 */

class StreamHealthMonitor {
    constructor() {
        this.isMonitoring = false;
        this.checkInterval = null;
        this.canvas = null;
        this.ctx = null;
        this.failureCount = 0;
        this.maxFailures = 3; // 3 checks consecutivos fallidos = problema
        this.checkIntervalMs = 2000; // Verificar cada 2 segundos
    }

    /**
     * Iniciar monitoreo de salud del stream
     * @param {HTMLImageElement} videoElement - Elemento <img> del stream
     */
    startMonitoring(videoElement) {
        if (this.isMonitoring) {
            console.warn('⚠️ [HEALTH] Ya hay un monitoreo activo');
            return;
        }

        console.log('⚕️ [HEALTH] Iniciando monitoreo de stream...');
        this.videoElement = videoElement;
        this.failureCount = 0;
        this.isMonitoring = true;

        // Crear canvas para analizar frames
        this.canvas = document.createElement('canvas');
        this.canvas.width = 160;  // Resolución baja para análisis rápido
        this.canvas.height = 120;
        this.ctx = this.canvas.getContext('2d');

        // Iniciar checks periódicos
        this.checkInterval = setInterval(() => {
            this.checkStreamHealth();
        }, this.checkIntervalMs);
    }

    /**
     * Verificar si el stream está saludable (no negro, no congelado)
     */
    checkStreamHealth() {
        if (!this.videoElement || !this.isMonitoring) {
            return;
        }

        try {
            // Dibujar frame actual en canvas
            this.ctx.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);
            
            // Analizar píxeles
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            const pixels = imageData.data;
            
            let totalBrightness = 0;
            let pixelCount = 0;
            
            // Calcular brillo promedio (cada 4 valores = RGBA)
            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i];
                const g = pixels[i + 1];
                const b = pixels[i + 2];
                const brightness = (r + g + b) / 3;
                totalBrightness += brightness;
                pixelCount++;
            }
            
            const avgBrightness = totalBrightness / pixelCount;
            
            // 🚨 DETECCIÓN DE PROBLEMA
            if (avgBrightness < 10) {
                this.failureCount++;
                console.warn(`⚠️ [HEALTH] Stream oscuro detectado (brillo: ${avgBrightness.toFixed(1)}). Fallo ${this.failureCount}/${this.maxFailures}`);
                
                if (this.failureCount >= this.maxFailures) {
                    this.handleStreamFailure();
                }
            } else {
                // Stream OK, resetear contador
                if (this.failureCount > 0) {
                    console.log(`✅ [HEALTH] Stream recuperado (brillo: ${avgBrightness.toFixed(1)})`);
                }
                this.failureCount = 0;
            }
            
        } catch (error) {
            console.error('❌ [HEALTH] Error verificando salud del stream:', error);
            this.failureCount++;
            
            if (this.failureCount >= this.maxFailures) {
                this.handleStreamFailure();
            }
        }
    }

    /**
     * Manejar falla crítica del stream
     */
    handleStreamFailure() {
        console.error('🚨 [HEALTH] FALLA CRÍTICA: Stream no funcional después de 3 intentos');
        this.stopMonitoring();

        // Mostrar error visual al usuario
        if (typeof showCameraStatus === 'function') {
            showCameraStatus('error', '❌ Cámara no transmite video. Intenta otra cámara o reconecta.');
        }

        // Mostrar botón de retry
        if (typeof showRetryButton === 'function') {
            showRetryButton();
        }

        // Detener stream actual
        if (typeof stopAnalysisCompletely === 'function') {
            console.log('🛑 [HEALTH] Deteniendo stream fallido...');
            stopAnalysisCompletely();
        }

        // Notificar al usuario con alerta si no hay funciones de UI
        if (typeof showCameraStatus !== 'function') {
            alert('⚠️ La cámara seleccionada no está transmitiendo video.\n\nPor favor:\n1. Verifica que tu cámara esté conectada\n2. Cierra otras apps que usen la cámara\n3. Intenta con otra cámara usando el ícono ⚙️');
        }
    }

    /**
     * Detener monitoreo
     */
    stopMonitoring() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        this.isMonitoring = false;
        this.failureCount = 0;
        console.log('🛑 [HEALTH] Monitoreo detenido');
    }
}

// Instancia global
window.streamHealthMonitor = new StreamHealthMonitor();

console.log('✅ [HEALTH] StreamHealthMonitor cargado');
