import pygame
import array
import math

_som_hover = None
_som_selecionar = None
_som_game_over = None

def inicializar_sons():
    global _som_hover, _som_selecionar, _som_game_over
    if not pygame.mixer or not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        except:
            pass
            
    if pygame.mixer and pygame.mixer.get_init():
        from audio_manager import aplicar_volume_som, carregar_config_audio
        config_audio = carregar_config_audio()
        if _som_hover is None:
            _som_hover = aplicar_volume_som(gerar_som_beep(600, 300, 0.08, volume=1.0), config_audio, canal="efeitos", volume_maximo=0.25)
        if _som_selecionar is None:
            _som_selecionar = aplicar_volume_som(gerar_som_beep(400, 800, 0.15, volume=1.0), config_audio, canal="efeitos", volume_maximo=0.35)
        if _som_game_over is None:
            _som_game_over = aplicar_volume_som(gerar_som_sad_chord(volume=1.0), config_audio, canal="efeitos", volume_maximo=0.45)

def tocar_hover():
    inicializar_sons()
    if _som_hover:
        _som_hover.play()

def tocar_selecionar():
    inicializar_sons()
    if _som_selecionar:
        _som_selecionar.play()

def tocar_game_over():
    inicializar_sons()
    if _som_game_over:
        _som_game_over.play()

def parar_tudo():
    if _som_hover:
        _som_hover.stop()
    if _som_selecionar:
        _som_selecionar.stop()
    if _som_game_over:
        _som_game_over.stop()

def gerar_som_beep(freq_inicial, freq_final, duracao_seg, volume=0.5):
    amostras_por_segundo = 22050
    num_amostras = int(amostras_por_segundo * duracao_seg)
    buf = array.array('h', [0] * num_amostras)
    
    for i in range(num_amostras):
        t = i / amostras_por_segundo
        freq = freq_inicial + (freq_final - freq_inicial) * (t / duracao_seg)
        val = math.sin(2 * math.pi * freq * t)
        
        envelope = 1.0
        if t > duracao_seg - 0.03:
            envelope = (duracao_seg - t) / 0.03
            
        buf[i] = int(val * 32767 * volume * envelope)
        
    return pygame.mixer.Sound(buffer=buf)

def gerar_som_sad_chord(volume=0.5):
    amostras_por_segundo = 22050
    duracao_seg = 2.5
    num_amostras = int(amostras_por_segundo * duracao_seg)
    buf = array.array('h', [0] * num_amostras)
    freqs = [130.81, 155.56, 196.00, 261.63]
    
    for i in range(num_amostras):
        t = i / amostras_por_segundo
        envelope = (duracao_seg - t) / duracao_seg
        if envelope < 0:
            envelope = 0
            
        val = 0
        for f in freqs:
            vibrato = math.sin(2 * math.pi * 6 * t) * 1.5
            val += math.sin(2 * math.pi * (f + vibrato) * t)
            
        val = val / len(freqs)
        buf[i] = int(val * 32767 * volume * envelope)
        
    return pygame.mixer.Sound(buffer=buf)
