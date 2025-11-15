# 📹 LISTA DE VIDEOS REQUERIDOS POR EL SISTEMA

## ✅ FORMATO CORRECTO: `{segmento}_{ejercicio}.mp4`

---

## 🎯 **SHOULDER (Hombro) - 3 videos**
- [x] `shoulder_flexion.mp4` ✅ YA EXISTE
- [x] `shoulder_extension.mp4` ✅ YA EXISTE
- [x] `shoulder_abduction.mp4` ✅ YA EXISTE

---

## 💪 **ELBOW (Codo) - 3 videos**
- [x] `elbow_flexion.mp4` ✅ YA EXISTE
- [x] `elbow_extension.mp4` ✅ YA EXISTE
- [ ] `elbow_overhead_extension.mp4` ❌ FALTA

**NOTA:** El archivo `elbow_pronation_supination.mp4` actual **NO COINCIDE** con ningún ejercicio del JSON. 
**ACCIÓN:** Renombrar o eliminar si es necesario.

---

## 👤 **NECK (Cuello) - 3 videos**
- [ ] `neck_flexion.mp4` ❌ FALTA
- [ ] `neck_rotation.mp4` ❌ FALTA
- [ ] `neck_lateral_flexion.mp4` ❌ FALTA

---

## 🏃 **SPINE (Columna) - 3 videos**
- [ ] `spine_flexion.mp4` ❌ FALTA
- [ ] `spine_extension.mp4` ❌ FALTA
- [ ] `spine_lateral_flexion.mp4` ❌ FALTA

---

## 🦵 **HIP (Cadera) - 3 videos**
- [x] `hip_flexion.mp4` ✅ YA EXISTE
- [x] `hip_extension.mp4` ✅ YA EXISTE (pero falta hip_abduction)
- [ ] `hip_abduction.mp4` ❌ FALTA
- [ ] `hip_adduction.mp4` ❌ FALTA

---

## 🦴 **KNEE (Rodilla) - 2 videos**
- [ ] `knee_flexion.mp4` ❌ FALTA
- [x] `knee_extension.mp4` ✅ YA EXISTE

---

## 👟 **ANKLE (Tobillo) - 3 videos**
- [ ] `ankle_flexion.mp4` ❌ FALTA (actualmente tienes: `ankle_dorsiflexion.mp4`)
- [x] `ankle_dorsiflexion.mp4` ✅ YA EXISTE
- [ ] `ankle_inversion.mp4` ❌ FALTA

**NOTA IMPORTANTE:** El JSON define "flexion" como **Flexión Plantar**, pero tu archivo se llama `ankle_dorsiflexion.mp4` (Dorsiflexión).
**ACCIÓN:** Crear `ankle_flexion.mp4` para Flexión Plantar.

---

## 📊 RESUMEN:

**TOTAL REQUERIDO:** 20 videos
**DISPONIBLES:** 8 videos ✅
**FALTAN:** 12 videos ❌

### ✅ **VIDEOS QUE YA TIENES (8/20):**
1. shoulder_flexion.mp4
2. shoulder_extension.mp4
3. shoulder_abduction.mp4
4. elbow_flexion.mp4
5. elbow_extension.mp4
6. hip_flexion.mp4
7. hip_extension.mp4
8. knee_extension.mp4
9. ankle_dorsiflexion.mp4

### ❌ **VIDEOS QUE FALTAN (12/20):**
1. elbow_overhead_extension.mp4
2. neck_flexion.mp4
3. neck_rotation.mp4
4. neck_lateral_flexion.mp4
5. spine_flexion.mp4
6. spine_extension.mp4
7. spine_lateral_flexion.mp4
8. hip_abduction.mp4
9. hip_adduction.mp4
10. knee_flexion.mp4
11. ankle_flexion.mp4 (Flexión Plantar)
12. ankle_inversion.mp4

---

## 🔧 **SOLUCIÓN TEMPORAL:**

El sistema ya está configurado para mostrar "Video no disponible" cuando falta un archivo.
Puedes ir agregando videos gradualmente y el sistema los detectará automáticamente.

**IMPORTANTE:** Los nombres deben coincidir EXACTAMENTE con los listados arriba (minúsculas, guiones bajos).
