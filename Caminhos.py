import builtins
import os
import shutil
import json
import hashlib
from pathlib import Path
from qa_logger import registrar_erro

# Garantir que o redirecionamento ocorra apenas uma vez
if not hasattr(builtins, "_saves_redirected"):
    builtins._saves_redirected = True
    
    # Salvar referências originais do sistema
    _original_open = builtins.open
    _original_exists = os.path.exists
    _original_remove = os.remove
    _original_unlink = getattr(os, 'unlink', None)

    def obter_diretorio_documentos():
        home = Path.home()
        # Tenta a pasta Documents (padrão do Windows)
        docs = home / "Documents"
        if docs.exists():
            return docs
        # Tenta em português caso aplicável
        docs_pt = home / "Documentos"
        if docs_pt.exists():
            return docs_pt
        # Fallback seguro para o diretório de usuário
        return home

    def obter_pasta_saves():
        pasta = obter_diretorio_documentos() / "Ruptura_Temporal_Cofre_Dimensional"
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta

    def redirecionar_caminho(caminho):
        if not isinstance(caminho, str):
            return caminho
            
        # Normalizar separadores de caminho
        caminho_norm = caminho.replace("\\", "/")
        
        # Verifica se aponta para a pasta local 'saves'
        if caminho_norm.startswith("saves/") or "/saves/" in caminho_norm:
            nome_arquivo = os.path.basename(caminho_norm)
            
            # Arquivos de IA / Memória que devem permanecer no diretório local do jogo
            ia_files = [
                "apolo_memoria_dqn.pt",
                "memoria_cartas_apolo.json",
                "historico_batalhas.json",
                "memoria_umbra_dqn.pt",
                "apolo_memoria_dqn_backup",
                "apolo_arq.json",
                "tendencias_umbra.json"
            ]
            
            # Se for arquivo de IA, mantém o caminho original na pasta local
            if any(ia in nome_arquivo for ia in ia_files):
                return caminho
                
            # Caso contrário, redireciona para a pasta em Documentos
            pasta_cofre = obter_pasta_saves()
            caminho_final = pasta_cofre / nome_arquivo
            
            # Migração automática: se o arquivo já existir na pasta local antiga,
            # copia o conteúdo para o novo diretório em Documentos
            caminho_antigo_local = os.path.join("saves", nome_arquivo)
            if not caminho_final.exists() and _original_exists(caminho_antigo_local):
                try:
                    pasta_cofre.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(caminho_antigo_local, caminho_final)
                except Exception as e:
                    registrar_erro(f"Cofre Dimensional: erro ao migrar {nome_arquivo}", e)
                    
            return str(caminho_final)
            
        return caminho

    def inicializar_cofre():
        pasta_cofre = obter_pasta_saves()
        
        # Gera o hash dinâmico do upgrade de aureas padrão para a assinatura
        upgrades_default = {"Racional": 0, "Impulsiva": 0, "Devota": 0, "Vanguarda": 0, "Insana": 0}
        upgrades_str = json.dumps(upgrades_default, sort_keys=True)
        hash_val = hashlib.sha256(upgrades_str.encode()).hexdigest()
        
        # Padrões para cada arquivo de configuração e save pessoal
        defaults = {
            "nome_jogador.json": {"nome": "Apolo"},
            "aurea_selecionada.json": {"aurea": "Racional"},
            "aureas_upgrade.json": {
                "upgrades": upgrades_default,
                "assinatura": hash_val
            },
            "config_audio.json": {
                "volume_musica": 0.5,
                "volume_efeitos": 0.5,
                "volume_master": 1.0
            },
            "config_graficos.json": {
                "sombras_ativas": "dinamicas",
                "qualidade_grafica": "alta",
                "nivel_detalhes": "alto",
                "particulas_ativas": True,
                "efeitos_visuais": True,
                "fps_limite": 60,
                "tela_cheia": False
            },
            "config_teclas.json": {
                "Mover para cima": 119, # pygame.K_w
                "Mover para baixo": 115, # pygame.K_s
                "Mover para esquerda": 97, # pygame.K_a
                "Mover para direita": 100, # pygame.K_d
                "Teleporte": 304, # pygame.K_LSHIFT
                "Comprar na loja": 101, # pygame.K_e
                "Habilidade Onda": "MOUSE_3"
            },
            "config_teleporte.json": {"modo": "fixo"},
            "modo_jogo.json": {"modo": "offline", "ip": None},
            "trailer_config.json": {"trailer_assistido": False},
            "tutorial_config.json": {"mostrar_tutorial": True}
        }
        
        for nome_arquivo, default_data in defaults.items():
            caminho_final = pasta_cofre / nome_arquivo
            caminho_antigo_local = os.path.join("saves", nome_arquivo)
            
            # Se o arquivo já existe na pasta de documentos, não faz nada
            if caminho_final.exists():
                continue
                
            # Se existe na pasta antiga local, tenta migrar primeiro
            if _original_exists(caminho_antigo_local):
                try:
                    shutil.copy2(caminho_antigo_local, caminho_final)
                except Exception as e:
                    registrar_erro(f"Cofre Dimensional: erro ao migrar {nome_arquivo}", e)
            else:
                # Se não existe em nenhum lugar, cria o arquivo com as configurações padrão
                try:
                    with _original_open(caminho_final, "w") as f:
                        json.dump(default_data, f, indent=4)
                except Exception as e:
                    registrar_erro(f"Cofre Dimensional: erro ao criar padrao para {nome_arquivo}", e)

    # Executa a inicialização de padrões/migração ao carregar o módulo
    try:
        inicializar_cofre()
    except Exception as e:
        registrar_erro("Cofre Dimensional: erro critico na inicializacao", e)

    # Funções patcheadas
    def patched_open(file, *args, **kwargs):
        file = redirecionar_caminho(file)
        return _original_open(file, *args, **kwargs)

    def patched_exists(path):
        path = redirecionar_caminho(path)
        return _original_exists(path)

    def patched_remove(path):
        path = redirecionar_caminho(path)
        return _original_remove(path)

    # Aplicar os patches globalmente no builtins e no os
    builtins.open = patched_open
    os.path.exists = patched_exists
    os.remove = patched_remove
    if _original_unlink:
        os.unlink = patched_remove
        
    # Patchear também NT/POSIX path helper para maior segurança
    if hasattr(os.path, 'exists'):
        os.path.exists = patched_exists
