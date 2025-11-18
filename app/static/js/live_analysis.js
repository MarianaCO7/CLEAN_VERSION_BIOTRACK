/**
 * 🎯 LIVE ANALYSIS CONTROLLER - Control del Análisis en Vivo
 * ===========================================================
 * Controla la interfaz de análisis en tiempo real
 * 
 * RESPONSABILIDADES:
 * - Polling de datos del analyzer cada 200ms
 * - Actualización de métricas en UI
 * - Control de sesión (start, stop, reset)
 * - Gráfico de ROM en tiempo real
 * - Modal de resultados
 * 
 * Autor: BIOTRACK Team
 * Fecha: 2025-11-14
 */

class LiveAnalysisController {
    constructor(config) {
        this.config = config;
        this.isActive = false;
        this.pollingInterval = null;
        this.romChart = null;
        this.dataPoints = [];
        this.maxDataPoints = 50; // Últimos 50 puntos en el gráfico
        
        // Inicializar
        this.init();
    }
    
    /**
     * Inicialización del controller
     */
    init() {
        console.log('[LiveAnalysis] Inicializando con config:', this.config);
        
        // Crear overlay de pantalla completa
        createFullscreenOverlay();
        
        // Inicializar gráfico de ROM
        this.initROMChart();
        
        // Event listeners
        this.setupEventListeners();
        
        // Ocultar overlay cuando el video stream empiece a funcionar (3 segundos)
        setTimeout(() => {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        }, 3000);
        
        console.log('[LiveAnalysis] Inicialización completa');
    }
    
    /**
     * Configurar event listeners
     */
    setupEventListeners() {
        // Detectar cuando se cierra la ventana/tab
        window.addEventListener('beforeunload', (e) => {
            if (this.isActive) {
                // Intentar detener análisis
                this.stopAnalysis(false); // Sin mostrar modal
                
                // Mensaje de confirmación (algunos navegadores lo ignoran)
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
    
    /**
     * Inicializa el gráfico de ROM con Chart.js
     */
    initROMChart() {
        const ctx = document.getElementById('romChart');
        if (!ctx) {
            console.warn('[LiveAnalysis] Canvas romChart no encontrado');
            return;
        }
        
        this.romChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Ángulo (°)',
                    data: [],
                    borderColor: 'rgba(102, 126, 234, 1)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 2,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: this.config.max_angle,
                        ticks: {
                            callback: function(value) {
                                return value + '°';
                            }
                        }
                    },
                    x: {
                        display: false // Ocultar eje X para simplificar
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y.toFixed(1) + '°';
                            }
                        }
                    }
                },
                animation: {
                    duration: 0 // Sin animación para actualización fluida
                }
            }
        });
        
        console.log('[LiveAnalysis] Gráfico ROM inicializado');
    }
    
    /**
     * Inicia el análisis
     */
    async startAnalysis() {
        console.log('[LiveAnalysis] Iniciando análisis...');
        
        try {
            const response = await fetch('/api/analysis/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    segment_type: this.config.segment_type,
                    exercise_key: this.config.exercise_key
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.isActive = true;
                
                // Actualizar UI
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                
                // Sincronizar botones de pantalla completa
                if (isFullscreenMode) {
                    syncButtonStates();
                }
                
                // Iniciar polling de datos
                this.startDataPolling();
                
                console.log('[LiveAnalysis] Análisis iniciado exitosamente');
            } else {
                throw new Error(data.error || 'Error al iniciar análisis');
            }
        } catch (error) {
            console.error('[LiveAnalysis] Error al iniciar análisis:', error);
            alert('Error al iniciar el análisis: ' + error.message);
        }
    }
    
    /**
     * Detiene el análisis
     */
    async stopAnalysis(showModal = true) {
        console.log('[LiveAnalysis] Deteniendo análisis...');
        
        try {
            const response = await fetch('/api/analysis/stop', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.isActive = false;
                
                // Detener polling
                this.stopDataPolling();
                
                // Actualizar UI
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                
                // Sincronizar botones de pantalla completa
                if (isFullscreenMode) {
                    syncButtonStates();
                }
                
                // Mostrar modal de resultados
                if (showModal) {
                    this.showResults(data.final_data);
                }
                
                console.log('[LiveAnalysis] Análisis detenido exitosamente');
            } else {
                throw new Error(data.error || 'Error al detener análisis');
            }
        } catch (error) {
            console.error('[LiveAnalysis] Error al detener análisis:', error);
            alert('Error al detener el análisis: ' + error.message);
        }
    }
    
    /**
     * Reinicia el ROM máximo
     */
    async resetROM() {
        console.log('[LiveAnalysis] Reiniciando ROM...');
        
        if (!confirm('¿Estás seguro de reiniciar el ROM máximo?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/analysis/reset', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Limpiar gráfico
                this.dataPoints = [];
                if (this.romChart) {
                    this.romChart.data.labels = [];
                    this.romChart.data.datasets[0].data = [];
                    this.romChart.update();
                }
                
                // Resetear métricas
                document.getElementById('maxROM').textContent = '0°';
                
                console.log('[LiveAnalysis] ROM reiniciado exitosamente');
            } else {
                throw new Error(data.error || 'Error al reiniciar ROM');
            }
        } catch (error) {
            console.error('[LiveAnalysis] Error al reiniciar ROM:', error);
            alert('Error al reiniciar ROM: ' + error.message);
        }
    }
    
    /**
     * Inicia el polling de datos cada 200ms
     */
    startDataPolling() {
        console.log('[LiveAnalysis] Iniciando polling de datos...');
        
        this.pollingInterval = setInterval(async () => {
            if (!this.isActive) {
                this.stopDataPolling();
                return;
            }
            
            try {
                const response = await fetch('/api/analysis/current_data');
                const data = await response.json();
                
                if (response.ok && data.success) {
                    this.updateUI(data.data);
                }
            } catch (error) {
                console.error('[LiveAnalysis] Error al obtener datos:', error);
            }
        }, 200); // Actualizar cada 200ms
    }
    
    /**
     * Detiene el polling de datos
     */
    stopDataPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            console.log('[LiveAnalysis] Polling detenido');
        }
    }
    
    /**
     * Actualiza la UI con los datos actuales
     */
    updateUI(data) {
        // Actualizar ángulo actual
        const angleElement = document.getElementById('currentAngle');
        if (angleElement && data.angle !== undefined) {
            // Para perfil: mostrar abs() + dirección
            if (data.angle < 0) {
                angleElement.textContent = `${Math.abs(data.angle).toFixed(1)}° (EXT)`;
            } else {
                angleElement.textContent = `${data.angle.toFixed(1)}° (FLEX)`;
            }
        }
        
        // Actualizar ROM máximo
        const romElement = document.getElementById('maxROM');
        if (romElement && data.max_rom !== undefined) {
            romElement.textContent = `${data.max_rom.toFixed(1)}°`;
        }
        
        // Para análisis frontal bilateral
        if (data.left_angle !== undefined && data.right_angle !== undefined) {
            angleElement.textContent = `Izq: ${data.left_angle.toFixed(1)}° | Der: ${data.right_angle.toFixed(1)}°`;
            romElement.textContent = `Izq: ${data.left_max_rom.toFixed(1)}° | Der: ${data.right_max_rom.toFixed(1)}°`;
        }
        
        // Actualizar estado de postura
        const postureElement = document.getElementById('postureStatus');
        if (postureElement && data.posture_valid !== undefined) {
            if (data.posture_valid) {
                postureElement.innerHTML = `
                    <i class="bi bi-check-circle-fill"></i>
                    <span>Postura Correcta</span>
                `;
                postureElement.classList.add('valid');
                postureElement.classList.remove('invalid');
            } else {
                postureElement.innerHTML = `
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <span>Ajusta tu postura</span>
                `;
                postureElement.classList.add('invalid');
                postureElement.classList.remove('valid');
            }
        }
        
        // Actualizar FPS
        const fpsElement = document.getElementById('fpsDisplay');
        if (fpsElement && data.fps !== undefined) {
            fpsElement.textContent = `${data.fps} FPS`;
        }
        
        // Actualizar gráfico
        if (this.romChart) {
            const angleValue = Math.abs(data.angle || data.left_angle || 0);
            this.updateChart(angleValue);
        }
        
        // Si estamos en modo pantalla completa, actualizar también esas métricas
        if (isFullscreenMode) {
            updateFullscreenMetrics();
        }
    }
    
    /**
     * Actualiza el gráfico de ROM
     */
    updateChart(angle) {
        if (!this.romChart) return;
        
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        
        // Agregar dato
        this.romChart.data.labels.push(timeLabel);
        this.romChart.data.datasets[0].data.push(angle);
        
        // Mantener solo los últimos N puntos
        if (this.romChart.data.labels.length > this.maxDataPoints) {
            this.romChart.data.labels.shift();
            this.romChart.data.datasets[0].data.shift();
        }
        
        // Actualizar sin animación
        this.romChart.update('none');
    }
    
    /**
     * Muestra el modal de resultados
     */
    showResults(finalData) {
        if (!finalData) {
            console.warn('[LiveAnalysis] No hay datos finales para mostrar');
            return;
        }
        
        // Obtener ROM final
        const maxROM = finalData.max_rom || finalData.left_max_rom || 0;
        
        // Actualizar valores en el modal
        document.getElementById('finalROM').textContent = `${maxROM.toFixed(1)}°`;
        
        // Clasificar ROM
        const classification = this.classifyROM(maxROM);
        const badgeElement = document.getElementById('romClassification');
        badgeElement.textContent = classification.label;
        badgeElement.className = 'result-value badge ' + classification.class;
        
        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('resultsModal'));
        modal.show();
        
        console.log('[LiveAnalysis] Resultados mostrados:', finalData);
    }
    
    /**
     * Clasifica el ROM según rangos
     */
    classifyROM(rom) {
        const percentage = (rom / this.config.max_angle) * 100;
        
        if (percentage >= 90) {
            return { label: 'Óptimo', class: 'bg-success' };
        } else if (percentage >= 75) {
            return { label: 'Bueno', class: 'bg-info' };
        } else if (percentage >= 50) {
            return { label: 'Limitado', class: 'bg-warning' };
        } else {
            return { label: 'Muy Limitado', class: 'bg-danger' };
        }
    }
    
    /**
     * Guarda los resultados en el historial
     */
    async saveResults() {
        console.log('[LiveAnalysis] Guardando resultados...');
        
        // TODO: Implementar guardado en base de datos
        alert('Función de guardado en desarrollo. Los resultados se guardarán en el historial próximamente.');
        
        // Cerrar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('resultsModal'));
        if (modal) {
            modal.hide();
        }
    }
    
    /**
     * Muestra error en el video feed
     */
    showVideoError() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.innerHTML = `
                <i class="bi bi-exclamation-triangle text-danger" style="font-size: 3rem;"></i>
                <p class="mt-2 text-danger">Error al cargar el video</p>
                <small>Verifica que la cámara esté conectada y disponible</small>
                <button class="btn btn-primary mt-3" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Recargar
                </button>
            `;
        }
    }
}

// ============================================================================
// INICIALIZACIÓN AL CARGAR LA PÁGINA
// ============================================================================

let liveAnalysisController = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('[LiveAnalysis] DOM cargado - Inicializando controller');
    
    // Verificar que existe la configuración
    if (typeof EXERCISE_CONFIG === 'undefined') {
        console.error('[LiveAnalysis] EXERCISE_CONFIG no está definido');
        alert('Error: Configuración del ejercicio no disponible');
        return;
    }
    
    // Crear controller
    liveAnalysisController = new LiveAnalysisController(EXERCISE_CONFIG);
    
    console.log('[LiveAnalysis] Sistema listo');
});

// ============================================================================
// FUNCIONES GLOBALES (llamadas desde HTML)
// ============================================================================

function startAnalysis() {
    if (liveAnalysisController) {
        liveAnalysisController.startAnalysis();
    }
}

function stopAnalysis() {
    if (liveAnalysisController) {
        liveAnalysisController.stopAnalysis(true);
    }
}

function resetROM() {
    if (liveAnalysisController) {
        liveAnalysisController.resetROM();
    }
}

function saveResults() {
    if (liveAnalysisController) {
        liveAnalysisController.saveResults();
    }
}

// ============================================================================
// MODO PANTALLA COMPLETA
// ============================================================================

let isFullscreenMode = false;
let originalVideoParent = null;
let fullscreenOverlay = null;

// Crear el overlay dinámicamente al cargar la página
function createFullscreenOverlay() {
    if (fullscreenOverlay) return; // Ya existe
    
    fullscreenOverlay = document.createElement('div');
    fullscreenOverlay.id = 'fullscreenOverlay';
    fullscreenOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.95);
        z-index: 9999;
        display: none;
        align-items: center;
        justify-content: center;
        margin: 0;
        padding: 0;
        overflow: hidden;
    `;
    
    fullscreenOverlay.innerHTML = `
        <!-- Botón de cerrar -->
        <button class="fullscreen-close" onclick="toggleFullscreen()" style="
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 10001;
        ">
            <i class="bi bi-x-lg"></i>
        </button>
        
        <!-- Contenedor del video -->
        <div id="fullscreenVideoContainer" style="
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 80px 20px 120px 20px;
        "></div>
        
        <!-- Controles flotantes -->
        <div class="fullscreen-controls" style="
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
            z-index: 10001;
            background: rgba(0, 0, 0, 0.7);
            padding: 15px 25px;
            border-radius: 50px;
            backdrop-filter: blur(10px);
        ">
            <button id="fullscreenStartBtn" class="btn btn-success btn-lg" onclick="startAnalysis()">
                <i class="bi bi-play-fill"></i> Iniciar Análisis
            </button>
            <button id="fullscreenStopBtn" class="btn btn-danger btn-lg" onclick="stopAnalysis()" disabled>
                <i class="bi bi-stop-fill"></i> Detener
            </button>
            <button id="fullscreenResetBtn" class="btn btn-warning btn-lg" onclick="resetROM()">
                <i class="bi bi-arrow-clockwise"></i> Reiniciar ROM
            </button>
        </div>
        
        <!-- Métricas flotantes -->
        <div class="fullscreen-metrics" style="
            position: absolute;
            top: 80px;
            left: 30px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            z-index: 10001;
        ">
            <div class="metric-box" style="
                background: rgba(0, 0, 0, 0.7);
                padding: 15px 25px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(102, 126, 234, 0.3);
                min-width: 200px;
            ">
                <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;">Ángulo Actual</div>
                <div id="fullscreenCurrentAngle" style="font-size: 2rem; font-weight: 700; color: #00d4ff; text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);">0°</div>
            </div>
            <div class="metric-box" style="
                background: rgba(0, 0, 0, 0.7);
                padding: 15px 25px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(102, 126, 234, 0.3);
                min-width: 200px;
            ">
                <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;">ROM Máximo</div>
                <div id="fullscreenMaxROM" style="font-size: 2rem; font-weight: 700; color: #00d4ff; text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);">0°</div>
            </div>
            <div class="metric-box" style="
                background: rgba(0, 0, 0, 0.7);
                padding: 15px 25px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(102, 126, 234, 0.3);
                min-width: 200px;
            ">
                <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;">Estado</div>
                <div id="fullscreenPostureStatus" style="display: flex; align-items: center; gap: 8px; font-size: 1rem; color: white;">
                    <i class="bi bi-hourglass-split"></i>
                    <span>Detectando...</span>
                </div>
            </div>
        </div>
    `;
    
    // Agregar al body (fuera de cualquier contenedor)
    document.body.appendChild(fullscreenOverlay);
    console.log('[Fullscreen] Overlay creado y agregado al body');
}

function toggleFullscreen() {
    // Asegurarse de que el overlay existe
    if (!fullscreenOverlay) {
        createFullscreenOverlay();
    }
    
    const fullscreenContainer = document.getElementById('fullscreenVideoContainer');
    const videoElement = document.getElementById('videoFeed');
    
    isFullscreenMode = !isFullscreenMode;
    
    if (isFullscreenMode) {
        // Entrar en modo pantalla completa
        originalVideoParent = videoElement.parentElement;
        
        // MOVER el video al contenedor de pantalla completa
        fullscreenContainer.appendChild(videoElement);
        
        // Ajustar estilos del video para pantalla completa
        videoElement.style.maxWidth = '100%';
        videoElement.style.maxHeight = '100%';
        videoElement.style.width = 'auto';
        videoElement.style.height = 'auto';
        videoElement.style.objectFit = 'contain';
        videoElement.style.borderRadius = '10px';
        videoElement.style.boxShadow = '0 20px 60px rgba(0, 0, 0, 0.5)';
        
        // Mostrar overlay
        fullscreenOverlay.style.display = 'flex';
        
        // Bloquear scroll del body
        document.body.style.overflow = 'hidden';
        
        // Sincronizar estados de botones
        syncButtonStates();
        
        // Actualizar métricas fullscreen
        updateFullscreenMetrics();
        
        console.log('[Fullscreen] Modo pantalla completa activado');
    } else {
        // Salir de modo pantalla completa
        if (originalVideoParent) {
            // Restaurar estilos originales del video
            videoElement.style.maxWidth = '';
            videoElement.style.maxHeight = '';
            videoElement.style.width = '';
            videoElement.style.height = '';
            videoElement.style.objectFit = '';
            videoElement.style.borderRadius = '';
            videoElement.style.boxShadow = '';
            
            // DEVOLVER el video a su contenedor original
            originalVideoParent.appendChild(videoElement);
        }
        
        // Ocultar overlay
        fullscreenOverlay.style.display = 'none';
        
        // Restaurar scroll del body
        document.body.style.overflow = '';
        
        console.log('[Fullscreen] Modo pantalla completa desactivado');
    }
}

function syncButtonStates() {
    // Sincronizar estado de botones entre vista normal y fullscreen
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const resetBtn = document.getElementById('resetBtn');
    
    const fsStartBtn = document.getElementById('fullscreenStartBtn');
    const fsStopBtn = document.getElementById('fullscreenStopBtn');
    const fsResetBtn = document.getElementById('fullscreenResetBtn');
    
    fsStartBtn.disabled = startBtn.disabled;
    fsStopBtn.disabled = stopBtn.disabled;
    fsResetBtn.disabled = resetBtn.disabled;
}

function updateFullscreenMetrics() {
    // Copiar valores actuales a las métricas de pantalla completa
    const currentAngle = document.getElementById('currentAngle').textContent;
    const maxROM = document.getElementById('maxROM').textContent;
    const postureStatus = document.getElementById('postureStatus').innerHTML;
    
    document.getElementById('fullscreenCurrentAngle').textContent = currentAngle;
    document.getElementById('fullscreenMaxROM').textContent = maxROM;
    document.getElementById('fullscreenPostureStatus').innerHTML = postureStatus;
}

// Tecla ESC para salir de pantalla completa
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isFullscreenMode) {
        toggleFullscreen();
    }
});
