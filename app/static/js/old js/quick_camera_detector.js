/**
 * 🎯 DETECTOR RÁPIDO PARA PLAN 1.5 - CORREGIDO
 * ✅ SOLO detecta y mapea camera_id para Python
 */

class QuickCameraDetector {
    constructor() {
        this.detectedCameras = [];
        this.selectedCameraId = null;
    }
    
    async detectBestCameraId() {
        try {
            // ✅ SOLICITAR permisos básicos
            await navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    stream.getTracks().forEach(track => track.stop());
                });
            
            // ✅ ENUMERAR dispositivos disponibles
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(d => d.kind === 'videoinput');
            
            if (videoDevices.length === 0) {
                throw new Error('No hay cámaras disponibles');
            }
            
            // 🎯 MAPEO REAL JAVASCRIPT → PYTHON OPENCV
            let priorityMappings = [];
            let regularMappings = [];
            
            // 🧪 PROBAR CADA CÁMARA Y MAPEAR A ÍNDICE REAL
            for (let jsIndex = 0; jsIndex < videoDevices.length; jsIndex++) {
                const device = videoDevices[jsIndex];
                const label = (device.label || '').toLowerCase();
                
                if (device.deviceId) {
                    const works = await this.quickTestCamera(device.deviceId);
                    
                    if (works) {
                        // 🎯 DETECCIÓN REAL CAMO - MAPEO INTELIGENTE
                        let pythonIndex = jsIndex; // Fallback por defecto
                        
                        // 🥇 CAMO TIENE PRIORIDAD ABSOLUTA - FORZAR SELECCIÓN
                        if (label.includes('camo')) {
                            // 🧪 EXPERIMENTAR con índices comunes de Camo
                            const camoCommonIndices = [1, 2, 0, 3]; // Orden típico de Camo
                            
                            for (let testIndex of camoCommonIndices) {
                                // Test rápido: crear VideoCapture temporal para verificar
                                try {
                                    const testStream = await navigator.mediaDevices.getUserMedia({
                                        video: { 
                                            deviceId: { exact: device.deviceId },
                                            width: { ideal: 1280 }, // Camo típicamente alta res
                                            height: { ideal: 720 }
                                        }
                                    });
                                    
                                    const track = testStream.getVideoTracks()[0];
                                    const settings = track.getSettings();
                                    track.stop();
                                    testStream.getTracks().forEach(t => t.stop());
                                    
                                    // Si resolución alta, probablemente es el índice correcto
                                    if (settings.width >= 1280) {
                                        pythonIndex = testIndex;
                                        break;
                                    }
                                    
                                } catch (testError) {
                                    // Continuar con siguiente índice
                                }
                            }
                        }
                        
                        const mapping = {
                            jsIndex: jsIndex,
                            pythonIndex: pythonIndex,
                            device: device,
                            label: device.label || `Cámara ${jsIndex}`,
                            priority: this.getCameraPriority(label)
                        };
                        
                        // 📱 SEPARAR por prioridad
                        if (mapping.priority === 'HIGH') {
                            priorityMappings.push(mapping);
                        } else {
                            regularMappings.push(mapping);
                        }
                    }
                }
            }
            
            // ✅ SELECCIONAR mejor cámara por prioridad
            const testOrder = [...priorityMappings, ...regularMappings];
            
            if (testOrder.length > 0) {
                const bestMapping = testOrder[0];
                const result = {
                    success: true,
                    pythonCameraId: bestMapping.pythonIndex,
                    jsDeviceId: bestMapping.device.deviceId,
                    label: bestMapping.label,
                    deviceType: bestMapping.priority === 'HIGH' ? 'mobile' : 'standard'
                };
                
                return result;
            }
            
            // ✅ FALLBACK
            console.warn('⚠️ Ninguna cámara ideal, usando primera disponible');
            return {
                success: true,
                pythonCameraId: 0,
                jsDeviceId: videoDevices[0].deviceId,
                label: videoDevices[0].label || 'Cámara predeterminada',
                deviceType: 'fallback'
            };
            
        } catch (error) {
            console.error('❌ Error en detección rápida:', error);
            
            return {
                success: false,
                pythonCameraId: 0,
                jsDeviceId: null,
                label: 'Fallback a Python',
                deviceType: 'error',
                error: error.message
            };
        }
    }
    
    async quickTestCamera(deviceId) {
        // ✅ FIXED: Usar comentarios JavaScript, no docstrings Python
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    deviceId: { exact: deviceId },
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            });
            
            stream.getTracks().forEach(track => track.stop());
            return true;
            
        } catch (error) {
            console.log(`⚠️ Cámara ${deviceId} no funciona:`, error.message);
            return false;
        }
    }
    
    detectDeviceType(label, index) {
        // ✅ FIXED: Comentario normal JavaScript
        const lowerLabel = label.toLowerCase();
        
        if (lowerLabel.includes('logitech') || lowerLabel.includes('microsoft') || 
            lowerLabel.includes('creative') || lowerLabel.includes('razer')) {
            return 'external_usb';
        }
        
        if (lowerLabel.includes('android') || lowerLabel.includes('droidcam') || 
            lowerLabel.includes('epoccam') || lowerLabel.includes('camo')) {
            return 'mobile_app';
        }
        
        if (lowerLabel.includes('integrated') || lowerLabel.includes('built-in') || 
            lowerLabel.includes('facetime') || lowerLabel.includes('chicony')) {
            return 'integrated';
        }
        
        return index === 0 ? 'integrated' : 'external';
    }
    
    // 🎯 NUEVA FUNCIÓN: Detectar prioridad de cámara
    getCameraPriority(label) {
        const lowerLabel = label.toLowerCase();
        
        // 🥇 ALTA PRIORIDAD: Móviles y apps especializadas
        if (lowerLabel.includes('camo') || lowerLabel.includes('droidcam') || 
            lowerLabel.includes('android') || lowerLabel.includes('epoccam') ||
            lowerLabel.includes('webcamoid') || lowerLabel.includes('obs virtual')) {
            return 'HIGH';
        }
        
        // 📷 PRIORIDAD NORMAL: Todo lo demás
        return 'NORMAL';
    }
}


// Exportar a window
window.QuickCameraDetector = QuickCameraDetector;
