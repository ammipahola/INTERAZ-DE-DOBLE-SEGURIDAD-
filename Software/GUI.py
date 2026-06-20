import sys
import serial
import numpy as np
import sounddevice as sd
from collections import deque

from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg

PORT = "COM6 "
BAUD = 115200

FS_EMG = 500
WINDOW_RMS = int(0.2 * FS_EMG)
OFFSET_DC_HARDWARE = 2048
UMBRAL_EMG = 230.0

FS_AUDIO = 16000
FREQ_MIN_VOZ = 100
FREQ_MAX_VOZ = 3000
UMBRAL_VOZ_FFT = .5
UMBRAL_VOZ_ZCR = 0.05
UMBRAL_FRICATIVA_ZCR = 0.22

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
except Exception as e:
    print(f"Puerto {PORT} no detectado ({e}). Modo simulación EMG (12 bits) activado.")
    ser = None

buffer_crudo = deque(maxlen=1000)

emg_activo = False
comando_voz_actual = "SILENCIO"
energia_actual = 0
zcr_actual = 0

vector_frecuencias = np.zeros(401)
vector_magnitudes = np.zeros(401)

grabando_palabra = False
buffer_audio_palabra = []
bloques_consecutivos_silencio = 0
TOLERANCIA_SILENCIO_BLOQUES = 4  

def audio_callback(indata, frames, time, status):
    global comando_voz_actual, energia_actual, zcr_actual
    global grabando_palabra, buffer_audio_palabra, bloques_consecutivos_silencio
    global vector_frecuencias, vector_magnitudes

    audio_bloque = indata[:, 0]
    N = len(audio_bloque)
    
    ventana = np.hanning(N)
    audio_ventaneado = audio_bloque * ventana
    
    fft_resultado = np.fft.rfft(audio_ventaneado)
    magnitudes = np.abs(fft_resultado)
    frecuencias = np.fft.rfftfreq(N, d=1/FS_AUDIO)
    
    vector_frecuencias = frecuencias
    vector_magnitudes = magnitudes
    
    indices_voz = (frecuencias >= FREQ_MIN_VOZ) & (frecuencias <= FREQ_MAX_VOZ)
    energia_espectral = np.sum(magnitudes[indices_voz] ** 2) / N
    energia_actual = energia_espectral

    cruces = np.sum(np.diff(np.sign(audio_bloque)) != 0)
    zcr = cruces / N
    zcr_actual = zcr

    hay_actividad = (energia_espectral > UMBRAL_VOZ_FFT) and (zcr > UMBRAL_VOZ_ZCR)

    if hay_actividad:
        if not grabando_palabra:
            grabando_palabra = True
            buffer_audio_palabra = []
            comando_voz_actual = "ESCUCHANDO..."
        
        buffer_audio_palabra.append(audio_bloque)
        bloques_consecutivos_silencio = 0  
        
    elif grabando_palabra:
        buffer_audio_palabra.append(audio_bloque)
        bloques_consecutivos_silencio += 1
        
        if bloques_consecutivos_silencio >= TOLERANCIA_SILENCIO_BLOQUES:
            grabando_palabra = False
            audio_completo = np.concatenate(buffer_audio_palabra)
            
            mitad = len(audio_completo) // 2
            segmento_inicio = audio_completo[:mitad]
            segmento_fin = audio_completo[mitad:]
            
            zcr_fin = np.sum(np.diff(np.sign(segmento_fin)) != 0) / len(segmento_fin)
            energia_inicio = np.mean(segmento_inicio**2)
            energia_fin = np.mean(segmento_fin**2)
            
            if zcr_fin > UMBRAL_FRICATIVA_ZCR:
                comando_voz_actual = "BAJA"  
            elif energia_inicio > energia_fin:
                comando_voz_actual = "ALTO"  
            else:
                comando_voz_actual = "DESCONOCIDO"
                
            bloques_consecutivos_silencio = -20  
            
    else:
        if bloques_consecutivos_silencio < 0:
            bloques_consecutivos_silencio += 1
        else:
            comando_voz_actual = "SILENCIO"

audio_stream = sd.InputStream(samplerate=FS_AUDIO, channels=1, callback=audio_callback, blocksize=800)
audio_stream.start()

class EMGVoiceMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HMI Bimodal - Sistema de Control de Doble Seguridad")
        self.resize(1100, 750)
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI', Arial; }
            QFrame { background-color: #1E1E1E; border-radius: 8px; border: 1px solid #2C2C2C; }
            QLabel { border: none; }
        """)

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        self.frame_status = QFrame()
        status_layout = QVBoxLayout(self.frame_status)
        self.lbl_candado = QLabel("SISTEMA BLOQUEADO")
        self.lbl_candado.setAlignment(Qt.AlignCenter)
        self.lbl_candado.setFont(QFont("Arial", 22, QFont.Bold))
        self.lbl_candado.setStyleSheet("color: #FF5252; padding: 10px;")
        self.lbl_diagnostico = QLabel("Estado: Esperando coincidencia bimodal...")
        self.lbl_diagnostico.setAlignment(Qt.AlignCenter)
        self.lbl_diagnostico.setFont(QFont("Arial", 11))
        self.lbl_diagnostico.setStyleSheet("color: #888888;")
        status_layout.addWidget(self.lbl_candado)
        status_layout.addWidget(self.lbl_diagnostico)
        main_layout.addWidget(self.frame_status, 0, 0, 1, 2)

        frame_emg = QFrame()
        emg_layout = QVBoxLayout(frame_emg)
        lbl_title_emg = QLabel("SEÑAL EMG RECTIFICADA")
        lbl_title_emg.setFont(QFont("Arial", 13, QFont.Bold))
        lbl_title_emg.setStyleSheet("color: #00E5FF;")
        self.lbl_rms = QLabel("Calculando RMS: 0.00")
        self.lbl_rms.setFont(QFont("Arial", 11))
        self.lbl_emg_status = QLabel("MÚSCULO: REPOSO")
        self.lbl_emg_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.lbl_emg_status.setStyleSheet("color: #757575;")
        
        self.plot_emg = pg.PlotWidget()
        self.plot_emg.setBackground('#1E1E1E')
        self.plot_emg.showGrid(x=False, y=True, alpha=0.3)
        
        self.plot_emg.setYRange(0, 400, padding=0)  
        self.plot_emg.getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis, enable=False) 
        
        self.curve_emg = self.plot_emg.plot(pen=pg.mkPen(color='#00E5FF', width=1.5))
        self.line_th_emg = pg.InfiniteLine(pos=UMBRAL_EMG, angle=0, pen=pg.mkPen(color='#FF5252', width=1.5, style=Qt.DashLine))
        self.plot_emg.addItem(self.line_th_emg)

        emg_layout.addWidget(lbl_title_emg)
        emg_layout.addWidget(self.plot_emg)
        emg_layout.addWidget(self.lbl_rms)
        emg_layout.addWidget(self.lbl_emg_status)
        main_layout.addWidget(frame_emg, 1, 0)

        frame_voice = QFrame()
        voice_layout = QVBoxLayout(frame_voice)
        lbl_title_voice = QLabel("ESPECTRO DE FRECUENCIA EN TIEMPO REAL")
        lbl_title_voice.setFont(QFont("Arial", 13, QFont.Bold))
        lbl_title_voice.setStyleSheet("color: #69F0AE;")
        self.lbl_energia = QLabel("Energía FFT (100Hz-3kHz): 0.000000")
        self.lbl_energia.setFont(QFont("Arial", 11))
        self.lbl_zcr = QLabel("Cruces por Cero (ZCR): 0.00")
        self.lbl_zcr.setFont(QFont("Arial", 11))
        self.lbl_voz_status = QLabel("VOZ: SILENCIO")
        self.lbl_voz_status.setFont(QFont("Arial", 13, QFont.Bold))
        self.lbl_voz_status.setStyleSheet("color: #757575;")
        
        self.plot_voice = pg.PlotWidget()
        self.plot_voice.setBackground('#1E1E1E')
        self.plot_voice.setLabel('bottom', 'Frecuencia', 'Hz')
        self.plot_voice.setXRange(0, 4000) 
        self.plot_voice.showGrid(x=True, y=True, alpha=0.3)
        
        self.plot_voice.setYRange(0, 20, padding=0)  
        self.plot_voice.getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis, enable=False) 
        
        self.curve_voice = self.plot_voice.plot(pen=pg.mkPen(color='#69F0AE', width=1.5))

        voice_layout.addWidget(lbl_title_voice)
        voice_layout.addWidget(self.plot_voice)
        voice_layout.addWidget(self.lbl_energia)
        voice_layout.addWidget(self.lbl_zcr)
        voice_layout.addWidget(self.lbl_voz_status)
        main_layout.addWidget(frame_voice, 1, 1)

        self.frame_luz = QFrame()
        layout_luz = QVBoxLayout(self.frame_luz)
        self.lbl_titulo_luz = QLabel("ACTUADOR")
        self.lbl_titulo_luz.setAlignment(Qt.AlignCenter)
        self.lbl_titulo_luz.setFont(QFont("Arial", 11, QFont.Bold))
        self.lbl_titulo_luz.setStyleSheet("color: #888888;")
        self.luz_piloto = QLabel()
        self.luz_piloto.setFixedSize(100, 100) 
        self.luz_piloto.setAlignment(Qt.AlignCenter)
        self.estilo_luz_config = "border-radius: 50px; border: 4px solid;"
        self.estilo_luz_apagada = self.estilo_luz_config + "background-color: #212121; border-color: #424242;"
        self.estilo_luz_encendida = self.estilo_luz_config + "background-color: #FF1744; border-color: #FF8A80;"
        self.luz_piloto.setStyleSheet(self.estilo_luz_apagada)
        layout_luz.addWidget(self.lbl_titulo_luz)
        layout_luz.addWidget(self.luz_piloto, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.frame_luz, 2, 0, 1, 2)

        main_layout.setRowStretch(0, 1)
        main_layout.setRowStretch(1, 4)
        main_layout.setRowStretch(2, 2)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(20)

    def update_data(self):
        global emg_activo, comando_voz_actual, energia_actual, zcr_actual
        global vector_frecuencias, vector_magnitudes

        if ser is not None:
            while ser.in_waiting:
                try:
                    value = int(ser.readline().decode().strip())
                    buffer_crudo.append(value - OFFSET_DC_HARDWARE)
                except:
                    pass
        else:
            offset_simulado = OFFSET_DC_HARDWARE + np.random.normal(0, 4)
            if np.random.rand() > 0.92 and not emg_activo:
                offset_simulado += np.random.choice([-1, 1]) * np.random.uniform(140, 240)
            buffer_crudo.append(int(offset_simulado - OFFSET_DC_HARDWARE))

        if len(buffer_crudo) > 0:
            data = np.array(buffer_crudo)
            data_rectificada = np.abs(data)
            self.curve_emg.setData(data_rectificada)

            if len(data) >= WINDOW_RMS:
                ventana = data[-WINDOW_RMS:]
                rms = np.sqrt(np.mean(ventana**2))
                self.lbl_rms.setText(f"RMS (Fuerza Real): {rms:.2f} (Umbral: {UMBRAL_EMG})")

                if rms > UMBRAL_EMG:
                    emg_activo = True
                    self.lbl_emg_status.setText("MÚSCULO: CONTRACCIÓN")
                    self.lbl_emg_status.setStyleSheet("color: #121212; background-color: #00E5FF; font-weight: bold; border-radius: 4px; padding: 2px;")
                else:
                    emg_activo = False
                    self.lbl_emg_status.setText("MÚSCULO: REPOSO")
                    self.lbl_emg_status.setStyleSheet("color: #757575; background-color: transparent;")

        self.curve_voice.setData(vector_frecuencias, vector_magnitudes)
        
        self.lbl_energia.setText(f"Energía FFT (100Hz-3kHz): {energia_actual:.6f} (Umbral: {UMBRAL_VOZ_FFT})")
        self.lbl_zcr.setText(f"Tasa Cruces por Cero (ZCR): {zcr_actual:.2f}")

        if comando_voz_actual in ["ALTO", "BAJA"]:
            self.lbl_voz_status.setText(f"VOZ: COMANDO [{comando_voz_actual}] EXTRAÍDO")
            self.lbl_voz_status.setStyleSheet("color: #69F0AE; background-color: #0F3421; padding: 2px; border-radius: 4px;")
        elif comando_voz_actual == "ESCUCHANDO...":
            self.lbl_voz_status.setText("VOZ: CAPTURANDO PALABRA...")
            self.lbl_voz_status.setStyleSheet("color: #FFD54F;")
        else:
            self.lbl_voz_status.setText("VOZ: SILENCIO")
            self.lbl_voz_status.setStyleSheet("color: #757575; background-color: transparent;")

        hable_comando = comando_voz_actual in ["ALTO", "BAJA"]

        if emg_activo and hable_comando:
            self.lbl_candado.setText(f"🔓 SISTEMA DESBLOQUEADO ({comando_voz_actual})")
            self.lbl_candado.setStyleSheet("color: #69F0AE; background-color: #1B5E20; padding: 10px; border-radius: 8px;")
            self.lbl_diagnostico.setText(f"Éxito: Validación bimodal correcta para el comando '{comando_voz_actual}'.")
            
            if comando_voz_actual == "ALTO":
                self.luz_piloto.setStyleSheet(self.estilo_luz_encendida) 
                self.lbl_titulo_luz.setText("ACTUADOR: ACTIVO")
                self.lbl_titulo_luz.setStyleSheet("color: #FF1744; font-weight: bold;")
            elif comando_voz_actual == "BAJA":
                self.luz_piloto.setStyleSheet(self.estilo_luz_apagada)   
                self.lbl_titulo_luz.setText("ACTUADOR: APAGADO")
                self.lbl_titulo_luz.setStyleSheet("color: #888888; font-weight: bold;")
            
        elif emg_activo and not hable_comando:
            self.lbl_candado.setText("🔒 SISTEMA BLOQUEADO")
            self.lbl_candado.setStyleSheet("color: #FF5252; background-color: #2D1414; padding: 10px; border-radius: 8px;")
            if comando_voz_actual == "DESCONOCIDO":
                self.lbl_diagnostico.setText("⚠️ FALLO: Contracción detectada, pero la palabra no coincide con 'ALTO' o 'BAJA'.")
            else:
                self.lbl_diagnostico.setText("⚠️ FALLO: Contracción aislada (Falta comando de voz coincidente).")
                
        elif not emg_activo and hable_comando:
            self.lbl_candado.setText("🔒 SISTEMA BLOQUEADO")
            self.lbl_candado.setStyleSheet("color: #FF5252; background-color: #2D1414; padding: 10px; border-radius: 8px;")
            self.lbl_diagnostico.setText(f"⚠️ FALLO: Comando acústico '{comando_voz_actual}' detectado sin activación muscular.")
            
        else:
            self.lbl_candado.setText("🔒 SISTEMA BLOQUEADO")
            self.lbl_candado.setStyleSheet("color: #FF5252; background-color: transparent; padding: 10px;")
            if comando_voz_actual == "ESCUCHANDO...":
                self.lbl_diagnostico.setText("Registrando ráfagas acústicas y espectro FFT del micrófono...")
            else:
                self.lbl_diagnostico.setText("Estado: Esperando coincidencia bimodal...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EMGVoiceMonitor()
    window.show()
    sys.exit(app.exec_())
