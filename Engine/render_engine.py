import pygame

class MotorRenderizacao:
    _sombra_sprite_cache = {}

    @classmethod
    def obter_sombra_sprite(cls, imagem, squish_y=0.35, cor=(0, 0, 0, 110)):
        if imagem is None:
            return None
        
        # Utilizamos o id(imagem) para criar o cache. Os sprites carregados de imagem são persistentes.
        chave = (id(imagem), squish_y, cor)
        
        sombra = cls._sombra_sprite_cache.get(chave)
        if sombra is not None:
            return sombra
        
        try:
            # Cria a máscara extraindo apenas pixels não transparentes
            mask = pygame.mask.from_surface(imagem)
            sombra_original = mask.to_surface(setcolor=cor, unsetcolor=(0, 0, 0, 0))
            
            w, h = sombra_original.get_size()
            novo_w = w
            novo_h = max(1, int(h * squish_y))
            
            # Escala e inverte no Y se quisermos que a sombra aponte "para trás" (chão), 
            # mas o achatamento sem flip costuma ser visualmente aceito em top-downs.
            # Aqui vamos aplicar flip vertical para fazer uma sombra de "projeção no chão".
            sombra_flip = pygame.transform.flip(sombra_original, False, True)
            sombra_escalada = pygame.transform.scale(sombra_flip, (novo_w, novo_h))
            
            # Otimização para limpar memória
            if len(cls._sombra_sprite_cache) > 2000:
                cls._sombra_sprite_cache.clear()
                
            cls._sombra_sprite_cache[chave] = sombra_escalada
            return sombra_escalada
        except Exception as e:
            # Em caso de qualquer problema de superfície não compatível com máscara
            return None

    @classmethod
    def desenhar_sombra_dinamica_sprite(cls, tela, imagem, x, y, largura, altura, modo_sombra="dinamicas", offset_y=5):
        if modo_sombra == "desativadas":
            return False
            
        if imagem is None or modo_sombra == "simples":
            return False

        sombra = cls.obter_sombra_sprite(imagem)
        if sombra:
            s_w, s_h = sombra.get_size()
            
            # A sombra de flip e squish deve começar no "pé" do personagem e apontar pra baixo.
            # y + altura = pé do personagem.
            pos_x = x + (largura - s_w) // 2
            pos_y = y + altura - offset_y - 2 # Apenas cola no chão
            
            tela.blit(sombra, (pos_x, pos_y))
            return True
        return False
