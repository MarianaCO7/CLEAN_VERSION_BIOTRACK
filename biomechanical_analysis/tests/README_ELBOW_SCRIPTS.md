# 🦾 Scripts de Análisis de Codo

Este directorio contiene scripts especializados para análisis biomecánico de **CODO**.

---

## 📁 Scripts de Codo Disponibles

### 1. **`test_elbow_profile.py`** (Vista de PERFIL)
- 🎯 **Solo FLEXIÓN/EXTENSIÓN** de codo
- 🎯 Requiere posición de **PERFIL** (lateral)
- ✅ Análisis de un solo codo
- ✅ Rango de medición: 0-150°

**Movimientos analizados:**
- Flexión del codo (llevar mano hacia hombro)
- Extensión del codo (estirar el brazo)

**Sistema de medición:**
```
0° = Brazo EXTENDIDO (antebrazo hacia abajo)
90° = Antebrazo HORIZONTAL  
150° = FLEXIÓN MÁXIMA (mano toca hombro)

ROM normal: 0-150°
```

**Cuándo usar:**
- Evaluación específica de ROM de codo
- Rehabilitación post-fractura
- Detección de limitaciones de movimiento
- Medición de progreso en terapia

---

### 2. **`test_elbow_frontal.py`** (Vista FRONTAL)
- 🎯 **FLEXIÓN BILATERAL** de codos
- 🎯 Requiere posición de **FRENTE**
- ✅ Mide **ambos codos simultáneamente**
- ✅ **Análisis de simetría** automático
- ✅ Detección de asimetrías

**Movimientos analizados:**
- Flexión bilateral (ambos codos flexionan al mismo tiempo)
- Comparación izquierda vs derecha
- Diferencias de ROM entre lados

**Sistema de medición:**
```
0° = Brazos EXTENDIDOS (antebrazos hacia abajo)
90° = Antebrazos HORIZONTALES
150° = FLEXIÓN MÁXIMA (manos tocan hombros)
```

**Análisis de simetría:**
- 🟢 Verde: Diferencia < 10° (EXCELENTE)
- 🟠 Naranja: Diferencia 10-20° (ACEPTABLE)
- 🔴 Rojo: Diferencia > 20° (REVISAR - posible lesión o debilidad)

**Cuándo usar:**
- Detección de asimetrías post-lesión
- Evaluación bilateral de fuerza
- Comparación de lado dominante vs no dominante
- Seguimiento de recuperación simétrica

---

## 🔧 Detalles Técnicos

### Landmarks Utilizados

**MediaPipe Pose Landmarks:**
```python
# Vista de PERFIL (el lado visible):
SHOULDER → ELBOW → WRIST

# Vista FRONTAL (ambos lados):
LEFT_SHOULDER → LEFT_ELBOW → LEFT_WRIST
RIGHT_SHOULDER → RIGHT_ELBOW → RIGHT_WRIST
```

### Sistema Goniómetro

**Puntos de referencia:**
- **Punto de vértice:** CODO (punto amarillo grande)
- **Eje fijo (verde):** Línea vertical que pasa por el codo
- **Eje móvil (azul):** Línea CODO → MUÑECA (antebrazo)

**Cálculo del ángulo:**
```
Ángulo = arccos(vertical · antebrazo)
Donde:
  - vertical = [0, 1] (vector hacia abajo)
  - antebrazo = [muñeca - codo] (normalizado)
```

---

## 🚀 Cómo Ejecutar

### Opción 1: Vista de Perfil
```bash
python test_elbow_profile.py
```

### Opción 2: Vista Frontal
```bash
python test_elbow_frontal.py
```

---

## ⌨️ Controles

| Tecla | Acción |
|-------|--------|
| **Q** | Salir de la aplicación |
| **R** | Reiniciar estadísticas (ROM máximo) |
| **M** | Cambiar modo de visualización |

---

## 🎨 Modos de Visualización

| Modo | Descripción | Visualización |
|------|-------------|---------------|
| **CLEAN** | Solo líneas biomecánicas | Línea verde + línea azul + puntos |
| **FULL** | Con skeleton MediaPipe | Todo el esqueleto + líneas |
| **MINIMAL** | Mínimo esencial | Solo antebrazo + eje vertical |

---

## 📊 Interpretación de Resultados

### ROM Normal de Codo

| Edad | Flexión Normal | Notas |
|------|---------------|-------|
| **Adultos** | 140-150° | Rango saludable |
| **Deportistas** | 145-155° | Puede exceder por elasticidad |
| **> 60 años** | 130-145° | Disminución natural |

### Evaluación del ROM

**Vista de PERFIL:**
- ✅ **> 140°** = EXCELENTE ROM
- ✅ **120-140°** = ROM BUENO (funcional)
- ⚠️ **90-120°** = ROM LIMITADO (revisar causa)
- 🔴 **< 90°** = ROM MUY LIMITADO (requiere intervención)

**Vista FRONTAL (Simetría):**
- ✅ **< 10° diferencia** = Simetría EXCELENTE
- ⚠️ **10-20° diferencia** = Asimetría ACEPTABLE (monitorear)
- 🔴 **> 20° diferencia** = Asimetría SIGNIFICATIVA (evaluar causa)

### Posibles Causas de Limitación

**ROM Reducido:**
- Rigidez articular post-inmovilización
- Fractura previa de codo
- Artrosis o artritis
- Contractura de Volkmann
- Osificación heterotópica

**Asimetría > 20°:**
- Lesión unilateral reciente
- Debilidad muscular de un lado
- Diferencia de dominancia extrema
- Compensación por dolor

---

## 📐 Visualización en Pantalla

### Vista de PERFIL:
```
┌─────────────────────────────────────┐
│ 🦾 ANÁLISIS DE CODO - PERFIL        │
│                                     │
│ Lado analizado: DERECHO             │
│ Ángulo actual: 125° [FLEXIONADO]   │
│ ROM máximo: 142°                    │
│                                     │
│ [████████████████░░] 142°/150°      │
│                                     │
│ Evaluación: EXCELENTE ROM           │
└─────────────────────────────────────┘

Elementos visuales:
│ ← Línea verde (eje vertical fijo)
🟡 ← Codo (vértice del ángulo)
 \
  \ ← Línea azul (antebrazo)
   \
    🔵 ← Muñeca
```

### Vista FRONTAL:
```
┌─────────────────────────────────────┐
│ 🦾 ANÁLISIS DE CODO - FRONTAL       │
│                                     │
│ Codo IZQ: 128° | DER: 135°          │
│ ROM IZQ: 145° | DER: 148°           │
│                                     │
│ Diferencia: 3° [🟢 EXCELENTE]       │
│                                     │
│ IZQ [████████████████░] 145°/150°   │
│ DER [█████████████████] 148°/150°   │
│                                     │
│ Simetría: PERFECTA                  │
└─────────────────────────────────────┘
```

---

## 🔄 Diferencias con Scripts de Hombro

| Característica | Hombro | Codo |
|----------------|--------|------|
| **Punto de vértice** | Hombro | Codo |
| **Eje vertical pasa por** | Hombro | Codo |
| **Segmento medido** | Brazo (hombro→codo) | Antebrazo (codo→muñeca) |
| **ROM máximo normal** | 180° | 150° |
| **Landmarks** | Cadera-Hombro-Codo | Hombro-Codo-Muñeca |

---

## ⚙️ Optimizaciones Implementadas

✅ **Todas las optimizaciones de los scripts de hombro:**
- Procesamiento en 640x480 (upscaling a 720p)
- Dibujos OpenCV con LINE_4 (no LINE_AA)
- Caché de colores pre-calculados
- Profiling de FPS y latencia en tiempo real
- Threading para procesamiento asíncrono

✅ **Método de detección de lado:**
- Usa **solo visibilidad** (consistente con scripts de hombro)
- Opcional: Código comentado para usar Z+Visibilidad (más robusto)

---

## 📋 Checklist de Uso Clínico

### Antes de la evaluación:
- [ ] Paciente en ropa que permita ver brazos
- [ ] Iluminación uniforme
- [ ] Cámara a altura del pecho
- [ ] Distancia: 1.5-2 metros

### Durante la evaluación:
- [ ] **PERFIL:** Paciente de lado, brazo visible hacia cámara
- [ ] **FRONTAL:** Paciente de frente, ambos brazos visibles
- [ ] Realizar movimiento LENTAMENTE
- [ ] Mantener tronco estable (sin inclinarse)
- [ ] Repetir 2-3 veces para confirmar ROM

### Después de la evaluación:
- [ ] Anotar ROM máximo alcanzado
- [ ] Si frontal: Anotar diferencia de simetría
- [ ] Comparar con evaluación anterior (progreso)
- [ ] Documentar dolor o limitaciones reportadas

---

## 🆘 Troubleshooting

**Problema:** "No se detecta persona"
- ✅ Asegúrate de estar completamente en el encuadre
- ✅ Iluminación suficiente (no contraluz)
- ✅ Distancia adecuada (1.5-2 metros)

**Problema:** Ángulos incorrectos o erráticos
- ✅ Mantén el cuerpo estable
- ✅ No muevas el tronco durante la flexión
- ✅ Verifica que la línea verde sea perfectamente vertical

**Problema:** En frontal, solo detecta un codo
- ✅ Asegúrate de estar de FRENTE a la cámara
- ✅ Ambos brazos deben estar visibles
- ✅ No cruces los brazos frente al cuerpo

**Problema:** Script detecta lado incorrecto (perfil)
- ✅ Gira más el cuerpo (90° respecto a cámara)
- ✅ Aleja el brazo no medido del encuadre
- ✅ Opcional: Activa método Z+Visibilidad (descomentar código)

---

## 📚 Relación con otros Scripts

**Scripts de Hombro:**
- `test_shoulder_profile.py` - Flexión/Extensión de hombro
- `test_shoulder_frontal.py` - Abducción de hombro

**Scripts de Codo (estos):**
- `test_elbow_profile.py` - Flexión/Extensión de codo
- `test_elbow_frontal.py` - Flexión bilateral de codo

**Próximos segmentos planificados:**
- Cadera (flexión, abducción, rotación)
- Rodilla (flexión/extensión)
- Tobillo (dorsiflexión/plantarflexión)

---

## 📖 Referencias Clínicas

**ROM Normal de Codo:**
- Flexión: 0-150° (Norkin & White, 2016)
- Extensión completa: 0° (posición neutra)
- Hiperextensión: Hasta -10° en algunas personas

**Patrones de Movimiento:**
- Actividades de vida diaria requieren 30-130° (Morrey et al.)
- Comer requiere ~140° de flexión
- Higiene personal requiere 120-140°

---

## ✅ Validación Técnica

| Criterio | Estado |
|----------|--------|
| Sintaxis Python | ✅ Sin errores |
| Imports | ✅ Completos |
| Eje vertical fijo | ✅ Implementado |
| Detección de lado | ✅ Consistente con hombro |
| Análisis bilateral | ✅ Solo en frontal |
| Simetría | ✅ Con código de color |
| Optimizaciones | ✅ Todas aplicadas |
| Modos visualización | ✅ CLEAN/FULL/MINIMAL |
| Métricas rendimiento | ✅ FPS + latencia |
| Documentación | ✅ Completa |

---

Creado: Noviembre 11, 2025  
Versión: 1.0  
Basado en: Scripts de hombro v1.0
