import Caminhos
import json
import pygame

_som_max_volumes = {}

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

def aplicar_volume_som(som, config_audio=None, canal="efeitos", volume_maximo=1.0):
    """Aplica o volume configurado a um som específico"""
    if config_audio is None:
        config_audio = carregar_config_audio()
    
    volume_master = config_audio.get("volume_master", 1.0)
    chave_volume = "volume_musica" if canal == "musica" else "volume_efeitos"
    volume_canal = config_audio.get(chave_volume, 0.5)
    
    # Calcula o volume final
    volume_final = volume_canal * volume_master * volume_maximo
    som.set_volume(volume_final)
    
    # Armazena o volume máximo no dicionário para atualizações dinâmicas
    _som_max_volumes[id(som)] = volume_maximo
    
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

def atualizar_sons_do_jogo(config_audio=None):
    """Aplica o volume de música e atualiza todos os objetos Sound ativos no jogo."""
    import sys
    if config_audio is None:
        config_audio = carregar_config_audio()
    
    # 1. Aplicar volume da música
    aplicar_volume_musica(config_audio)
    
    # 2. Atualizar todos os objetos Sound definidos nos módulos do jogo
    for mod_name, mod in list(sys.modules.items()):
        if mod_name.startswith("GAME") or mod_name in ["__main__", "sons_procedurais", "Ruptura_Temporal", "Tela_Pause", "Tela_Cartas", "Tela_Cartas_Coop"]:
            for attr_name in dir(mod):
                try:
                    val = getattr(mod, attr_name)
                    if isinstance(val, pygame.mixer.Sound):
                        nome = attr_name.lower()
                        canal = "musica" if nome.startswith("musica_") or nome.startswith("som_tema") or "tema" in nome else "efeitos"
                        vol_max = _som_max_volumes.get(id(val), 1.0)
                        aplicar_volume_som(val, config_audio, canal=canal, volume_maximo=vol_max)
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, pygame.mixer.Sound):
                                vol_max = _som_max_volumes.get(id(item), 1.0)
                                aplicar_volume_som(item, config_audio, canal="efeitos", volume_maximo=vol_max)
                except Exception:
                    pass

