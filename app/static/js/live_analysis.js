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
        
        // Inicializar gráfico de ROM
        this.initROMChart();
        
        // Event listeners
        this.setupEventListeners();
        
        // Ocultar overlay cuando el video stream empiece a funcionar (3 segundos)
        setTimeout(() => {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.classList.add('hidden');
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
