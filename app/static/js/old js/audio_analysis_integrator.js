/**
 * 🔗 INTEGRADOR DE AUDIO CON ANÁLISIS BIOMECÁNICO
 * 
 * Conecta el sistema de audio con los timers y fases del análisis
 * sin modificar la lógica existente de cámara o handlers
 */

class AudioAnalysisIntegrator {
    constructor() {
        this.audioGuide = null;
        this.isIntegrated = false;
        this.currentExerciseConfig = null;
        
        console.log('🔗 AudioAnalysisIntegrator initialized');
        
        // Esperar a que el sistema de audio esté disponible
        this.waitForAudioSystem();
    }
    
    /**
     * ⏳ Esperar a que el sistema de audio esté disponible
     */
    waitForAudioSystem() {
        if (window.audioGuide && window.audioGuide.isInitialized) {
            this.initializeIntegration();
        } else {
            // Escuchar el evento de que el audio esté listo
            window.addEventListener('audioGuideReady', () => {
                this.initializeIntegration();
            });
            
            // Fallback: revisar cada 500ms por máximo 10 segundos
            let attempts = 0;
            const checkAudio = setInterval(() => {
                attempts++;
                if (window.audioGuide && window.audioGuide.isInitialized) {
                    clearInterval(checkAudio);
                    this.initializeIntegration();
                } else if (attempts > 20) {
                    clearInterval(checkAudio);
                    console.warn('⚠️ AudioGuideSystem not available after 10 seconds');
                }
            }, 500);
        }
    }
    
    /**
     * 🚀 Inicializar integración con el sistema existente
     */
    initializeIntegration() {
        this.audioGuide = window.audioGuide;
        
        // Obtener configuración del ejercicio desde el contexto global
        this.extractExerciseConfig();
        
        // Integrar con los puntos clave del análisis
        this.integrateWithAnalysisFlow();
        
        this.isIntegrated = true;
        console.log('🔗 Audio integration active');
    }
    
    /**
     * 📋 Extraer configuración del ejercicio
     */
    extractExerciseConfig() {
        // Intentar obtener configuración desde variables globales existentes
        if (typeof EXERCISE_CONFIG !== 'undefined') {
            this.currentExerciseConfig = EXERCISE_CONFIG;
        } else if (window.EXERCISE_CONFIG) {
            this.currentExerciseConfig = window.EXERCISE_CONFIG;
        } else {
            // Fallback desde el DOM o URL
            this.extractConfigFromDOM();
        }
        
        console.log('📋 Exercise config:', this.currentExerciseConfig);
    }
    
    /**
     * 🔍 Extraer configuración desde el DOM
     */
    extractConfigFromDOM() {
        try {
            // Intentar desde meta tags o elementos del DOM
            const titleElement = document.querySelector('h2');
            const segmentInfo = document.querySelector('.text-secondary');
            
            if (titleElement && segmentInfo) {
                const exerciseName = titleElement.textContent.trim();
                const segmentText = segmentInfo.textContent.toLowerCase();
                
                let segment = 'shoulder'; // default
                if (segmentText.includes('hombro')) segment = 'shoulder';
                else if (segmentText.includes('codo')) segment = 'elbow';
                else if (segmentText.includes('rodilla')) segment = 'knee';
                else if (segmentText.includes('cadera')) segment = 'hip';
                else if (segmentText.includes('tobillo')) segment = 'ankle';
                else if (segmentText.includes('cuello')) segment = 'neck';
                
                let exercise = 'flexion'; // default
                if (exerciseName.toLowerCase().includes('flexión')) exercise = 'flexion';
                else if (exerciseName.toLowerCase().includes('extensión')) exercise = 'extension';
                else if (exerciseName.toLowerCase().includes('abducción')) exercise = 'abduction';
                else if (exerciseName.toLowerCase().includes('aducción')) exercise = 'adduction';
                
                this.currentExerciseConfig = {
                    segment: segment,
                    exercise: exercise,
                    exercise_name: exerciseName,
                    segment_name: segment.charAt(0).toUpperCase() + segment.slice(1)
                };
            }
        } catch (error) {
            console.warn('⚠️ Could not extract config from DOM:', error);
            // Configuración por defecto
            this.currentExerciseConfig = {
                segment: 'shoulder',
                exercise: 'flexion',
                exercise_name: 'Flexión de Hombro',
                segment_name: 'Hombro'
            };
        }
    }
    
    /**
     * 🔄 Integrar con el flujo de análisis existente
     */
    integrateWithAnalysisFlow() {
        // Interceptar las funciones de análisis existentes sin modificarlas
        this.interceptAnalysisFunctions();
        
        // Escuchar eventos específicos del DOM
        this.setupDOMObservers();
    }
    
    /**
     * 🎯 Interceptar funciones de análisis
     */
    interceptAnalysisFunctions() {
        // 1. Interceptar el inicio del countdown de calibración (5 segundos)
        this.interceptCalibrationCountdown();
        
        // 2. Interceptar el inicio del análisis ROM (20 segundos)
        this.interceptROMAnalysis();
        
        // 3. Interceptar la finalización del análisis
        this.interceptAnalysisCompletion();
    }
    
    /**
     * ⏰ Interceptar countdown de calibración
     */
    interceptCalibrationCountdown() {
        // Buscar patrones en el DOM que indiquen inicio de calibración
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.ELEMENT_NODE) {
                            const text = node.textContent || '';
                            
                            // Detectar inicio de posicionamiento
                            if (text.includes('POSICIONAMIENTO') && text.includes('segundos restantes')) {
                                this.triggerPositioningPhase();
                            }
                        }
                    });
                }
                
                if (mutation.type === 'characterData') {
                    const text = mutation.target.textContent || '';
                    
                    // Detectar countdown de posicionamiento
                    if (text.includes('POSICIONAMIENTO') && text.includes('segundos restantes')) {
                        this.triggerPositioningPhase();
                    }
                }
            });
        });
        
        // Observar cambios en el área de estado
        const statusElements = document.querySelectorAll('[class*="status"], [id*="status"], .alert');
        statusElements.forEach(element => {
            observer.observe(element, {
                childList: true,
                subtree: true,
                characterData: true
            });
        });
    }
    
    /**
     * 🏃‍♂️ Interceptar análisis ROM
     */
    interceptROMAnalysis() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const text = (mutation.target.textContent || '') + 
                                (mutation.addedNodes?.[0]?.textContent || '');
                    
                    // Detectar inicio de análisis ROM
                    if (text.includes('ANÁLISIS ROM') && 
                        (text.includes('¡Realiza el ejercicio!') || text.includes('20 segundos'))) {
                        this.triggerExercisePhase();
                    }
                    
                    // Detectar finalización
                    if (text.includes('Análisis completado') || 
                        text.includes('✅') && text.includes('completado')) {
                        this.triggerCompletionPhase();
                    }
                }
            });
        });
        
        // Observar cambios en elementos de estado y overlay
        const observeElements = document.querySelectorAll(
            '[class*="status"], [id*="status"], [class*="overlay"], [id*="overlay"], .alert'
        );
        observeElements.forEach(element => {
            observer.observe(element, {
                childList: true,
                subtree: true,
                characterData: true
            });
        });
    }
    
    /**
     * ✅ Interceptar finalización de análisis
     */
    interceptAnalysisCompletion() {
        // Ya está manejado en interceptROMAnalysis()
        // Pero podemos agregar observadores adicionales para elementos específicos
        
        // Observar cambios en botones que indiquen finalización
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    const element = mutation.target;
                    
                    // Detectar si aparecen botones de resultados o navegación
                    if (element.textContent && 
                        (element.textContent.includes('Ver Resultados') || 
                         element.textContent.includes('Nuevo Análisis'))) {
                        this.triggerCompletionPhase();
                    }
                }
            });
        });
        
        // Observar botones
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            observer.observe(button, {
                attributes: true,
                attributeFilter: ['style', 'class', 'disabled']
            });
        });
    }
    
    /**
     * 📦 Configurar observadores del DOM
     */
    setupDOMObservers() {
        // Observador general para cambios importantes en el DOM
        const mainObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                // Detectar adición de elementos relacionados con timers
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Detectar elementos de countdown
                            if (node.id && node.id.includes('countdown')) {
                                this.handleCountdownElement(node);
                            }
                            
                            // Detectar overlays de timer
                            if (node.className && node.className.includes('overlay')) {
                                this.handleOverlayElement(node);
                            }
                        }
                    });
                }
            });
        });
        
        // Observar el body completo
        mainObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    /**
     * ⏰ Manejar elementos de countdown
     */
    handleCountdownElement(element) {
        console.log('⏰ Countdown element detected:', element.id);
        
        // Si es el countdown de calibración, disparar fase de posicionamiento
        if (element.id.includes('calibration')) {
            this.triggerPositioningPhase();
        }
    }
    
    /**
     * 🎭 Manejar elementos de overlay
     */
    handleOverlayElement(element) {
        console.log('🎭 Overlay element detected:', element.className);
        
        // Detectar si es un overlay de timer activo
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    const text = element.textContent || '';
                    
                    // Si muestra números de countdown, podría ser fase de ejercicio
                    if (/\d+\s*s?$/.test(text.trim()) && !text.includes('Posiciónate')) {
                        // Podría ser el timer de 20 segundos
                        const number = parseInt(text.match(/\d+/)[0]);
                        if (number <= 20 && number >= 15) {
                            this.triggerExercisePhase();
                        }
                    }
                }
            });
        });
        
        observer.observe(element, {
            childList: true,
            subtree: true,
            characterData: true
        });
    }
    
    /**
     * 🎯 DISPARADORES DE FASES
     */
    
    /**
     * 📝 Helper: Convertir timing string a milisegundos
     * Soporta: "3s", "3000ms", 3 (número = segundos)
     */
    parseTimingToMs(timing) {
        if (typeof timing === 'number') {
            return timing * 1000; // Asumir segundos
        }
        if (typeof timing === 'string') {
            if (timing.endsWith('ms')) {
                return parseInt(timing);
            } else if (timing.endsWith('s')) {
                return parseFloat(timing) * 1000;
            } else {
                return parseFloat(timing) * 1000; // Asumir segundos
            }
        }
        return 0;
    }
    
    triggerPositioningPhase() {
        if (!this.audioGuide || !this.currentExerciseConfig) return;
        
        // Evitar múltiples llamadas
        if (this.audioGuide.currentPhase === 'positioning') return;
        
        console.log('🧍 Triggering positioning phase with tts_phases timing');
        
        // Obtener configuración de TTS phases
        const ttsPhases = this.currentExerciseConfig.tts_phases || {};
        
        // Programar fases según timing de exercises.json
        if (ttsPhases.welcome) {
            this.audioGuide.speak(ttsPhases.welcome.text, 'high');
            
            // Programar positioning después de welcome
            if (ttsPhases.positioning) {
                const welcomeDuration = this.parseTimingToMs(ttsPhases.welcome.duration || 2);
                setTimeout(() => {
                    if (this.audioGuide) {
                        this.audioGuide.speak(ttsPhases.positioning.text, 'high');
                    }
                }, welcomeDuration);
            }
        } else if (ttsPhases.positioning) {
            // Si no hay welcome, solo positioning
            this.audioGuide.speak(ttsPhases.positioning.text, 'high');
        } else {
            // Fallback al método original
            this.audioGuide.startPositioningPhase(
                this.currentExerciseConfig.segment, 
                this.currentExerciseConfig.exercise
            );
        }
    }
    
    triggerExercisePhase() {
        if (!this.audioGuide || !this.currentExerciseConfig) return;
        
        // Evitar múltiples llamadas
        if (this.audioGuide.currentPhase === 'exercise') return;
        
        console.log('🏃‍♂️ Triggering exercise phase with tts_phases timing');
        
        // Obtener configuración de TTS phases
        const ttsPhases = this.currentExerciseConfig.tts_phases || {};
        
        if (ttsPhases.exercise_start) {
            // Anunciar inicio de ejercicio
            this.audioGuide.speak(ttsPhases.exercise_start.text, 'high');
            
            // 🆕 STEP 3: Programar countdown a los 11 segundos
            const duration = this.currentExerciseConfig.duration_seconds || 14;
            const countdownStart = duration - 3; // Comenzar countdown 3 segundos antes del final
            
            if (ttsPhases.countdown) {
                setTimeout(() => {
                    if (this.audioGuide) {
                        this.audioGuide.speak(ttsPhases.countdown.text, 'high');
                    }
                }, countdownStart * 1000);
            }
        } else {
            // Fallback al método original
            this.audioGuide.startExercisePhase(
                this.currentExerciseConfig.segment, 
                this.currentExerciseConfig.exercise
            );
        }
    }
    
    triggerCompletionPhase() {
        if (!this.audioGuide) return;
        
        // Evitar múltiples llamadas
        if (this.audioGuide.currentPhase === 'completed') return;
        
        console.log('✅ Triggering completion phase');
        
        // Obtener configuración de TTS phases
        const ttsPhases = this.currentExerciseConfig?.tts_phases || {};
        
        if (ttsPhases.completion) {
            this.audioGuide.speak(ttsPhases.completion.text, 'normal');
        } else {
            // Fallback al método original
            this.audioGuide.completeAnalysis();
        }
    }
    
    /**
     * 📊 Estado del integrador
     */
    getStatus() {
        return {
            isIntegrated: this.isIntegrated,
            hasAudioGuide: !!this.audioGuide,
            hasExerciseConfig: !!this.currentExerciseConfig,
            currentExerciseConfig: this.currentExerciseConfig,
            audioGuideStatus: this.audioGuide?.getStatus()
        };
    }
}

// 🌍 Instancia global
let audioAnalysisIntegrator = null;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Pequeña pausa para asegurar que todos los scripts estén cargados
    setTimeout(() => {
        audioAnalysisIntegrator = new AudioAnalysisIntegrator();
        window.audioAnalysisIntegrator = audioAnalysisIntegrator;
        
        console.log('🔗 AudioAnalysisIntegrator ready');
    }, 1000);
});

console.log('📁 audio_analysis_integrator.js loaded');