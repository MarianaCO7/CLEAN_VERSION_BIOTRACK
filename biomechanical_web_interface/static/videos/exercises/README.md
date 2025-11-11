# 🎬 Videos de Demostración de Ejercicios

## 📁 Estructura de Archivos

Los videos deben nombrarse siguiendo esta convención:

```
{articulacion}_{ejercicio}.mp4
```

## 📋 Nomenclatura de Archivos

### Hombro (Shoulder)
- `shoulder_flexion.mp4` - Flexión de hombro
- `shoulder_extension.mp4` - Extensión de hombro
- `shoulder_abduction.mp4` - Abducción de hombro

### Codo (Elbow)
- `elbow_flexion.mp4` - Flexión de codo
- `elbow_extension.mp4` - Extensión de codo

### Cadera (Hip)
- `hip_flexion.mp4` - Flexión de cadera
- `hip_extension.mp4` - Extensión de cadera
- `hip_abduction.mp4` - Abducción de cadera

### Rodilla (Knee)
- `knee_flexion.mp4` - Flexión de rodilla
- `knee_extension.mp4` - Extensión de rodilla

### Tobillo (Ankle)
- `ankle_dorsiflexion.mp4` - Dorsiflexión
- `ankle_plantarflexion.mp4` - Plantiflexión

### Cuello (Neck)
- `neck_flexion.mp4` - Flexión cervical
- `neck_extension.mp4` - Extensión cervical

## 🎥 Especificaciones Técnicas Recomendadas

- **Formato**: MP4 (H.264)
- **Resolución**: 1280x720 (720p) o 1920x1080 (1080p)
- **Duración**: 15-30 segundos
- **Frame Rate**: 30 fps
- **Bitrate**: 2-5 Mbps
- **Audio**: No necesario (opcional)

## 📝 Contenido del Video

Cada video debe mostrar:
1. **Posición inicial**: 3-5 segundos
2. **Movimiento completo**: 2-3 repeticiones lentas
3. **Posición final**: 2-3 segundos

## 🎨 Recomendaciones de Grabación

- Fondo neutro (preferiblemente uniforme)
- Buena iluminación
- Vista lateral o frontal (según el ejercicio)
- Ropa que contraste con el fondo
- Movimientos lentos y controlados
- Enfoque en la articulación específica

## 💾 Tamaño de Archivo

Mantener cada video por debajo de 10 MB para optimizar la carga.

## 🔄 Conversión de Videos

Si necesitas convertir videos, usa FFmpeg:

```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k -vf scale=1280:720 output.mp4
```

## ✅ Checklist

Para cada ejercicio:
- [ ] Video grabado con buena calidad
- [ ] Duración apropiada (15-30s)
- [ ] Nombre de archivo correcto
- [ ] Tamaño optimizado (<10 MB)
- [ ] Formato MP4 compatible
- [ ] Movimiento claramente visible
