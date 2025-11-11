# 📊 Scripts de Análisis de Hombro

Este directorio contiene **3 scripts** para análisis biomecánico de hombro:

---

## 📁 Scripts Disponibles

### 1. **`test_shoulder.py.py`** (Script Original - Dual Mode)
- ✅ **Detección automática** de orientación (PERFIL/FRONTAL)
- ✅ Analiza **ambos tipos** de movimiento en un solo script
- ✅ Cambia automáticamente según la posición del usuario
- ⚠️ Más complejo, más líneas de código
- 📦 **Uso:** Análisis general, demos, investigación

**Cuándo usar:**
- Quieres flexibilidad total
- No estás seguro de qué movimiento necesitas
- Investigación o evaluación inicial

---

### 2. **`test_shoulder_profile.py`** (Vista de PERFIL - Especializado)
- 🎯 **Solo FLEXIÓN/EXTENSIÓN** de hombro
- 🎯 Requiere posición de **PERFIL**
- ✅ Código más simple y enfocado
- ✅ Menor overhead de procesamiento
- ✅ Interfaz optimizada para un solo movimiento

**Movimientos analizados:**
- Flexión (brazo hacia adelante)
- Extensión (brazo hacia atrás)
- Elevación vertical (brazo hacia arriba)

**Cuándo usar:**
- Evaluación específica de flexión/extensión
- Rehabilitación de movimientos sagitales
- Protocolos estandarizados de perfil

**Sistema de medición:**
```
0° = Brazo hacia ABAJO (neutro)
+90° = Brazo HORIZONTAL hacia adelante (FLEXIÓN)
-90° = Brazo HORIZONTAL hacia atrás (EXTENSIÓN)
180° = Brazo hacia ARRIBA
```

---

### 3. **`test_shoulder_frontal.py`** (Vista FRONTAL - Especializado)
- 🎯 **Solo ABDUCCIÓN BILATERAL**
- 🎯 Requiere posición de **FRENTE**
- ✅ Mide **ambos brazos simultáneamente**
- ✅ **Análisis de simetría** automático
- ✅ Detecta asimetrías entre lado izquierdo y derecho

**Movimientos analizados:**
- Abducción bilateral (levantar brazos lateralmente)
- Comparación izquierda vs derecha
- Diferencias de ROM entre lados

**Cuándo usar:**
- Evaluación de abducción de hombro
- Detección de asimetrías
- Rehabilitación de movimientos coronales
- Evaluación bilateral

**Sistema de medición:**
```
0° = Brazos pegados al cuerpo (neutro)
90° = Brazos HORIZONTALES (perpendiculares al cuerpo)
180° = Brazos completamente levantados (vertical)
```

**Análisis de simetría:**
- 🟢 Verde: Diferencia < 10° (EXCELENTE)
- 🟠 Naranja: Diferencia 10-20° (ACEPTABLE)
- 🔴 Rojo: Diferencia > 20° (REVISAR)

---

## 🚀 Cómo Ejecutar

### Opción 1: Script Original (Dual Mode)
```bash
python test_shoulder.py.py
```

### Opción 2: Vista de Perfil (Especializado)
```bash
python test_shoulder_profile.py
```

### Opción 3: Vista Frontal (Especializado)
```bash
python test_shoulder_frontal.py
```

---

## ⌨️ Controles (Todos los Scripts)

| Tecla | Acción |
|-------|--------|
| **Q** | Salir |
| **R** | Reiniciar estadísticas |
| **M** | Cambiar modo de visualización |

---

## 🎨 Modos de Visualización

| Modo | Descripción | Cuándo usar |
|------|-------------|-------------|
| **CLEAN** | Solo líneas biomecánicas | Análisis profesional |
| **FULL** | Con skeleton MediaPipe | Debugging/verificación |
| **MINIMAL** | Líneas esenciales | Máximo rendimiento |

---

## 📊 Comparación de Scripts

| Característica | `test_shoulder.py.py` | `test_shoulder_profile.py` | `test_shoulder_frontal.py` |
|----------------|----------------------|----------------------------|---------------------------|
| **Detección automática** | ✅ Sí | ❌ No | ❌ No |
| **Flexión/Extensión** | ✅ Sí | ✅ Sí | ❌ No |
| **Abducción** | ✅ Sí | ❌ No | ✅ Sí |
| **Análisis bilateral** | ✅ Sí | ❌ No | ✅ Sí |
| **Análisis de simetría** | ⚠️ Básico | ❌ No | ✅ Avanzado |
| **Líneas de código** | ~1000 | ~550 | ~580 |
| **Complejidad** | Alta | Media | Media |
| **Velocidad** | Normal | +5-10% | +5-10% |

---

## 🎯 Recomendaciones de Uso

### Para Clínica/Fisioterapia:
- **Evaluación inicial**: `test_shoulder.py.py` (explorar todos los movimientos)
- **Seguimiento de flexión**: `test_shoulder_profile.py`
- **Seguimiento de abducción**: `test_shoulder_frontal.py`

### Para Investigación:
- **Estudio completo**: `test_shoulder.py.py`
- **Protocolo estandarizado**: Scripts especializados según movimiento

### Para Desarrollo:
- **Testing rápido**: Scripts especializados (menos código que revisar)
- **Features nuevas**: `test_shoulder.py.py` (más completo)

---

## 🔧 Diferencias Técnicas

### `test_shoulder_profile.py`:
- Clase: `ShoulderProfileAnalyzer`
- Método principal: `calculate_extension_angle()`
- Variables: `current_angle`, `max_angle`, `side`
- Sin detección de vista automática
- ~450 líneas menos que original

### `test_shoulder_frontal.py`:
- Clase: `ShoulderFrontalAnalyzer`
- Método principal: `calculate_abduction_angle()`
- Variables: `left_abduction_angle`, `right_abduction_angle`, `max_left_abduction`, `max_right_abduction`
- Análisis de diferencia entre lados
- ~420 líneas menos que original

---

## 📈 Ventajas de Scripts Especializados

1. **Código más limpio**: Sin lógica de detección automática
2. **Más rápido**: ~5-10% mejora de FPS
3. **Más simple**: Fácil de mantener y modificar
4. **Más enfocado**: Interfaz específica para cada movimiento
5. **Menos bugs**: Menos casos edge que manejar

---

## 🔄 Migración desde Script Original

Si estabas usando `test_shoulder.py.py`:

**Para análisis de PERFIL:**
```bash
# Antes:
python test_shoulder.py.py  # (colocarse de perfil)

# Ahora:
python test_shoulder_profile.py
```

**Para análisis FRONTAL:**
```bash
# Antes:
python test_shoulder.py.py  # (colocarse de frente)

# Ahora:
python test_shoulder_frontal.py
```

---

## 📝 Notas Importantes

1. **Todos los scripts usan el mismo sistema goniómetro** (eje vertical fijo)
2. **Todos tienen las mismas optimizaciones** (procesamiento 640x480, LINE_4, etc.)
3. **Todos generan métricas de rendimiento** (FPS, latencia)
4. **El script original NO será eliminado** - sigue disponible para uso general

---

## 🆘 Troubleshooting

**Problema:** "No se detecta persona" en script de perfil
- **Solución:** Asegúrate de estar de PERFIL (lateral) a la cámara

**Problema:** "No se detecta persona" en script frontal
- **Solución:** Asegúrate de estar de FRENTE a la cámara

**Problema:** Ángulos incorrectos
- **Solución:** Verifica que estás usando el script correcto para tu orientación

---

## 📚 Recursos Adicionales

- **Documentación del proyecto**: `CONTEXTO_PROYECTO_BIOTRACK.md`
- **Optimizaciones aplicadas**: `OPTIMIZACIONES_IMPLEMENTADAS.md`
- **Modos de visualización**: `MODOS_VISUALIZACION.md`

---

Creado: Noviembre 11, 2025
Versión: 1.0
