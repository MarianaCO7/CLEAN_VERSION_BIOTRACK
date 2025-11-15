/**
 * EXERCISE CONFIG LOADER
 * 
 * Módulo para cargar exercises.json dinámicamente desde el servidor
 * y proporcionar acceso fácil a las configuraciones de ejercicios
 * incluyendo las nuevas secuencias TTS (tts_sequence)
 */

class ExerciseConfigLoader {
    constructor() {
        this.config = null;
        this.isLoaded = false;
        this.loadPromise = null;
    }
    
    /**
     * Cargar configuración desde el servidor
     * @returns {Promise} Promesa que resuelve cuando la configuración está cargada
     */
    async load() {
        // Si ya hay una carga en progreso, retornar esa promesa
        if (this.loadPromise) {
            return this.loadPromise;
        }
        
        // Si ya está cargada, retornar inmediatamente
        if (this.isLoaded) {
            return Promise.resolve(this.config);
        }
        
        // Iniciar carga
        this.loadPromise = this._fetchConfig();
        
        try {
            this.config = await this.loadPromise;
            this.isLoaded = true;
            return this.config;
        } catch (error) {
            console.error('❌ Error cargando configuración de ejercicios:', error);
            this.loadPromise = null; // Permitir reintentar
            throw error;
        }
    }
    
    /**
     * Fetch de la configuración desde el servidor
     * @private
     */
    async _fetchConfig() {
        const response = await fetch('/api/exercises_config');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Error desconocido');
        }
        
        return data.config;
    }
    
    /**
     * Obtener configuración de un ejercicio específico
     * @param {string} segment - Nombre del segmento (ej: 'shoulder', 'elbow')
     * @param {string} exercise - Nombre del ejercicio (ej: 'flexion', 'extension')
     * @returns {Object|null} Configuración del ejercicio o null si no existe
     */
    getExercise(segment, exercise) {
        if (!this.isLoaded) {
            console.warn('⚠️ Config no cargada. Llama a load() primero');
            return null;
        }
        
        try {
            return this.config.segments[segment]?.exercises[exercise] || null;
        } catch (error) {
            console.error(`❌ Error obteniendo ejercicio ${segment}/${exercise}:`, error);
            return null;
        }
    }
    
    /**
     * Obtener secuencia TTS de un ejercicio
     * @param {string} segment - Nombre del segmento
     * @param {string} exercise - Nombre del ejercicio
     * @returns {Array|null} Array de {text, pause_after} o null si no existe
     */
    getTTSSequence(segment, exercise) {
        const exerciseConfig = this.getExercise(segment, exercise);
        return exerciseConfig?.tts_sequence || null;
    }
    
    /**
     * Obtener instrucciones legacy (fallback)
     * @param {string} segment - Nombre del segmento
     * @param {string} exercise - Nombre del ejercicio
     * @returns {Object|null} Objeto con position, movement, warning, tips
     */
    getInstructions(segment, exercise) {
        const exerciseConfig = this.getExercise(segment, exercise);
        return exerciseConfig?.instructions || null;
    }
    
    /**
     * Verificar si un ejercicio tiene secuencia TTS
     * @param {string} segment - Nombre del segmento
     * @param {string} exercise - Nombre del ejercicio
     * @returns {boolean} true si tiene tts_sequence
     */
    hasTTSSequence(segment, exercise) {
        const exerciseConfig = this.getExercise(segment, exercise);
        return Array.isArray(exerciseConfig?.tts_sequence) && 
               exerciseConfig.tts_sequence.length > 0;
    }
    
    /**
     * Obtener lista de todos los segmentos disponibles
     * @returns {Array<string>} Array de nombres de segmentos
     */
    getSegments() {
        if (!this.isLoaded) return [];
        return Object.keys(this.config.segments || {});
    }
    
    /**
     * Obtener lista de ejercicios de un segmento
     * @param {string} segment - Nombre del segmento
     * @returns {Array<string>} Array de nombres de ejercicios
     */
    getExercises(segment) {
        if (!this.isLoaded) return [];
        return Object.keys(this.config.segments[segment]?.exercises || {});
    }
    
    /**
     * Estado de carga
     * @returns {Object} Estado actual del loader
     */
    getStatus() {
        return {
            isLoaded: this.isLoaded,
            isLoading: this.loadPromise !== null && !this.isLoaded,
            segmentsCount: this.isLoaded ? this.getSegments().length : 0
        };
    }
}

// Instancia global
window.exerciseConfigLoader = new ExerciseConfigLoader();

// Auto-cargar al cargar la página (sin bloquear)
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await window.exerciseConfigLoader.load();
        
        // Dispatch evento para notificar que está listo
        window.dispatchEvent(new CustomEvent('exerciseConfigLoaded', {
            detail: window.exerciseConfigLoader.config
        }));
    } catch (error) {
        console.error('❌ Error auto-cargando configuración:', error);
    }
});
