# INTERFAZ DE DOBLE SEGURIDAD
Este trabajo desarrolla una interfaz humano-máquina basado en una metodología de doble seguridad mediante el uso de señales electromiografícas (EMG) y voz.  

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

# Instalación y ejecución 
1. Requisitos previos
- Python 3.9 o superior
- Pip instalado
- Micrófono funcional
-Módulo EMG conectado por puerto serial
  
# Librerias utilizadas
- Python 3
- NumPy
- PyQt5 (interfaz gráfica)
- PyQtGraph (visualización en tiempo real)
- SoundDevice (adquisición de audio)
- PySerial (comunicación con hardware)

# Autor 
Ammi Pahola Rodriguez Salgado 
Irais Guadaupe Solano Rosas
Pablo Azgad Camarena Mendoza

# Licencia
Uso académico y educativo.
