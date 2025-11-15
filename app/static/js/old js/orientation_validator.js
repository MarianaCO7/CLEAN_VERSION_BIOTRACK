/**
 * 🧭 SISTEMA DE VALIDACIÓN DE ORIENTACIÓN
 * 
 * Detecta si el usuario está en la orientación correcta (sagital o frontal)
 * antes de iniciar el análisis biomecánico
 * 
 * Basado en landmarks de MediaPipe Pose para determinar:
 * - Sagital: Usuario de perfil (hombros alineados en profundidad Z)
 * - Frontal: Usuario de frente (hombros alineados horizontalmente)
 */

class OrientationValidator {
    constructor() {
        this.currentOrientation = null; // 'sagital' | 'frontal' | 'unknown'
        this.isValidating = false;
        this.validationCallbacks = [];
        
        // Umbrales de detección
        this.thresholds = {
            sagital: {
                shoulder_z_diff: 0.05,  // Diferencia Z entre hombros debe ser > 0.05
                shoulder_x_diff: 0.15   // Diferencia X entre hombros debe ser < 0.15
            },
            frontal: {
                shoulder_z_diff: 0.03,  // Diferencia Z entre hombros debe ser < 0.03
                shoulder_x_diff: 0.10   // Diferencia X entre hombros debe ser > 0.10
            }
        };
        
        console.log('🧭 OrientationValidator initialized');
    }

    /**
     * 🔍 Detectar orientación actual del usuario basada en landmarks
     * @param {Array} landmarks - Array de landmarks de MediaPipe Pose
     * @returns {string} 'sagital' | 'frontal' | 'unknown'
     */
    detectOrientation(landmarks) {
        if (!landmarks || landmarks.length < 33) {
            return 'unknown';
        }

        // Extraer hombros (landmarks 11 y 12)
        const leftShoulder = landmarks[11];   // LEFT_SHOULDER
        const rightShoulder = landmarks[12];  // RIGHT_SHOULDER

        if (!leftShoulder || !rightShoulder) {
            return 'unknown';
        }

        // Calcular diferencias
        const shoulderZDiff = Math.abs(leftShoulder.z - rightShoulder.z);
        const shoulderXDiff = Math.abs(leftShoulder.x - rightShoulder.x);

        // 📐 DETECCIÓN SAGITAL (de perfil)
        // - Los hombros están alineados en profundidad (uno detrás del otro)
        // - Poca diferencia horizontal
        const isSagital = (
            shoulderZDiff > this.thresholds.sagital.shoulder_z_diff &&
            shoulderXDiff < this.thresholds.sagital.shoulder_x_diff
        );

        // 📐 DETECCIÓN FRONTAL (de frente)
        // - Los hombros están alineados horizontalmente
        // - Poca diferencia en profundidad
        const isFrontal = (
            shoulderZDiff < this.thresholds.frontal.shoulder_z_diff &&
            shoulderXDiff > this.thresholds.frontal.shoulder_x_diff
        );

        if (isSagital) {
            this.currentOrientation = 'sagital';
            return 'sagital';
        } else if (isFrontal) {
            this.currentOrientation = 'frontal';
            return 'frontal';
        } else {
            this.currentOrientation = 'unknown';
            return 'unknown';
        }
    }

    /**
     * ⏳ Esperar a que el usuario esté en la orientación correcta
     * @param {string} requiredOrientation - 'sagital' o 'frontal'
     * @param {number} timeoutMs - Tiempo máximo de espera en milisegundos
     * @returns {Promise} Resuelve cuando se detecta la orientación correcta
     */
    async waitForCorrectOrientation(requiredOrientation, timeoutMs = 5000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            this.isValidating = true;

            console.log(`🔍 Esperando orientación: ${requiredOrientation} (timeout: ${timeoutMs}ms)`);

            const checkInterval = setInterval(() => {
                const elapsed = Date.now() - startTime;

                // Timeout alcanzado
                if (elapsed >= timeoutMs) {
                    clearInterval(checkInterval);
                    this.isValidating = false;
                    
                    console.warn(`⏰ Timeout: No se detectó orientación ${requiredOrientation}`);
                    reject(new Error(`Orientation validation timeout after ${timeoutMs}ms`));
                    return;
                }

                // Verificar orientación actual
                if (this.currentOrientation === requiredOrientation) {
                    clearInterval(checkInterval);
                    this.isValidating = false;
                    
                    console.log(`✅ Orientación ${requiredOrientation} detectada en ${elapsed}ms`);
                    resolve(true);
                }
            }, 100); // Verificar cada 100ms
        });
    }

    /**
     * 📊 Actualizar orientación desde landmarks externos
     * Llamado por el sistema de análisis cuando detecta nuevos landmarks
     * @param {Array} landmarks - Landmarks de MediaPipe Pose
     */
    updateFromLandmarks(landmarks) {
        const orientation = this.detectOrientation(landmarks);
        
        // Solo log si cambió la orientación
        if (orientation !== this.currentOrientation) {
            console.log(`🧭 Orientación detectada: ${orientation}`);
        }
    }

    /**
     * 🎨 Mostrar feedback visual en pantalla (opcional)
     * @param {string} requiredOrientation - Orientación requerida
     * @param {HTMLElement} container - Elemento donde mostrar el feedback
     */
    showVisualFeedback(requiredOrientation, container) {
        if (!container) return;

        const isCorrect = this.currentOrientation === requiredOrientation;
        const icon = isCorrect ? '✅' : '⚠️';
        const status = isCorrect ? 'CORRECTO' : 'Ajusta tu posición';
        const colorClass = isCorrect ? 'text-success' : 'text-warning';

        const feedbackHTML = `
            <div class="orientation-feedback ${colorClass}">
                <span class="feedback-icon">${icon}</span>
                <span class="feedback-text">
                    ${status}: ${this.getOrientationLabel(requiredOrientation)}
                </span>
            </div>
        `;

        container.innerHTML = feedbackHTML;
    }

    /**
     * 🏷️ Obtener etiqueta legible de orientación
     * @param {string} orientation - 'sagital' o 'frontal'
     * @returns {string} Etiqueta en español
     */
    getOrientationLabel(orientation) {
        const labels = {
            'sagital': 'De perfil a la cámara',
            'frontal': 'De frente a la cámara',
            'unknown': 'Posición desconocida'
        };
        return labels[orientation] || orientation;
    }

    /**
     * 🔄 Resetear estado del validador
     */
    reset() {
        this.currentOrientation = null;
        this.isValidating = false;
        console.log('🔄 OrientationValidator reset');
    }
}

// 🌐 Crear instancia global
window.orientationValidator = new OrientationValidator();
console.log('✅ OrientationValidator disponible globalmente');
