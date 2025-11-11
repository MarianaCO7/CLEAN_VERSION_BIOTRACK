/**
 * SERVO CONTROL SYSTEM
 * Control de servomotores MG995 via ESP32 WiFi
 * Integración con análisis biomecánico
 */

class ServoControlSystem {
    constructor() {
        this.esp32IP = null;
        this.connectionStatus = 'disconnected';
        this.currentTilt = 0;
        this.currentPan = 0;
        this.autoLevelEnabled = true;
        this.moveInterval = null;
        this.statusInterval = null;
        
        // Configuraciones guardadas
        this.savedConfigs = JSON.parse(localStorage.getItem('servoConfigs') || '[]');
        
        this.init();
    }
    
    init() {
        console.log('🎛️ Inicializando Sistema de Control Servo');
        this.detectESP32();
        this.loadSavedConfigs();
        this.startStatusUpdates();
    }
    
    // === DETECCION Y CONEXION ESP32 ===
    async detectESP32() {
        console.log('Detectando ESP32...');
        this.updateConnectionStatus('connecting');
        
        // 1. Intentar IP guardada primero
        const savedIP = localStorage.getItem('esp32IP');
        if (savedIP) {
            console.log('Intentando IP guardada: ' + savedIP);
            if (await this.tryConnectToIP(savedIP)) {
                return;
            }
        }
        
        // 2. Lista de IPs comunes para ESP32
        const possibleIPs = [
            '192.168.0.10',     // Red Ruphay (tu ESP32)
            '192.168.1.100',    // IP estatica comun
            '192.168.1.101', 
            '192.168.4.1',      // AP mode (BIOMECH-SETUP)
            '192.168.0.100',
            '10.0.0.100'
        ];
        
        for (const ip of possibleIPs) {
            if (await this.tryConnectToIP(ip)) {
                return;
            }
        }
        
        // No se encontro ESP32
        this.esp32IP = null;
        this.connectionStatus = 'disconnected';
        this.updateConnectionStatus('disconnected');
        console.warn('ESP32 no encontrado en ninguna IP conocida');
        
        // Mostrar opcion de ingreso manual
        this.showManualIPInput();
    }
    
    async tryConnectToIP(ip) {
        try {
            console.log('Probando IP: ' + ip);
            const response = await fetch('http://' + ip + '/api/status', {
                method: 'GET',
                signal: AbortSignal.timeout(2000)  // 2 segundos timeout
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Verificar que es nuestro dispositivo biomecanico
                if (data.device === 'biomech-servo-control') {
                    this.esp32IP = ip;
                    this.connectionStatus = 'connected';
                    this.updateConnectionStatus('connected', data);
                    console.log('ESP32 encontrado en: ' + ip);
                    console.log('Estado:', data);
                    
                    // Guardar IP para proximas veces
                    localStorage.setItem('esp32IP', ip);
                    
                    // Actualizar estado inicial
                    this.currentTilt = data.current_tilt || 0;
                    this.currentPan = data.current_pan || 0;
                    this.updateUI();
                    
                    return true;
                }
            }
        } catch (error) {
            console.log('Sin respuesta en ' + ip);
        }
        return false;
    }
    
    showManualIPInput() {
        // Agregar campo de entrada manual si no existe
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement && !document.getElementById('manualIPInput')) {
            const inputHTML = '<div style="margin-top: 10px;">' +
                '<input type="text" id="manualIPInput" placeholder="Ej: 192.168.1.150" ' +
                'style="padding: 5px; width: 150px; border: 1px solid #ccc; border-radius: 3px;">' +
                '<button onclick="window.servoControl.connectManualIP()" ' +
                'style="padding: 5px 10px; margin-left: 5px; background: #2196F3; color: white; border: none; border-radius: 3px; cursor: pointer;">' +
                'Conectar</button>' +
                '</div>';
            statusElement.insertAdjacentHTML('afterend', inputHTML);
        }
    }
    
    async connectManualIP() {
        const input = document.getElementById('manualIPInput');
        if (!input) return;
        
        const ip = input.value.trim();
        if (!ip) {
            alert('Ingrese una IP valida');
            return;
        }
        
        console.log('Intentando conexion manual a: ' + ip);
        if (await this.tryConnectToIP(ip)) {
            // Remover input si conexion exitosa
            input.parentElement.remove();
        } else {
            alert('No se pudo conectar a ' + ip + '\nVerifique:\n1. ESP32 encendido\n2. Misma red WiFi\n3. IP correcta');
        }
    }
    
    updateConnectionStatus(status) {
        this.connectionStatus = status;
        const statusElement = document.getElementById('connectionStatus');
        
        if (statusElement) {
            statusElement.className = `badge ${status}`;
            
            switch(status) {
                case 'connected':
                    statusElement.textContent = '✅ Conectado';
                    statusElement.style.backgroundColor = '#28a745';
                    break;
                case 'connecting':
                    statusElement.textContent = '🔄 Conectando...';
                    statusElement.style.backgroundColor = '#ffc107';
                    statusElement.style.color = '#000';
                    break;
                case 'disconnected':
                    statusElement.textContent = '❌ Desconectado (Modo Demo)';
                    statusElement.style.backgroundColor = '#dc3545';
                    break;
            }
        }
    }
    
    // === SINCRONIZACIÓN CON ESP32 ===
    async syncWithESP32() {
        if (!this.esp32IP) return;
        
        try {
            const response = await fetch(`http://${this.esp32IP}/api/servo/status`);
            const data = await response.json();
            
            this.currentTilt = data.tilt || 0;
            this.currentPan = data.pan || 0;
            
            this.updateUI();
        } catch (error) {
            console.error('❌ Error sincronizando con ESP32:', error);
        }
    }
    
    // === CONTROL DE SERVOS ===
    async moveServo(type, direction) {
        console.log(`🎛️ Moviendo servo ${type} hacia ${direction}`);
        
        if (this.esp32IP) {
            try {
                await fetch(`http://${this.esp32IP}/api/servo/move`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        servo: type,
                        direction: direction,
                        continuous: true
                    })
                });
            } catch (error) {
                console.error('❌ Error moviendo servo:', error);
            }
        } else {
            // Modo simulación
            this.simulateServoMovement(type, direction);
        }
    }
    
    async stopServo(type) {
        console.log(`🛑 Deteniendo servo ${type}`);
        
        if (this.esp32IP) {
            try {
                await fetch(`http://${this.esp32IP}/api/servo/stop`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({servo: type})
                });
            } catch (error) {
                console.error('❌ Error deteniendo servo:', error);
            }
        }
        
        // Actualizar posición actual
        await this.syncWithESP32();
    }
    
    async setPanPosition(angle) {
        console.log(`🎯 Estableciendo paneo a ${angle}°`);
        
        // Limitar rango (-90 a +90)
        angle = Math.max(-90, Math.min(90, angle));
        
        if (this.esp32IP) {
            try {
                // ⚡ MÉTODO OPTIMIZADO: Usar comando simple (3x más rápido)
                let command = 'C';  // Default: centro
                if (angle === -45) command = 'L';      // Left
                else if (angle === 0) command = 'C';   // Center
                else if (angle === 45) command = 'R';  // Right
                
                // Para ángulos exactos (-45, 0, 45) usar endpoint optimizado
                if (angle === -45 || angle === 0 || angle === 45) {
                    const response = await fetch(`http://${this.esp32IP}/c?c=${command}`, {
                        method: 'GET'
                    });
                    
                    if (response.ok) {
                        console.log(`✅ Comando optimizado enviado: ${command} (${angle}°)`);
                        this.currentPan = angle;
                    } else {
                        throw new Error('Comando simple falló, usando método tradicional');
                    }
                } else {
                    // Para ángulos personalizados, usar API JSON tradicional
                    const response = await fetch(`http://${this.esp32IP}/api/servo/pan`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({angle: angle})
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        console.log('✅ Posición pan actualizada (JSON):', result);
                        this.currentPan = angle;
                    } else {
                        console.error('❌ Error en respuesta ESP32:', response.status);
                    }
                }
            } catch (error) {
                console.error('❌ Error estableciendo posición pan:', error);
            }
        } else {
            console.warn('⚠️ ESP32 no conectado - simulando cambio local');
            this.currentPan = angle;
        }
        
        // Actualizar UI inmediatamente
        this.updateUI();
    }
    
    async centerPan() {
        await this.setPanPosition(0);
    }
    
    // === NIVELACIÓN AUTOMÁTICA ===
    toggleAutoLevel() {
        this.autoLevelEnabled = document.getElementById('autoLevelSwitch').checked;
        console.log(`🎚️ Nivelación automática: ${this.autoLevelEnabled ? 'ON' : 'OFF'}`);
        
        const manualControls = document.getElementById('manualTiltControls');
        if (manualControls) {
            manualControls.style.display = this.autoLevelEnabled ? 'none' : 'block';
        }
        
        if (this.esp32IP) {
            fetch(`http://${this.esp32IP}/api/auto-level`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled: this.autoLevelEnabled})
            }).catch(error => console.error('❌ Error configurando auto-level:', error));
        }
    }
    
    // === CONFIGURACIONES GUARDADAS ===
    saveCurrentConfig() {
        const configName = prompt('Nombre para esta configuración:');
        if (!configName) return;
        
        const config = {
            id: Date.now(),
            name: configName,
            joint: window.currentJointType || 'general',
            tilt: this.currentTilt,
            pan: this.currentPan,
            autoLevel: this.autoLevelEnabled,
            timestamp: new Date().toISOString()
        };
        
        this.savedConfigs.push(config);
        localStorage.setItem('servoConfigs', JSON.stringify(this.savedConfigs));
        
        this.loadSavedConfigs();
        
        console.log('💾 Configuración guardada:', config);
    }
    
    async loadConfig(configId) {
        const config = this.savedConfigs.find(c => c.id === configId);
        if (!config) return;
        
        console.log('📂 Cargando configuración:', config);
        
        await this.setPanPosition(config.pan);
        
        document.getElementById('autoLevelSwitch').checked = config.autoLevel;
        this.toggleAutoLevel();
        
        if (!config.autoLevel && this.esp32IP) {
            // Establecer inclinación manual
            try {
                await fetch(`http://${this.esp32IP}/api/servo/position`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        servo: 'tilt',
                        angle: config.tilt
                    })
                });
            } catch (error) {
                console.error('❌ Error cargando inclinación:', error);
            }
        }
        
        this.updateUI();
    }
    
    deleteConfig(configId) {
        if (!confirm('¿Eliminar esta configuración?')) return;
        
        this.savedConfigs = this.savedConfigs.filter(c => c.id !== configId);
        localStorage.setItem('servoConfigs', JSON.stringify(this.savedConfigs));
        this.loadSavedConfigs();
    }
    
    loadSavedConfigs() {
        const container = document.getElementById('savedConfigs');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.savedConfigs.forEach(config => {
            const configElement = document.createElement('div');
            configElement.className = 'col-md-4';
            configElement.innerHTML = `
                <div class="saved-config-card">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="text-light mb-0">${config.name}</h6>
                        <button type="button" class="btn btn-outline-danger btn-sm" 
                                onclick="servoControl.deleteConfig(${config.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <small class="text-muted d-block mb-2">
                        ${config.joint} • Pan: ${config.pan}° • ${config.autoLevel ? 'Auto' : 'Manual'}
                    </small>
                    <button type="button" class="btn btn-outline-success btn-sm w-100" 
                            onclick="servoControl.loadConfig(${config.id})">
                        <i class="bi bi-play"></i> Cargar
                    </button>
                </div>
            `;
            container.appendChild(configElement);
        });
        
        if (this.savedConfigs.length === 0) {
            container.innerHTML = '<div class="col-12"><p class="text-muted text-center">No hay configuraciones guardadas</p></div>';
        }
    }
    
    // === RESETEAR A VALORES POR DEFECTO ===
    async resetToDefaults() {
        console.log('🔄 Reseteando a valores por defecto');
        
        await this.setPanPosition(0);
        
        document.getElementById('autoLevelSwitch').checked = true;
        this.toggleAutoLevel();
        
        if (this.esp32IP) {
            try {
                await fetch(`http://${this.esp32IP}/api/reset`, {method: 'POST'});
            } catch (error) {
                console.error('❌ Error reseteando ESP32:', error);
            }
        }
        
        this.updateUI();
    }
    
    // === SIMULACIÓN (SIN HARDWARE) ===
    simulateServoMovement(type, direction) {
        if (type === 'pan') {
            const increment = direction === 'left' ? -2 : 2;
            this.currentPan = Math.max(-90, Math.min(90, this.currentPan + increment));
        } else if (type === 'tilt') {
            const increment = direction === 'up' ? 1 : -1;
            this.currentTilt = Math.max(-30, Math.min(30, this.currentTilt + increment));
        }
        
        this.updateUI();
    }
    
    // === ACTUALIZACIÓN DE UI ===
    updateUI() {
        // Actualizar posición de paneo
        const panElement = document.getElementById('currentPan');
        if (panElement) {
            panElement.textContent = `${this.currentPan}° ${this.currentPan === 0 ? '(Centro)' : ''}`;
        }
        
        // 🎛️ ACTUALIZAR SLIDER SINCRONIZADO
        const panSlider = document.getElementById('panSlider');
        if (panSlider && panSlider.value != this.currentPan) {
            panSlider.value = this.currentPan;
        }
        
        // Actualizar marcador visual
        const panMarker = document.getElementById('panMarker');
        if (panMarker) {
            const percentage = ((this.currentPan + 90) / 180) * 100;
            panMarker.style.left = `${percentage}%`;
        }
        
        // Actualizar inclinación
        const tiltElement = document.getElementById('currentTilt');
        if (tiltElement) {
            tiltElement.textContent = `${this.currentTilt.toFixed(1)}°`;
        }
        
        // Actualizar barra de inclinación
        const tiltBar = document.getElementById('tiltBar');
        if (tiltBar) {
            const percentage = ((this.currentTilt + 30) / 60) * 100;
            tiltBar.style.width = `${percentage}%`;
        }
    }
    
    // === MONITOREO DE ESTADO ===
    startStatusUpdates() {
        this.statusInterval = setInterval(async () => {
            if (this.esp32IP && this.connectionStatus === 'connected') {
                try {
                    const response = await fetch(`http://${this.esp32IP}/api/status`);
                    const data = await response.json();
                    
                    this.currentTilt = data.tilt || this.currentTilt;
                    this.currentPan = data.pan || this.currentPan;
                    
                    this.updateUI();
                } catch (error) {
                    console.warn('⚠️ Perdida conexión con ESP32');
                    this.updateConnectionStatus('disconnected');
                }
            }
        }, 2000);
    }
    
    // === LIMPIEZA ===
    cleanup() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
        }
        if (this.moveInterval) {
            clearInterval(this.moveInterval);
        }
    }
}

// === EXPORTAR AL SCOPE GLOBAL ===
window.ServoControlSystem = ServoControlSystem;

// === FUNCIONES GLOBALES ===
// IMPORTANTE: Exponer servoControl a window para acceso desde HTML inline
let servoControl = null;

function initServoControl() {
    if (!servoControl) {
        servoControl = new ServoControlSystem();
        window.servoControl = servoControl; // EXPONER GLOBALMENTE
    }
    return servoControl;
}

function openServoControl(jointType) {
    console.log(`🎛️ Abriendo control servo para: ${jointType}`);
    
    // Guardar contexto actual
    window.currentJointType = jointType;
    
    // Inicializar sistema si no existe
    initServoControl();
    
    // Calcular altura recomendada
    const userHeight = parseInt(window.userHeight || 170); // Default si no está disponible
    const recommendedHeight = calculateRecommendedHeight(jointType, userHeight);
    
    // Actualizar modal
    const heightElement = document.getElementById('recommendedHeight');
    if (heightElement) {
        heightElement.textContent = `${recommendedHeight} cm`;
    }
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('servoControlModal'));
    modal.show();
}

function closeServoControl() {
    console.log('🔒 Cerrando control servo');
    
    // Guardar configuración actual
    if (servoControl) {
        const currentConfig = {
            tilt: servoControl.currentTilt,
            pan: servoControl.currentPan,
            autoLevel: servoControl.autoLevelEnabled
        };
        
        localStorage.setItem('lastServoConfig', JSON.stringify(currentConfig));
    }
    
    // El análisis puede continuar normalmente
}

// === EXPORTAR FUNCIONES AL SCOPE GLOBAL ===
window.openServoControl = openServoControl;
window.closeServoControl = closeServoControl;
window.initServoControl = initServoControl;

// === FÓRMULAS BIOMECÁNICAS ===
function calculateRecommendedHeight(jointType, userHeight) {
    const ratios = {
        'shoulder': 0.818,  // Altura del hombro
        'elbow': 0.630,     // Altura del codo
        'hip': 0.530,       // Altura de la cadera  
        'knee': 0.285,      // Altura de la rodilla
        'ankle': 0.039,     // Altura del tobillo
        'neck': 0.900       // Estimado para base del cuello
    };
    
    const ratio = ratios[jointType] || 0.500; // Default al 50% si no se encuentra
    const height = Math.round(userHeight * ratio);
    
    console.log(`📐 Altura calculada para ${jointType}: ${height}cm (${userHeight}cm × ${ratio})`);
    
    return height;
}

// === FUNCIONES DE CONTROL ESPECÍFICAS ===
function moveServo(type, direction) {
    if (servoControl) {
        servoControl.moveServo(type, direction);
    }
}

function stopServo(type) {
    if (servoControl) {
        servoControl.stopServo(type);
    }
}

function setPanPosition(angle) {
    if (servoControl) {
        servoControl.setPanPosition(angle);
    }
}

function centerPan() {
    if (servoControl) {
        servoControl.centerPan();
    }
}

function toggleAutoLevel() {
    if (servoControl) {
        servoControl.toggleAutoLevel();
    }
}

function saveCurrentConfig() {
    if (servoControl) {
        servoControl.saveCurrentConfig();
    }
}

function resetToDefaults() {
    if (servoControl) {
        servoControl.resetToDefaults();
    }
}

function reconnectESP32() {
    if (servoControl) {
        servoControl.reconnectESP32();
    }
}

// === LIMPIEZA AL SALIR ===
window.addEventListener('beforeunload', () => {
    if (servoControl) {
        servoControl.cleanup();
    }
});

console.log('🎛️ Sistema de Control Servo cargado');

// Agregar estilos CSS adicionales
const additionalStyles = `
<style>
.saved-config-card {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}

.saved-config-card:hover {
    border-color: var(--biomech-cyan);
    background: rgba(0, 212, 255, 0.1);
}

// =============================================================================
// 🎛️ EVENT LISTENERS PARA SLIDER CONTROL
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Listener para slider de paneo
    const panSlider = document.getElementById('panSlider');
    if (panSlider) {
        let sliderTimeout = null;
        
        panSlider.addEventListener('input', function() {
            const targetAngle = parseInt(this.value);
            
            // Actualizar UI inmediatamente para responsividad
            const panElement = document.getElementById('currentPan');
            if (panElement) {
                const centerText = targetAngle === 0 ? ' (Centro)' : '';
                panElement.textContent = targetAngle + 'deg' + centerText;
            }
            
            // Debounce para evitar spam de requests
            clearTimeout(sliderTimeout);
            sliderTimeout = setTimeout(() => {
                if (window.servoControl && window.servoControl.connectionStatus === 'connected') {
                    window.servoControl.setPosition('pan', targetAngle);
                    console.log('Slider: Pan ajustado a ' + targetAngle + 'deg');
                } else {
                    console.log('ESP32 no conectado - simulando posicion');
                    if (window.servoControl) {
                        window.servoControl.currentPan = targetAngle;
                        window.servoControl.updateUI();
                    }
                }
            }, 150); // 150ms debounce para suavidad
        });
        
        console.log('🎛️ Slider control inicializado');
    }
});
</style>
`;

if (document.head) {
    document.head.insertAdjacentHTML('beforeend', additionalStyles);
}

// =============================================================================
// 🌐 FUNCIONES DE CONFIGURACIÓN WiFi (NUEVAS)
// =============================================================================

function toggleWiFiConfig() {
    const panel = document.getElementById('wifiConfigPanel');
    const btn = document.getElementById('wifiConfigBtn');
    
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        btn.innerHTML = '<i class="bi bi-x"></i> Cerrar';
        
        // Cargar redes al abrir
        scanWiFiNetworks();
    } else {
        panel.style.display = 'none';
        btn.innerHTML = '<i class="bi bi-gear"></i> Config';
    }
}

async function scanWiFiNetworks() {
    const select = document.getElementById('availableNetworks');
    select.innerHTML = '<option value="">Escaneando...</option>';
    
    if (!window.servoSystem || !window.servoSystem.esp32IP) {
        select.innerHTML = '<option value="">ESP32 no conectado</option>';
        return;
    }
    
    try {
        const response = await fetch(`http://${window.servoSystem.esp32IP}/api/wifi/scan`);
        
        if (response.ok) {
            const data = await response.json();
            select.innerHTML = '<option value="">Seleccionar red...</option>';
            
            data.networks.forEach(network => {
                const option = document.createElement('option');
                option.value = network.ssid;
                option.textContent = `${network.ssid} (${network.rssi} dBm)`;
                select.appendChild(option);
            });
            
            console.log(`📡 ${data.count} redes WiFi encontradas`);
        } else {
            select.innerHTML = '<option value="">Error escaneando</option>';
        }
    } catch (error) {
        console.error('❌ Error escaneando WiFi:', error);
        select.innerHTML = '<option value="">Error de conexión</option>';
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('wifiPassword');
    const toggleIcon = document.getElementById('passwordToggleIcon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.className = 'bi bi-eye-slash';
    } else {
        passwordInput.type = 'password';
        toggleIcon.className = 'bi bi-eye';
    }
}

async function saveWiFiConfig() {
    const selectedNetwork = document.getElementById('availableNetworks').value;
    const manualSSID = document.getElementById('manualSSID').value;
    const password = document.getElementById('wifiPassword').value;
    
    const ssid = selectedNetwork || manualSSID;
    
    if (!ssid) {
        alert('Por favor seleccione una red o escriba el SSID manualmente');
        return;
    }
    
    if (!window.servoSystem || !window.servoSystem.esp32IP) {
        alert('ESP32 no conectado. No se puede configurar WiFi.');
        return;
    }
    
    try {
        console.log(`🔧 Configurando WiFi: ${ssid}`);
        
        const response = await fetch(`http://${window.servoSystem.esp32IP}/api/wifi/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ssid: ssid,
                password: password
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Configuración WiFi enviada:', result);
            
            alert('Configuración enviada. El ESP32 se reiniciará y se conectará a la nueva red.\n\nPuede tardar hasta 30 segundos.');
            
            // Cerrar panel
            toggleWiFiConfig();
            
            // Intentar reconectar después de un tiempo
            setTimeout(() => {
                console.log('🔄 Intentando reconectar después de configuración WiFi...');
                window.servoSystem.detectESP32();
            }, 15000);
            
        } else {
            alert('Error enviando configuración al ESP32');
        }
    } catch (error) {
        console.error('❌ Error configurando WiFi:', error);
        alert('Error de conexión con ESP32');
    }
}