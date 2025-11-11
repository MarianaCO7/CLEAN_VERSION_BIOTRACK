/**
 * 🎯 ROM SESSION MANAGER - Sistema de Análisis de Rango de Movimiento
 * Maneja todo el flujo: preparación → calibración → medición → resultados
 */

class ROMSessionManager {
    constructor(segment, exercise) {
        this.segment = segment;
        this.exercise = exercise;
        this.currentPhase = 'preparation'; // preparation, calibration, measurement, results
        this.timer = null;
        this.countdownTimer = null;
        
        // Estado de la sesión
        this.sessionData = {
            calibrationAngle: null,
            maxROM: 0,
            currentROM: 0,
            sessionActive: false,
            calibrated: false
        };
        
        this.init();
    }
    
    init() {
        this.setupUI();
        this.loadCameraRecommendations();
    }
    
    async loadCameraRecommendations() {
        // 📱 Cargar recomendaciones de posición de cámara
        try {
            const response = await fetch(`/api/rom/status/${this.segment}/${this.exercise}`);
            const data = await response.json();
            
            if (data.success && data.camera_recommendations) {
                this.showCameraRecommendations(data.camera_recommendations);
            }
        } catch (error) {
            console.error('Error cargando recomendaciones:', error);
        }
    }
    
    showCameraRecommendations(recommendations) {
        // 📱 Mostrar instrucciones de posición de cámara
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="rom-phase rom-preparation">
                <div class="rom-card">
                    <div class="rom-header">
                        <i class="bi bi-camera" style="font-size: 2rem; color: var(--biomech-cyan);"></i>
                        <h2>Preparación de Cámara</h2>
                        <p class="text-secondary">Configura tu cámara para obtener mejores resultados</p>
                    </div>
                    
                    <div class="camera-instructions">
                        <div class="instruction-item">
                            <div class="instruction-icon">
                                <i class="bi bi-rulers"></i>
                            </div>
                            <div class="instruction-content">
                                <h4>Altura de Cámara</h4>
                                <p><strong>${recommendations.height_cm} cm</strong> del suelo</p>
                                <small class="text-muted">Basado en tu altura corporal</small>
                            </div>
                        </div>
                        
                        <div class="instruction-item">
                            <div class="instruction-icon">
                                <i class="bi bi-arrows-expand"></i>
                            </div>
                            <div class="instruction-content">
                                <h4>Distancia</h4>
                                <p><strong>${recommendations.distance_cm} cm</strong> de separación</p>
                                <small class="text-muted">Aproximadamente 1.5 metros</small>
                            </div>
                        </div>
                        
                        <div class="instruction-item">
                            <div class="instruction-icon">
                                <i class="bi bi-person-standing"></i>
                            </div>
                            <div class="instruction-content">
                                <h4>Posición</h4>
                                <p><strong>De perfil</strong> al ejercicio</p>
                                <small class="text-muted">${recommendations.instructions}</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="rom-actions">
                        <button class="btn btn-primary btn-lg" onclick="romSession.startCalibration()">
                            <i class="bi bi-play-circle"></i>
                            Continuar con Calibración
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    async startCalibration() {
        // """📏 Iniciar fase de calibración"""
        this.currentPhase = 'calibration';
        
        try {
            // Llamar API para iniciar calibración
            const response = await fetch(`/api/rom/start_calibration/${this.segment}/${this.exercise}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showCalibrationUI();
            } else {
                throw new Error(data.error || 'Error iniciando calibración');
            }
        } catch (error) {
            console.error('Error iniciando calibración:', error);
            this.showError('Error iniciando calibración: ' + error.message);
        }
    }
    
    showCalibrationUI() {
        // """⚖️ Mostrar UI de calibración"""
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="rom-phase rom-calibration">
                <div class="rom-card">
                    <div class="rom-header">
                        <i class="bi bi-bullseye" style="font-size: 2rem; color: var(--biomech-primary);"></i>
                        <h2>Calibración Anatómica</h2>
                        <p class="text-secondary">Adopta la posición erguida para establecer el punto de referencia</p>
                    </div>
                    
                    <div class="calibration-instructions">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i>
                            <strong>Instrucciones:</strong><br>
                            • Ponte de pie, erguido/a<br>
                            • Brazos a los lados del cuerpo<br>
                            • Mantén esta posición hasta que se complete la calibración
                        </div>
                        
                        <div class="calibration-status">
                            <div class="position-indicator">
                                <div class="indicator-circle" id="calibration-indicator">
                                    <div class="countdown-text" id="calibration-countdown" style="font-size: 72px; font-weight: bold; color: #007bff; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">5</div>
                                </div>
                            </div>
                            <p class="status-text">Preparándose para calibrar...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Iniciar countdown de calibración
        this.startCalibrationCountdown();
    }
    
    startCalibrationCountdown() {
        // """⏰ Countdown para calibración - 5 segundos"""
        let countdown = 5;
        const countdownElement = document.getElementById('calibration-countdown');
        const statusText = document.querySelector('.status-text');
        
        this.countdownTimer = setInterval(() => {
            if (countdown > 0) {
                countdownElement.textContent = countdown;
                statusText.textContent = `Calibrando en ${countdown} segundos...`;
                countdown--;
            } else {
                clearInterval(this.countdownTimer);
                this.performCalibration();
            }
        }, 1000);
    }
    
    async performCalibration() {
        // """⚖️ Realizar calibración con ángulo actual"""
        try {
            // Simular obtención de ángulo actual del stream
            // En implementación real, obtener del stream de MediaPipe
            const currentAngle = this.getCurrentAngleFromStream();
            
            const response = await fetch(`/api/rom/calibrate/${this.segment}/${this.exercise}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({angle: currentAngle})
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.sessionData.calibrated = true;
                this.sessionData.calibrationAngle = data.calibration_angle;
                
                // Mostrar éxito y continuar
                this.showCalibrationSuccess();
                setTimeout(() => this.showMeasurementInstructions(), 2000);
            } else {
                throw new Error(data.error || 'Error en calibración');
            }
        } catch (error) {
            console.error('Error en calibración:', error);
            this.showError('Error en calibración: ' + error.message);
        }
    }
    
    getCurrentAngleFromStream() {
        // """📐 Obtener ángulo actual del stream (placeholder)"""
        // TODO: Integrar con el stream real de MediaPipe
        // Por ahora retornar valor simulado
        return 0; // Posición anatómica = 0°
    }
    
    showCalibrationSuccess() {
        // """✅ Mostrar éxito de calibración"""
        const indicator = document.getElementById('calibration-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (indicator && statusText) {
            indicator.innerHTML = '<i class="bi bi-check-lg" style="color: var(--biomech-success); font-size: 2rem;"></i>';
            statusText.textContent = '¡Calibración completada exitosamente!';
            statusText.style.color = 'var(--biomech-success)';
        }
    }
    
    showMeasurementInstructions() {
        // """📋 Mostrar instrucciones pre-medición"""
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="rom-phase rom-pre-measurement">
                <div class="rom-card">
                    <div class="rom-header">
                        <i class="bi bi-activity" style="font-size: 2rem; color: var(--biomech-warning);"></i>
                        <h2>¡Prepárate para el Análisis!</h2>
                        <p class="text-secondary">Vas a realizar tu máximo movimiento durante 20 segundos</p>
                    </div>
                    
                    <div class="measurement-instructions">
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            <strong>¡Importante!</strong><br>
                            • Realiza tu <strong>máximo rango de movimiento</strong><br>
                            • Mantén el movimiento fluido y controlado<br>
                            • No fuerces ni causes dolor<br>
                            • El sistema guardará automáticamente tu mejor resultado
                        </div>
                        
                        <div class="start-countdown">
                            <div class="big-button-container">
                                <button class="btn btn-success btn-lg start-measurement-btn" onclick="romSession.startMeasurement()">
                                    <i class="bi bi-play-fill"></i>
                                    <span>Iniciar Medición ROM</span>
                                    <small>20 segundos</small>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async startMeasurement() {
        // """🚀 Iniciar sesión de medición ROM"""
        this.currentPhase = 'measurement';
        
        // 🆕 MOSTRAR OVERLAY INTEGRADO
        this.showIntegratedOverlay();
        
        this.showMeasurementUI();
        
        try {
            // Iniciar sesión en backend
            const response = await fetch(`/api/rom/start_session/${this.segment}/${this.exercise}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.sessionData.sessionActive = true;
                this.showMeasurementUI();
                this.startMeasurementTimer();
            } else {
                throw new Error(data.error || 'Error iniciando medición');
            }
        } catch (error) {
            console.error('Error iniciando medición:', error);
            this.showError('Error iniciando medición: ' + error.message);
        }
    }
    
    showMeasurementUI() {
        // """📊 Mostrar UI de medición activa"""
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="rom-phase rom-measuring">
                <div class="rom-card measuring-active">
                    <div class="rom-header">
                        <i class="bi bi-stopwatch" style="font-size: 2rem; color: var(--biomech-danger);"></i>
                        <h2>¡Realizando Medición!</h2>
                        <p class="text-secondary">Haz tu máximo movimiento ahora</p>
                    </div>
                    
                    <div class="measurement-display">
                        <div class="timer-display" style="text-align: center; background: rgba(0,0,0,0.8); border-radius: 15px; padding: 20px; margin: 20px;">
                            <div class="timer-circle" style="background: linear-gradient(45deg, #007bff, #0056b3); border-radius: 50%; width: 120px; height: 120px; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px;">
                                <span id="measurement-timer" style="font-size: 48px; font-weight: bold; color: white;">20</span>
                            </div>
                            <p class="timer-label" style="color: white; font-size: 18px; margin: 10px 0; font-weight: bold;">SEGUNDOS RESTANTES</p>                        <div class="rom-metrics">
                            <div class="metric-item">
                                <div class="metric-value" id="current-rom">0°</div>
                                <div class="metric-label">ROM Actual</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value" id="max-rom">0°</div>
                                <div class="metric-label">ROM Máximo</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="measurement-progress">
                        <div class="progress">
                            <div class="progress-bar" id="measurement-progress-bar" style="width: 0%;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    startMeasurementTimer() {
        // """⏰ Timer dinámico desde EXERCISE_CONFIG"""
        const duration = window.EXERCISE_CONFIG?.duration_seconds || 14;
        let timeLeft = duration;
        const timerElement = document.getElementById('measurement-timer');
        const progressBar = document.getElementById('measurement-progress-bar');
        
        // 🆕 Mostrar timer en overlay también
        this.showOverlayTimer(timeLeft);
        
        this.timer = setInterval(() => {
            if (timeLeft > 0) {
                timerElement.textContent = timeLeft;
                
                // 🆕 Actualizar overlay timer
                this.showOverlayTimer(timeLeft);
                
                // Actualizar barra de progreso
                const progress = ((duration - timeLeft) / duration) * 100;
                progressBar.style.width = progress + '%';
                
                // Cambiar colores en últimos 5 segundos
                if (timeLeft <= 5) {
                    timerElement.style.color = 'var(--biomech-danger)';
                    if (timeLeft <= 3) {
                        // Efecto parpadeo en últimos 3 segundos
                        timerElement.style.animation = 'pulse 0.5s infinite';
                    }
                }
                
                timeLeft--;
            } else {
                clearInterval(this.timer);
                this.endMeasurement();
            }
        }, 1000);
        
        // Simular actualización de ROM (en implementación real, viene del stream)
        this.startROMUpdates();
    }
    
    startROMUpdates() {
        // """📊 Simular actualizaciones de ROM (placeholder)"""
        // TODO: Integrar con stream real de MediaPipe
        this.romUpdateInterval = setInterval(() => {
            if (this.sessionData.sessionActive) {
                // Simular ROM creciente
                const currentROM = Math.random() * 120; // 0-120 grados
                const maxROM = Math.max(this.sessionData.maxROM, currentROM);
                
                this.updateROMDisplay(currentROM, maxROM);
                this.sessionData.maxROM = maxROM;
            }
        }, 100);
    }
    
    updateROMDisplay(current, max) {
        // """📊 Actualizar display de ROM en tiempo real"""
        const currentElement = document.getElementById('current-rom');
        const maxElement = document.getElementById('max-rom');
        
        if (currentElement) currentElement.textContent = Math.round(current) + '°';
        if (maxElement) maxElement.textContent = Math.round(max) + '°';
        
        // 🆕 Actualizar overlay integrado también
        this.updateOverlayAngles(current, max);
    }
    
    async endMeasurement() {
        // """⏹️ Finalizar medición y mostrar resultados"""
        this.sessionData.sessionActive = false;
        
        if (this.romUpdateInterval) {
            clearInterval(this.romUpdateInterval);
        }
        
        try {
            // Finalizar sesión en backend
            const response = await fetch(`/api/rom/end_session/${this.segment}/${this.exercise}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showResults(data.results);
            } else {
                throw new Error(data.error || 'Error finalizando medición');
            }
        } catch (error) {
            console.error('Error finalizando medición:', error);
            this.showError('Error finalizando medición: ' + error.message);
        }
    }
    
    showResults(results) {
        // """📊 Mostrar resultados finales"""
        this.currentPhase = 'results';
        
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        const classificationInfo = results.classification_info;
        const classificationColor = this.getClassificationColor(classificationInfo.level);
        
        container.innerHTML = `
            <div class="rom-phase rom-results">
                <div class="rom-card">
                    <div class="rom-header">
                        <i class="bi bi-trophy" style="font-size: 2rem; color: ${classificationColor};"></i>
                        <h2>¡Análisis Completado!</h2>
                        <p class="text-secondary">Resultados de tu evaluación ROM</p>
                    </div>
                    
                    <div class="results-display">
                        <div class="main-result">
                            <div class="rom-value">${results.max_rom}°</div>
                            <div class="rom-label">ROM Máximo Alcanzado</div>
                        </div>
                        
                        <div class="classification">
                            <div class="classification-badge" style="background-color: ${classificationColor};">
                                ${classificationInfo.level.toUpperCase()}
                            </div>
                            <p class="classification-description">${classificationInfo.description}</p>
                            <small class="classification-range">Rango: ${classificationInfo.range}</small>
                        </div>
                        
                        ${results.best_frame ? `
                        <div class="best-frame">
                            <h5>Tu Mejor Posición</h5>
                            <img src="data:image/jpeg;base64,${results.best_frame}" 
                                 alt="Mejor frame ROM" class="best-frame-image">
                        </div>
                        ` : ''}
                        
                        <div class="session-stats">
                            <div class="stat-item">
                                <span class="stat-value">${results.total_measurements}</span>
                                <span class="stat-label">Mediciones</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${Math.round(results.session_duration)}s</span>
                                <span class="stat-label">Duración</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${classificationInfo.percentage}%</span>
                                <span class="stat-label">Del rango óptimo</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="rom-actions">
                        <button class="btn btn-primary" onclick="romSession.restart()">
                            <i class="bi bi-arrow-clockwise"></i>
                            Realizar Nuevo Análisis
                        </button>
                        <button class="btn btn-success" onclick="window.location.href='/results/${this.segment}'">
                            <i class="bi bi-graph-up"></i>
                            Ver Historial
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    getClassificationColor(level) {
        // """🎨 Obtener color según clasificación"""
        const colors = {
            'optimal': 'var(--biomech-success)',
            'good': 'var(--biomech-primary)', 
            'needs_work': 'var(--biomech-warning)',
            'limited': 'var(--biomech-danger)'
        };
        return colors[level] || 'var(--biomech-secondary)';
    }
    
    restart() {
        // """🔄 Reiniciar análisis ROM"""
        // Limpiar timers
        if (this.timer) clearInterval(this.timer);
        if (this.countdownTimer) clearInterval(this.countdownTimer);
        if (this.romUpdateInterval) clearInterval(this.romUpdateInterval);
        
        // Resetear estado
        this.currentPhase = 'preparation';
        this.sessionData = {
            calibrationAngle: null,
            maxROM: 0,
            currentROM: 0,
            sessionActive: false,
            calibrated: false
        };
        
        // Reiniciar UI
        this.loadCameraRecommendations();
    }
    
    showError(message) {
        // """❌ Mostrar mensaje de error"""
        const container = document.getElementById('rom-session-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="rom-phase rom-error">
                <div class="rom-card">
                    <div class="rom-header">
                        <i class="bi bi-exclamation-triangle" style="font-size: 2rem; color: var(--biomech-danger);"></i>
                        <h2>Error en Análisis ROM</h2>
                        <p class="text-secondary">Se produjo un problema durante el análisis</p>
                    </div>
                    
                    <div class="alert alert-danger">
                        <strong>Error:</strong> ${message}
                    </div>
                    
                    <div class="rom-actions">
                        <button class="btn btn-primary" onclick="romSession.restart()">
                            <i class="bi bi-arrow-clockwise"></i>
                            Intentar de Nuevo
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupUI() {
        // """🎨 Configurar estilos CSS para ROM Session"""
        if (!document.getElementById('rom-session-styles')) {
            const styles = document.createElement('style');
            styles.id = 'rom-session-styles';
            styles.textContent = `
                .rom-phase {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.95);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                }
                
                .rom-card {
                    background: var(--biomech-glass-bg);
                    backdrop-filter: blur(10px);
                    border: 1px solid var(--biomech-glass-border);
                    border-radius: 20px;
                    padding: 2rem;
                    max-width: 600px;
                    width: 90%;
                    max-height: 90%;
                    overflow-y: auto;
                    text-align: center;
                }
                
                .rom-header h2 {
                    color: var(--biomech-cyan);
                    margin: 1rem 0;
                }
                
                .timer-circle {
                    width: 120px;
                    height: 120px;
                    border: 4px solid var(--biomech-primary);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1rem;
                    background: rgba(0, 255, 255, 0.1);
                }
                
                .timer-text {
                    font-size: 2.5rem;
                    font-weight: bold;
                    color: var(--biomech-cyan);
                }
                
                .rom-metrics {
                    display: flex;
                    justify-content: space-around;
                    margin: 2rem 0;
                }
                
                .metric-item {
                    text-align: center;
                }
                
                .metric-value {
                    font-size: 2rem;
                    font-weight: bold;
                    color: var(--biomech-primary);
                }
                
                .best-frame-image {
                    max-width: 300px;
                    border-radius: 10px;
                    margin: 1rem 0;
                }
                
                .rom-value {
                    font-size: 4rem;
                    font-weight: bold;
                    color: var(--biomech-success);
                    margin-bottom: 0.5rem;
                }
                
                .classification-badge {
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                    margin: 1rem 0;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    // 🆕 FUNCIONES PARA OVERLAY INTEGRADO
    showIntegratedOverlay() {
        const overlay = document.getElementById('romOverlay');
        if (overlay) {
            overlay.style.display = 'block';
            this.updateOverlayStatus('Activo');
        }
    }
    
    hideIntegratedOverlay() {
        const overlay = document.getElementById('romOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    updateOverlayStatus(status) {
        const statusElement = document.getElementById('romStatus');
        if (statusElement) {
            statusElement.textContent = status;
            
            // Cambiar color según estado
            const colors = {
                'Inactivo': '#6c757d',
                'Calibrando': '#ffc107',
                'Activo': '#28a745',
                'Finalizado': '#007bff'
            };
            statusElement.style.color = colors[status] || '#6c757d';
        }
    }
    
    updateOverlayAngles(current, max) {
        const currentElement = document.getElementById('romCurrentAngle');
        const maxElement = document.getElementById('romMaxAngle');
        
        if (currentElement) currentElement.textContent = Math.round(current) + '°';
        if (maxElement) maxElement.textContent = Math.round(max) + '°';
    }
    
    showOverlayTimer(seconds) {
        const timerElement = document.getElementById('romTimerCompact');
        const secondsElement = document.getElementById('romTimerSeconds');
        
        if (timerElement && secondsElement) {
            timerElement.style.display = 'block';
            secondsElement.textContent = seconds;
        }
    }
    
    hideOverlayTimer() {
        const timerElement = document.getElementById('romTimerCompact');
        if (timerElement) {
            timerElement.style.display = 'none';
        }
    }
}

// 🔴 REMOVIDO: Variable global declarada en analysis.html
// (Evitar duplicación que causa SyntaxError)
// La variable romSession ahora se declara en analysis.html línea ~388
