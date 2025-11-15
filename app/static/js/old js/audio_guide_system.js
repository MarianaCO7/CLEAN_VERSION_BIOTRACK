/**
 * 🔊 SISTEMA DE GUÍA AUDITIVA BIOMECÁNICA
 * 
 * Sistema modular de instrucciones de voz para análisis biomecánico
 * Sincronizado con timers existentes sin modificar lógic                // 🧍 Positioning phase (5 seconds)
                positioning: {
                    start: "Prepare for biomechanical analysis. Position yourself correctly in front of the camera.",
                    instructions: {
                        shoulder: "Stand upright, arms relaxed at your sides. Natural and upright posture.",
                        elbow: "Position yourself sideways to the camera. Arm relaxed at your side. Stable position.",
                        knee: "Stand facing the camera. Legs slightly apart. Maintain balance.",
                        hip: "Position yourself sideways to the camera. Maintain balance and natural posture.",
                        ankle: "Sit comfortably facing the camera with your foot completely visible.",
                        neck: "Stand upright facing the camera. Head in neutral and relaxed position."
                    },
                    countdown: "Analysis will begin in",
                    ready: "Perfect! Starting analysis."
                },* 
 * Características:
 * - Multi-idioma (ES/EN)
 * - Control de volumen y on/off
 * - Sincronización con timers de 5s y 20s
 * - Instrucciones contextuales por ejercicio
 * - Alertas en últimos 5 segundos
 */

class AudioGuideSystem {
    constructor() {
        this.enabled = true;
        this.volume = 0.7;
        this.language = 'es'; // 'es' | 'en'
        this.synth = window.speechSynthesis;
        this.voice = null;
        
        // 🎛️ Estado del sistema
        this.isInitialized = false;
        this.currentPhase = null; // 'positioning' | 'exercise' | 'completed'
        
        // 🔄 Cache de configuraciones
        this.exerciseConfig = null;
        this.exercisesData = null; // Cache para exercises.json
        
        // ⏰ Array para rastrear todos los timeouts activos
        this.activeTimeouts = [];
        
        this.initializeVoices();
        this.loadExercisesConfig(); // Cargar configuración de ejercicios
    }
    
    /**
     * 🎤 Inicializar voces disponibles
     */
    async initializeVoices() {
        return new Promise((resolve) => {
            if (this.synth.getVoices().length > 0) {
                this.selectBestVoice();
                this.isInitialized = true;
                resolve();
            } else {
                this.synth.addEventListener('voiceschanged', () => {
                    this.selectBestVoice();
                    this.isInitialized = true;
                    resolve();
                });
            }
        });
    }
    
    /**
     * 🎯 Seleccionar la mejor voz disponible - PRIORIDAD VOZ FEMENINA ESPAÑOLA
     */
    selectBestVoice() {
        const voices = this.synth.getVoices();
        
        // 🎤 VOCES ESPAÑOLAS FEMENINAS - MÁXIMA PRIORIDAD
        const voicePreferences = {
            'es': [
                // 🚺 VOZ DALIA (Microsoft Narrator México) - MÁXIMA PRIORIDAD
                'Microsoft Dalia Online (Natural) - Spanish (Mexico)',
                'Dalia',
                
                // 🚺 VOCES FEMENINAS ESPAÑOLAS DE ESPAÑA
                'Microsoft Helena - Spanish (Spain)',
                'Microsoft Paloma Online (Natural) - Spanish (Spain)',
                'Google español de Estados Unidos', // Algunas versiones tienen buena calidad
                'Helena',
                'Paloma',
                
                // 🚺 VOCES FEMENINAS LATINOAMERICANAS (segunda prioridad)
                'Microsoft Sabina - Spanish (Mexico)',
                'Sabina',
                'Paulina',
                'Monica',
                
                // 🔄 FALLBACK: Cualquier voz española (puede ser masculina)
                'Microsoft Elvira - Spanish (Spain)', // Elvira puede ser masculina en algunos sistemas
                'Spanish (Spain)',
                'es-ES-Standard',
                'es-ES',
                'Spanish (Mexico)',
                'es-MX',
                'es-AR',
                'es-CO'
            ],
            'en': [
                // 🚺 VOCES FEMENINAS INGLESAS
                'Microsoft Zira - English (United States)',
                'Google US English',
                'Samantha',
                'en-US',
                'en-GB'
            ]
        };
        
        const preferred = voicePreferences[this.language];
        
        // 🎯 FASE 1: Búsqueda prioritaria de voces FEMENINAS ESPAÑOLAS
        for (const voiceName of preferred) {
            const voice = voices.find(v => {
                const name = v.name.toLowerCase();
                const lang = v.lang.toLowerCase();
                const searchTerm = voiceName.toLowerCase();
                
                // 🔍 Búsqueda exacta por nombre completo
                if (name.includes(searchTerm)) return true;
                
                // 🔍 Búsqueda por código de idioma nativo
                if (lang === searchTerm) return true;
                
                // 🔍 Verificar combinaciones de idioma
                if (searchTerm.includes('spain') && lang.includes('es-es')) return true;
                if (searchTerm.includes('mexico') && lang.includes('es-mx')) return true;
                
                return false;
            });
            
            if (voice) {
                this.voice = voice;
                return;
            }
        }
        
        // 🎯 FASE 2: BÚSQUEDA INTELIGENTE Y ESTRICTA DE VOCES FEMENINAS
        const femaleIndicators = [
            'female', 'woman', 'mujer', 'femenina',
            // Nombres femeninos CONFIRMADOS en TTS systems
            'dalia', 'helena', 'paloma', 'sabina', 'monica', 'paulina', 'lucia', 'carmen',
            'zira', 'samantha', 'victoria', 'karen', 'susan', 'allison', 'salli',
            'joanna', 'kendra', 'kimberly', 'ivy', 'emma', 'amy', 'nicole'
        ];
        
        // ❌ EXCLUIR EXPLÍCITAMENTE VOCES MASCULINAS
        const maleIndicators = [
            'male', 'man', 'hombre', 'masculino',
            'david', 'mark', 'jorge', 'pablo', 'miguel', 'diego', 'raul',
            'matthew', 'justin', 'joey', 'juan', 'enrique'
        ];
        
        const femaleVoice = voices.find(v => {
            const name = v.name.toLowerCase();
            const lang = v.lang.toLowerCase();
            
            // ❌ RECHAZAR si contiene indicador masculino
            const isMale = maleIndicators.some(indicator => name.includes(indicator));
            if (isMale) return false;
            
            // ✅ Voz española femenina (buscar indicadores)
            const isFemale = femaleIndicators.some(indicator => name.includes(indicator));
            const isSpanish = lang.startsWith(this.language) || 
                            lang.includes('es-') || 
                            lang.includes('spanish');
            
            return isFemale && isSpanish;
        });
        
        if (femaleVoice) {
            this.voice = femaleVoice;
            return;
        }
        
        // 🎯 FASE 3: FALLBACK - Cualquier voz española (último recurso)
        const spanishVoice = voices.find(v => {
            const lang = v.lang.toLowerCase();
            const name = v.name.toLowerCase();
            
            // ❌ RECHAZAR si es masculina explícita
            const maleIndicators = ['male', 'man', 'hombre', 'david', 'mark', 'jorge', 'miguel'];
            const isMale = maleIndicators.some(indicator => name.includes(indicator));
            
            const isSpanish = lang.startsWith(this.language) || 
                             lang.includes('es-') || 
                             lang.includes('spanish');
            
            return isSpanish && !isMale;
        });
        
        if (spanishVoice) {
            this.voice = spanishVoice;
            console.warn('⚠️⚠️⚠️ WARNING: NO HAY VOZ FEMENINA DISPONIBLE ⚠️⚠️⚠️');
            console.warn(`Usando voz española: ${spanishVoice.name} (${spanishVoice.lang})`);
            console.warn('RECOMENDACIÓN: Instalar voces españolas femeninas en Windows');
            console.warn('Panel de Control > Voz > Agregar voces');
            console.warn('========================================');
            return;
        }
        
        // 🎯 FASE 4: FALLBACK FINAL - Primera voz disponible
        this.voice = voices[0];
        console.error('❌❌❌ ERROR CRÍTICO: NO HAY VOCES ESPAÑOLAS ❌❌❌');
        console.error(`Usando fallback: ${this.voice?.name || 'none'}`);
        console.error('El sistema usará voz en inglés u otro idioma');
        console.error('========================================');
    }
    
    /**
     * 🔊 Reproducir mensaje de voz CON SOPORTE DE BEEP SIMULTÁNEO
     */
    speak(text, options = {}) {
        if (!this.enabled || !this.isInitialized || !text) return;
        
        // 🔔 REPRODUCIR BEEP SIMULTÁNEO SI SE SOLICITA
        if (options.playBeep) {
            this.playBeep(options.beepType || 'info');
        }
        
        // Cancelar speech anterior si está hablando
        this.synth.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.voice = this.voice;
        utterance.volume = options.volume || this.volume;
        
        // ⚡ RATE MEJORADO: Más lento para español nativo (mejor comprensión)
        utterance.rate = options.rate || 0.85; // Reducido de 0.9 a 0.85
        
        // 🎵 PITCH FEMENINO: Ligeramente más alto para voz femenina
        utterance.pitch = options.pitch || 1.1; // Aumentado de 1.0 a 1.1
        
        // 🇪🇸 CONFIGURACIÓN DE IDIOMA EXPLÍCITA
        utterance.lang = this.language === 'es' ? 'es-ES' : 'en-US';
        
        if (options.onEnd) {
            utterance.onend = options.onEnd;
        }
        
        this.synth.speak(utterance);
    }
    
    /**
     * 🔔 Sistema de BEEPS para alertas simultáneas
     * Permite reproducir un sonido breve mientras habla
     */
    playBeep(type = 'info') {
        // ✅ No reproducir beeps si el audio está deshabilitado
        if (!this.enabled) return;
        
        // 🎵 AudioContext API para generar beeps sintéticos
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // 🎚️ CONFIGURACIÓN POR TIPO DE BEEP
            const beepConfigs = {
                'info': { frequency: 800, duration: 0.15, volume: 0.3 },      // Tono suave informativo
                'success': { frequency: 1000, duration: 0.2, volume: 0.4 },   // Tono alto de éxito
                'warning': { frequency: 600, duration: 0.25, volume: 0.35 },  // Tono medio de advertencia
                'countdown': { frequency: 900, duration: 0.1, volume: 0.25 }, // Tono breve para conteo
                'start': { frequency: 1200, duration: 0.3, volume: 0.4 }      // Tono agudo de inicio
            };
            
            const config = beepConfigs[type] || beepConfigs['info'];
            
            oscillator.frequency.value = config.frequency;
            oscillator.type = 'sine'; // Onda suave, no agresiva
            
            gainNode.gain.setValueAtTime(config.volume, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + config.duration);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + config.duration);
            
        } catch (error) {
            console.warn('⚠️ No se pudo reproducir beep:', error);
        }
    }
    
    /**
     * 🔇 MÉTODOS DE CONTROL DE MUTE OPTIMIZADOS
     */
    toggleMute() {
        this.enabled = !this.enabled;
        
        // ✅ Si se desactiva, detener audio actual inmediatamente Y limpiar timeouts pendientes
        if (!this.enabled) {
            this.synth.cancel(); // Detener cualquier audio que esté sonando
            this.clearAllTimeouts(); // 🆕 Cancelar todos los timeouts programados
            console.log('🔇 Audio SILENCIADO - todos los timeouts cancelados');
        } else {
            console.log('🔊 Audio ACTIVADO');
        }
        
        // 🔄 Actualizar ícono flotante existente si está disponible
        if (window.audioToggleButton) {
            window.audioToggleButton.updateIcon(this.enabled);
        }
        
        return this.enabled;
    }
    
    mute() {
        this.enabled = false;
        this.synth.cancel(); // Detener audio actual
        this.clearAllTimeouts(); // 🆕 Cancelar todos los timeouts programados
        
        if (window.audioToggleButton) {
            window.audioToggleButton.updateIcon(false);
        }
    }
    
    unmute() {
        this.enabled = true;
        
        if (window.audioToggleButton) {
            window.audioToggleButton.updateIcon(true);
        }
    }
    
    /**
     * 🆕 Limpiar todos los timeouts pendientes
     */
    clearAllTimeouts() {
        this.activeTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
        this.activeTimeouts = [];
        console.log('⏰ Todos los timeouts de audio cancelados');
    }
    
    /**
     * 🆕 Registrar un setTimeout y guardarlo para poder cancelarlo después
     */
    registerTimeout(callback, delay) {
        const timeoutId = setTimeout(() => {
            // Remover el timeout de la lista cuando se ejecute
            const index = this.activeTimeouts.indexOf(timeoutId);
            if (index > -1) {
                this.activeTimeouts.splice(index, 1);
            }
            callback();
        }, delay);
        
        this.activeTimeouts.push(timeoutId);
        return timeoutId;
    }

    /**
     * 📥 Cargar configuración de ejercicios desde exercises.json
     */
    async loadExercisesConfig() {
        try {
            const response = await fetch('/api/exercises_config');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Error loading exercises config');
            }
            this.exercisesData = data.config; // El JSON está en data.config
        } catch (error) {
            console.error('❌ Error cargando exercises.json:', error);
            this.exercisesData = null;
        }
    }

    /**
     * 🔍 Obtener configuración TTS de un ejercicio específico
     */
    getExerciseTTSConfig(segment, exercise) {
        if (!this.exercisesData?.segments?.[segment]?.exercises?.[exercise]) {
            console.warn(`⚠️ No se encontró configuración TTS para ${segment}.${exercise}`);
            return null;
        }
        
        const exerciseData = this.exercisesData.segments[segment].exercises[exercise];
        return {
            camera_orientation: exerciseData.camera_orientation,
            tts_phases: exerciseData.tts_phases,
            segment,
            exercise
        };
    }

    /**
     * 🎯 Obtener mensajes del sistema (solo mensajes de UI, NO instrucciones de ejercicios)
     */
    getSystemMessages() {
        const messages = {
            'es': {
                completion: {
                    success: "¡Excelente! Análisis completado. Puedes relajarte.",
                    processing: "Procesando resultados. Mantente en posición unos segundos más."
                },
                system: {
                    audio_enabled: "Guía de voz activada",
                    audio_disabled: "Guía de voz desactivada",
                    language_changed: "Idioma cambiado a español"
                }
            },
            'en': {
                completion: {
                    success: "Excellent work! Analysis completed successfully. You can relax.",
                    processing: "Processing analysis results. Stay in position for a few more seconds while we finalize."
                },
                system: {
                    audio_enabled: "Voice guide enabled",
                    audio_disabled: "Voice guide disabled",
                    language_changed: "Language changed to English"
                }
            }
        };
        
        return messages[this.language];
    }
    
    /**
     * � NUEVA: Fase de bienvenida (welcome phase)
     * Reproduce el mensaje de bienvenida al inicio
     * @param {string} segment - shoulder, elbow, hip, knee, ankle, neck
     * @param {string} exercise - flexion, extension, etc.
     */
    async startWelcomePhase(segment, exercise) {
        this.currentPhase = 'welcome';
        
        // Obtener configuración TTS del ejercicio
        const ttsConfig = this.getExerciseTTSConfig(segment, exercise);
        if (!ttsConfig || !ttsConfig.tts_phases?.welcome) {
            console.warn(`⚠️ No hay tts_phases.welcome para ${segment}.${exercise}`);
            return;
        }
        
        const welcomePhase = ttsConfig.tts_phases.welcome;
        
        // Reproducir mensaje de bienvenida
        this.speak(welcomePhase.text, { 
            rate: 0.85, 
            volume: this.volume + 0.1,
            pitch: 1.15,
            playBeep: true,
            beepType: 'start'
        });
        
        console.log(`🎉 Welcome phase: ${welcomePhase.text}`);
    }

    /**
     * 🎯 NUEVA: Fase de posicionamiento (positioning phase) con validación de orientación
     * @param {string} segment - shoulder, elbow, hip, knee, ankle, neck
     * @param {string} exercise - flexion, extension, etc.
     * @param {Function} onValidationComplete - Callback cuando se valida la orientación
     * @returns {Promise} Resuelve cuando el usuario está correctamente posicionado
     */
    async startPositioningPhase(segment, exercise, onValidationComplete = null) {
        this.currentPhase = 'positioning';
        
        // Obtener configuración TTS del ejercicio
        const ttsConfig = this.getExerciseTTSConfig(segment, exercise);
        if (!ttsConfig || !ttsConfig.tts_phases?.positioning) {
            console.warn(`⚠️ No hay tts_phases.positioning para ${segment}.${exercise}`);
            return;
        }
        
        const positioningPhase = ttsConfig.tts_phases.positioning;
        const validation = positioningPhase.validation || {};
        
        // Reproducir instrucción de posicionamiento (rate más lento para claridad)
        this.speak(positioningPhase.text, { 
            rate: 0.70,  // Muy lento para instrucciones críticas
            volume: this.volume + 0.1,
            pitch: 1.1
        });
        
        console.log(`📍 Positioning phase: ${positioningPhase.text}`);
        console.log(`🔍 Validación requerida: ${validation.required_orientation || 'none'}`);
        
        // ⚠️ COMENTADO: Validación movida a analysis.html (antes del countdown)
        // La validación de orientación ahora se hace ANTES de reproducir audio de posicionamiento
        // Ver: analysis.html → startIntegratedROMSequence() → waitForCorrectOrientation()
        /*
        // Iniciar validación de orientación si es necesario
        if (validation.required_orientation && window.orientationValidator) {
            const timeout = (validation.timeout || 5) * 1000;
            
            try {
                await window.orientationValidator.waitForCorrectOrientation(
                    validation.required_orientation,
                    timeout
                );
                
                console.log(`✅ Orientación ${validation.required_orientation} validada correctamente`);
                
                if (onValidationComplete) {
                    onValidationComplete(true);
                }
            } catch (error) {
                console.warn(`⚠️ Timeout en validación de orientación: ${error.message}`);
                
                // Continuar de todos modos después del timeout
                if (onValidationComplete) {
                    onValidationComplete(false);
                }
            }
        } else {
        */
        
        // ✅ NUEVO: Sin validación aquí, solo esperar duración del audio
        // La validación se hace ANTES en analysis.html
        {
            // Sin validación, continuar después de la duración especificada
            this.registerTimeout(() => {
                if (onValidationComplete) {
                    onValidationComplete(true);
                }
            }, (positioningPhase.duration || 4) * 1000);
        }
    }

    /**
     * 🔢 NUEVA: Fase de preparación (countdown 3-2-1)
     * @param {string} segment - shoulder, elbow, hip, knee, ankle, neck
     * @param {string} exercise - flexion, extension, etc.
     */
    async startPreparationPhase(segment, exercise) {
        this.currentPhase = 'preparation';
        
        // Obtener configuración TTS del ejercicio
        const ttsConfig = this.getExerciseTTSConfig(segment, exercise);
        if (!ttsConfig || !ttsConfig.tts_phases?.preparation) {
            console.warn(`⚠️ No hay tts_phases.preparation para ${segment}.${exercise}`);
            return;
        }
        
        const preparationPhases = ttsConfig.tts_phases.preparation;
        
        // Reproducir countdown 3-2-1 secuencialmente
        let cumulativeTime = 0;
        for (const phase of preparationPhases) {
            this.registerTimeout(() => {
                if (!phase.text) return;
                
                // Beep con cada número del countdown
                this.speak(phase.text, { 
                    rate: 0.90, 
                    volume: this.volume + 0.15,
                    pitch: 1.2,
                    playBeep: true,
                    beepType: 'countdown'
                });
            }, cumulativeTime);
            
            cumulativeTime += (phase.duration || 1) * 1000;
        }
        
        console.log(`🔢 Preparation countdown initiated: 3-2-1`);
    }
    
    /**
     * 🏃‍♂️ Iniciar fase de ejercicio usando tts_phases.exercise
     * @param {string} segment - shoulder, elbow, hip, knee, ankle, neck
     * @param {string} exercise - flexion, extension, etc.
     */
    async startExercisePhase(segment, exercise) {
        this.currentPhase = 'exercise';
        
        // Obtener configuración TTS del ejercicio
        const ttsConfig = this.getExerciseTTSConfig(segment, exercise);
        if (!ttsConfig || !ttsConfig.tts_phases?.exercise) {
            console.warn(`⚠️ No hay tts_phases.exercise para ${segment}.${exercise}`);
            return;
        }
        
        const exercisePhases = ttsConfig.tts_phases.exercise;
        
        // Reproducir instrucciones según timing markers
        for (const phase of exercisePhases) {
            const timingMs = this.parseTimingToMs(phase.timing || 'start');
            
            this.registerTimeout(() => {
                if (!phase.text) return;
                
                // Rate adaptativo según longitud del texto
                const wordCount = phase.text.split(' ').length;
                const rate = wordCount > 15 ? 0.70 : 0.80;
                
                this.speak(phase.text, { 
                    rate, 
                    volume: this.volume + 0.05
                });
            }, timingMs);
        }
    }
    
    /**
     * ⏱️ Convertir timing marker a milisegundos
     */
    parseTimingToMs(timing) {
        if (timing === 'start') return 0;
        if (timing === 'pre_calibration') return 0;
        if (typeof timing === 'number') return timing * 1000;
        return 0;
    }
    
    /**
     * 🔔 Reproducir fase de countdown usando tts_phases.countdown
     * @param {string} segment - shoulder, elbow, hip, knee, ankle, neck
     * @param {string} exercise - flexion, extension, etc.
     */
    async speakCountdown(segment, exercise) {
        // Obtener configuración TTS del ejercicio
        const ttsConfig = this.getExerciseTTSConfig(segment, exercise);
        if (!ttsConfig || !ttsConfig.tts_phases?.countdown) {
            console.warn(`⚠️ No hay tts_phases.countdown para ${segment}.${exercise}`);
            return;
        }
        
        const countdownPhases = ttsConfig.tts_phases.countdown;
        
        // Reproducir countdown según timing markers
        for (const phase of countdownPhases) {
            const timingMs = this.parseTimingToMs(phase.timing || 22);
            
            this.registerTimeout(() => {
                if (!phase.text) return;
                
                // Countdown numbers: mayor volumen, pitch y rate
                const isCountdownNumber = ['3', '2', '1'].includes(phase.text);
                const options = isCountdownNumber ? {
                    volume: this.volume + 0.2,
                    rate: 1.2,
                    pitch: 1.3,
                    playBeep: phase.beep === true,
                    beepType: 'countdown'
                } : {
                    volume: this.volume + 0.05,
                    rate: 0.82
                };
                
                this.speak(phase.text, options);
            }, timingMs);
        }
    }
    
    /**
     * ✅ Completar análisis CON BEEP DE ÉXITO
     */
    completeAnalysis() {
        this.currentPhase = 'completed';
        
        const messages = this.getSystemMessages();
        // 🔔 Mensaje de finalización con beep de éxito
        this.speak(messages.completion.success, { 
            rate: 0.80,  // Lento para completar toda la frase
            volume: this.volume + 0.1,
            playBeep: true,
            beepType: 'success'
        });
    }
    
    /**
     * 🔧 Métodos de control público
     */
    toggle() {
        this.enabled = !this.enabled;
        const messages = this.getSystemMessages();
        const message = this.enabled ? messages.system.audio_enabled : messages.system.audio_disabled;
        
        // Si se está desactivando, cancelar todos los timeouts
        if (!this.enabled) {
            this.synth.cancel();
            this.clearAllTimeouts();
        }
        
        // Hablar solo si se está activando
        if (this.enabled) {
            this.registerTimeout(() => this.speak(message), 100);
        }
        
        return this.enabled;
    }
    
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
    }
    
    setLanguage(lang) {
        if (['es', 'en'].includes(lang)) {
            this.language = lang;
            this.selectBestVoice();
            
            const messages = this.getSystemMessages();
            this.speak(messages.system.language_changed);
        }
    }
    
    /**
     * 🛑 Detener audio actual
     */
    stop() {
        this.synth.cancel();
    }
    
    /**
     * 🎙️ NUEVA FUNCIÓN: Reproducir secuencia de instrucciones con pausas
     * @param {Array} sequence - Array de {text, pause_after}
     * @returns {Promise} - Resuelve cuando la secuencia completa termina
     * 
     * Ejemplo de uso:
     * const sequence = [
     *   { text: "Ponte de pie", pause_after: 2.0 },
     *   { text: "Levanta el brazo", pause_after: 1.5 }
     * ];
     * await audioGuide.speakSequence(sequence);
     */
    async speakSequence(sequence) {
        if (!this.enabled || !this.isInitialized) {
            return;
        }
        
        if (!sequence || !Array.isArray(sequence) || sequence.length === 0) {
            console.warn('⚠️ Secuencia vacía o inválida');
            return;
        }
        
        for (let i = 0; i < sequence.length; i++) {
            const instruction = sequence[i];
            
            if (!instruction.text) {
                console.warn(`⚠️ Instrucción ${i+1} sin texto, saltando`);
                continue;
            }
            
            // Hablar línea actual y esperar a que termine
            await this.speakAsync(instruction.text);
            
            // Pausa programática después de hablar
            const pauseTime = instruction.pause_after || 0;
            if (pauseTime > 0) {
                await this.sleep(pauseTime * 1000);
            }
        }
    }
    
    /**
     * 🔊 Versión asíncrona de speak() que espera a que termine
     * @param {string} text - Texto a reproducir
     * @returns {Promise} - Resuelve cuando termina de hablar
     */
    speakAsync(text) {
        return new Promise((resolve) => {
            if (!this.enabled || !this.isInitialized || !text) {
                resolve();
                return;
            }
            
            // Cancelar speech anterior si está hablando
            this.synth.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.voice = this.voice;
            utterance.volume = this.volume;
            utterance.rate = 0.85;
            utterance.pitch = 1.1;
            utterance.lang = this.language === 'es' ? 'es-ES' : 'en-US';
            
            // Resolver cuando termina de hablar
            utterance.onend = () => {
                resolve();
            };
            
            // Manejar errores sin bloquear la secuencia
            utterance.onerror = (event) => {
                console.error(`   ❌ Error TTS: ${event.error}`);
                resolve(); // Resolver igual para no bloquear secuencia
            };
            
            this.synth.speak(utterance);
        });
    }
    
    /**
     * ⏱️ Pausa programática (sleep)
     * @param {number} ms - Milisegundos a esperar
     * @returns {Promise} - Resuelve después del tiempo especificado
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * 📊 Estado del sistema
     */
    getStatus() {
        return {
            enabled: this.enabled,
            volume: this.volume,
            language: this.language,
            isInitialized: this.isInitialized,
            currentPhase: this.currentPhase,
            voiceName: this.voice?.name || 'none'
        };
    }
}

// 🌍 Instancia global
window.audioGuide = new AudioGuideSystem();

// 🎛️ Evento para cuando el sistema esté listo
window.audioGuide.initializeVoices().then(() => {
    // Dispatch evento personalizado
    window.dispatchEvent(new CustomEvent('audioGuideReady', {
        detail: window.audioGuide.getStatus()
    }));
});