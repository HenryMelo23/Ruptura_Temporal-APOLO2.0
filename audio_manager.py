import Caminhos
import json
import pygame

def carregar_config_audio():
    """Carrega as configurações de áudio do arquivo JSON"""
    try:
        with open("saves/config_audio.json", "r") as f:
            return json.load(f)
    except:
        return {
            "volume_musica": 0.5,
            "volume_efeitos": 0.5,
            "volume_master": 1.0
        }

def aplicar_volume_som(som, config_audio=None):
    """Aplica o volume configurado a um som específico"""
    if config_audio is None:
        config_audio = carregar_config_audio()
    
    volume_master = config_audio.get("volume_master", 1.0)
    volume_efeitos = config_audio.get("volume_efeitos", 0.5)
    
    # Calcula o volume final
    volume_final = volume_efeitos * volume_master
    som.set_volume(volume_final)
    
    return som

def aplicar_volume_musica(config_audio=None):
    """Aplica o volume configurado à música de fundo"""
    if config_audio is None:
        config_audio = carregar_config_audio()
    
    volume_master = config_audio.get("volume_master", 1.0)
    volume_musica = config_audio.get("volume_musica", 0.5)
    
    # Calcula o volume final
    volume_final = volume_musica * volume_master
    pygame.mixer.music.set_volume(volume_final)

def salvar_config_audio(config_audio):
    """Salva as configurações de áudio no arquivo JSON"""
    with open("saves/config_audio.json", "w") as f:
        json.dump(config_audio, f, indent=4)
