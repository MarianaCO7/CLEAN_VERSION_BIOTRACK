/**
 * ============================================================================
 * ESP32 BLUETOOTH CONTROLLER - Web Serial API
 * ============================================================================
 * Controlador para comunicación con ESP32 vía Bluetooth Serial (COM port)
 * Usa Web Serial API (Chrome/Edge only)
 * Comandos de 1 carácter para optimización
 * ============================================================================
 */

class ESP32BluetoothController {
    constructor() {
        this.port = null;
        this.reader = null;
        this.writer = null;
        this.isConnected = false;
        this.statusCallback = null;
        this.messageCallback = null;
        
        // Verificar compatibilidad del navegador
        if (!('serial' in navigator)) {
            console.error('[ESP32] Web Serial API no está disponible');
            console.error('[ESP32] Requiere Chrome/Edge 89+ con flag habilitado');
        }
    }

    /**
     * Verificar si Web Serial API está disponible
     */
    static isSupported() {
        return 'serial' in navigator;
    }

    /**
     * Conectar al ESP32 vía puerto COM Bluetooth
     */
    async connect() {
        try {
            console.log('[ESP32] Solicitando puerto serial...');
            
            // Solicitar puerto al usuario (abre diálogo de selección)
            this.port = await navigator.serial.requestPort({
                filters: [
                    // Filtros para ESP32 Bluetooth
                    { usbVendorId: 0x1a86 }, // CH340
                    { usbVendorId: 0x10c4 }, // CP210x
                    { usbVendorId: 0x0403 }  // FTDI
                ]
            });
            
            console.log('[ESP32] Puerto seleccionado, abriendo conexión...');
            
            // Abrir puerto con configuración para ESP32
            await this.port.open({ 
                baudRate: 115200,
                dataBits: 8,
                stopBits: 1,
                parity: 'none',
                flowControl: 'none'
            });
            
            // Configurar reader y writer
            this.reader = this.port.readable.getReader();
            this.writer = this.port.writable.getWriter();
            
            this.isConnected = true;
            console.log('[ESP32] ✓ Conectado exitosamente');
            
            // Notificar cambio de estado
            if (this.statusCallback) {
                this.statusCallback(true, 'Conectado a BIOMECH-ESP32');
            }
            
            // Iniciar lectura de respuestas
            this.startReading();
            
            // Enviar comando de status para verificar
            await this.sendCommand('S');
            
            return true;
            
        } catch (error) {
            console.error('[ESP32] Error al conectar:', error);
            
            let errorMsg = 'Error de conexión';
            if (error.name === 'NotFoundError') {
                errorMsg = 'No se seleccionó ningún puerto';
            } else if (error.name === 'InvalidStateError') {
                errorMsg = 'Puerto ya está en uso';
            } else if (error.name === 'NetworkError') {
                errorMsg = 'Error de comunicación con el dispositivo';
            }
            
            if (this.statusCallback) {
                this.statusCallback(false, errorMsg);
            }
            
            return false;
        }
    }

    /**
     * Desconectar del ESP32
     */
    async disconnect() {
        try {
            console.log('[ESP32] Cerrando conexión...');
            
            // Cancelar reader
            if (this.reader) {
                await this.reader.cancel();
                this.reader.releaseLock();
                this.reader = null;
            }
            
            // Cerrar writer
            if (this.writer) {
                await this.writer.releaseLock();
                this.writer = null;
            }
            
            // Cerrar puerto
            if (this.port) {
                await this.port.close();
                this.port = null;
            }
            
            this.isConnected = false;
            console.log('[ESP32] ✓ Desconectado');
            
            if (this.statusCallback) {
                this.statusCallback(false, 'Desconectado');
            }
            
            return true;
            
        } catch (error) {
            console.error('[ESP32] Error al desconectar:', error);
            return false;
        }
    }

    /**
     * Enviar comando de 1 carácter al ESP32
     */
    async sendCommand(command) {
        if (!this.isConnected || !this.writer) {
            console.error('[ESP32] No hay conexión activa');
            return false;
        }
        
        try {
            const encoder = new TextEncoder();
            await this.writer.write(encoder.encode(command));
            
            console.log(`[ESP32] Comando enviado: '${command}'`);
            return true;
            
        } catch (error) {
            console.error('[ESP32] Error al enviar comando:', error);
            return false;
        }
    }

    /**
     * Comandos específicos para servos
     */
    async panLeft() {
        return await this.sendCommand('L');
    }

    async panCenter() {
        return await this.sendCommand('C');
    }

    async panRight() {
        return await this.sendCommand('R');
    }

    async getStatus() {
        return await this.sendCommand('S');
    }

    /**
     * Leer respuestas del ESP32 en background
     */
    async startReading() {
        console.log('[ESP32] Iniciando lectura de respuestas...');
        
        const decoder = new TextDecoder();
        let buffer = '';
        
        try {
            while (this.isConnected && this.reader) {
                const { value, done } = await this.reader.read();
                
                if (done) {
                    console.log('[ESP32] Stream cerrado por el dispositivo');
                    break;
                }
                
                // Decodificar y agregar al buffer
                buffer += decoder.decode(value, { stream: true });
                
                // Procesar líneas completas
                let lines = buffer.split('\n');
                buffer = lines.pop(); // Guardar línea incompleta
                
                for (let line of lines) {
                    line = line.trim();
                    if (line) {
                        console.log('[ESP32] <<', line);
                        this.processResponse(line);
                    }
                }
            }
        } catch (error) {
            if (error.name !== 'NetworkError' && error.name !== 'AbortError') {
                console.error('[ESP32] Error al leer:', error);
            }
        }
    }

    /**
     * Procesar respuesta del ESP32
     */
    processResponse(line) {
        // Formato de respuesta: "OK:L:45" o "STATUS:90:90:0.5"
        
        if (line.startsWith('OK:')) {
            const parts = line.split(':');
            const cmd = parts[1];
            const value = parts[2];
            
            if (this.messageCallback) {
                this.messageCallback({
                    type: 'success',
                    command: cmd,
                    value: value,
                    message: `Servo Pan: ${value}°`
                });
            }
        } 
        else if (line.startsWith('STATUS:')) {
            const parts = line.split(':');
            const panAngle = parseInt(parts[1]);
            const nivelAngle = parseInt(parts[2]);
            const gyroValue = parseFloat(parts[3]);
            
            if (this.messageCallback) {
                this.messageCallback({
                    type: 'status',
                    pan: panAngle,
                    nivel: nivelAngle,
                    gyro: gyroValue,
                    message: `Pan: ${panAngle}° | Nivel: ${nivelAngle}° | Gyro: ${gyroValue.toFixed(2)}°`
                });
            }
        }
        else if (line.startsWith('ERROR:')) {
            if (this.messageCallback) {
                this.messageCallback({
                    type: 'error',
                    message: line.replace('ERROR:', '')
                });
            }
        }
    }

    /**
     * Registrar callback para cambios de estado
     */
    onStatusChange(callback) {
        this.statusCallback = callback;
    }

    /**
     * Registrar callback para mensajes del ESP32
     */
    onMessage(callback) {
        this.messageCallback = callback;
    }

    /**
     * Obtener lista de puertos disponibles
     */
    static async getAvailablePorts() {
        if (!ESP32BluetoothController.isSupported()) {
            throw new Error('Web Serial API no está disponible');
        }
        
        return await navigator.serial.getPorts();
    }

    /**
     * Reconectar a último puerto usado
     */
    async reconnectToLastPort() {
        try {
            const ports = await ESP32BluetoothController.getAvailablePorts();
            
            if (ports.length > 0) {
                console.log('[ESP32] Reconectando a último puerto...');
                this.port = ports[0];
                
                await this.port.open({ 
                    baudRate: 115200,
                    dataBits: 8,
                    stopBits: 1,
                    parity: 'none',
                    flowControl: 'none'
                });
                
                this.reader = this.port.readable.getReader();
                this.writer = this.port.writable.getWriter();
                this.isConnected = true;
                
                if (this.statusCallback) {
                    this.statusCallback(true, 'Reconectado');
                }
                
                this.startReading();
                return true;
            }
            
            return false;
            
        } catch (error) {
            console.error('[ESP32] Error al reconectar:', error);
            return false;
        }
    }
}

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ESP32BluetoothController;
}
