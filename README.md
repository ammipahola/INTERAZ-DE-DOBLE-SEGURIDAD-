# INTERAZ-DE-DOBLE-SEGURIDAD-
Este trabajo desarrolla una interfaz humano-máquina basado en una metodología de doble seguridad mediante el uso de señales electromiografícas (EMG) y voz.  -

# Objetivo
Diseñar e implementar un sistema  basado en señales biológicas (EMG y voz) que permita la activación de un actuador únicamente cuando ambas señales coincidan dentro de una ventana temporal definida.

# Tecnologías utilizadas
- Python 3
- NumPy
- PyQt5 (interfaz gráfica)
- PyQtGraph (visualización en tiempo real)
- SoundDevice (adquisición de audio)
- PySerial (comunicación con hardware)

# Señales utilizadas
## 1. Señal EMG
- Adquisición mediante electrodos (activo, referencia y tierra)
- Módulo: AD8232
- Procesamiento:
  - Eliminación de offset
  - Rectificación de la señal
  - Cálculo de RMS en ventana de 200 ms
  - Comparación con umbral de activación
## 2. Señal de voz
- Captura mediante micrófono de computadora
- Procesamiento:
  - Ventaneo (Hanning)
  - Transformada Rápida de Fourier (FFT)
  - Energía espectral en banda de 100 Hz a 3000 Hz
  - Tasa de cruces por cero (ZCR)
  - Detección de comandos: “ALTO” y “BAJA”

# Lógica del sistema
El sistema funciona bajo una lógica bimodal: si la señal EMG supera el umbral de activación. Y simultáneamente se detecta un comando de voz válido.Entonces: el sistema se desbloquea.Se activa el actuador (simulado o físico)
En caso contrario, el sistema permanece bloqueado.

# Resultados
El sistema fue capaz de detectar correctamente la activación muscular y los comandos de voz en tiempo real. La validación bimodal permitió mejorar la seguridad del sistema al evitar activaciones accidentales por señales individuales.

# Instalación y ejecución
 1. Requisitos previos
- Python 3.9 o superior
- Pip instalado
- Micrófono funcional
- (Opcional) módulo EMG conectado por puerto serial
 2. Instalación de dependencias
```bash
pip install numpy pyqt5 pyqtgraph sounddevice pyserial

#Posibles mejoras
- Implementación de filtros digitales para reducción de ruido en EMG
- Uso de sensores EMG especializados en lugar de módulos ECG adaptados
- Mejora del reconocimiento de voz mediante modelos de machine learning
- Integración con actuadores físicos reales

#Autor
Ammi Pahola Rodriguez Sagado
Pablo Azgad Camarena Mendoza
Irais Guadalupe Solano Rosas 

# Licencia
Uso académico y educativo.
