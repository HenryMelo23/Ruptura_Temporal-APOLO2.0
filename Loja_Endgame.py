import pygame, sys, random, collections, math, os, json
from Variaveis import *

INIMIGOS_ELIMINADOS = 3000
MAX_CARTAS = 100
GRID_COLS  = 3
CARTA_W    = 120
CARTA_H    = 148
GAP_X      = 22   # gap horizontal entre cartas
GAP_Y      = 36   # gap vertical (espaço p/ nick)
PAINEL_W   = 175
MARGEM     = 18

CARTAS_DATA = [
    {"nome":"Speed Boost",       "nick":"Vento Celeste",        "cor":(80,200,255),
     "descricao":"+Velocidade e +Dano por carta.",
     "sprites":("Sprites/Deck/Speed_boost1.png","Sprites/Deck/Speed_boost2.png")},
    {"nome":"Porção",            "nick":"Elixir Vital",         "cor":(80,255,130),
     "descricao":"Vida máx +1130, restaura 30% vida e 25% Petro.",
     "sprites":("Sprites/Deck/carta_por1.png","Sprites/Deck/carta_por2.png")},
    {"nome":"Disparo crescente", "nick":"Impacto Escalante",    "cor":(255,110,80),
     "descricao":"+100 de dano por carta.",
     "sprites":("Sprites/Deck/carta_odio1.png","Sprites/Deck/carta_odio2.png")},
    {"nome":"Trembo",            "nick":"Reversão Temporal",    "cor":(200,100,255),
     "descricao":"Segunda vida! Regen mais rápida. Máx 1 cópia.",
     "sprites":("Sprites/Deck/carta_trem1.png","Sprites/Deck/carta_trem2.png")},
    {"nome":"Tempestade",        "nick":"Tempestade Crescente", "cor":(255,220,50),
     "descricao":"+32.5 dano e +3% chance crítica por carta.",
     "sprites":("Sprites/Deck/Carta_tempestade_crescente1.png","Sprites/Deck/Carta_tempestade_crescente2.png")},
    {"nome":"Cura",              "nick":"Mordida Sombria",      "cor":(255,80,150),
     "descricao":"Roubo de vida +0.25 e qtd +0.30 por carta.",
     "sprites":("Sprites/Deck/Carta_roubo_vida1.png","Sprites/Deck/Carta_roubo_vida2.png")},
    {"nome":"Speed Atack",       "nick":"Fluidez Letal",        "cor":(255,160,50),
     "descricao":"Vel. ataque x0.95 por carta (mín 70ms).",
     "sprites":("Sprites/Deck/carta_onda.png","Sprites/Deck/carta_onda2.png")},
    {"nome":"Teleporte",         "nick":"Salto Espacial",       "cor":(100,210,255),
     "descricao":"Cooldown dash x0.89 por carta (mín 0.4s).",
     "sprites":("Sprites/Deck/carta_teleporte1.png","Sprites/Deck/carta_teleporte2.png")},
    {"nome":"Defesa",            "nick":"Escudo Fásico",        "cor":(150,210,100),
     "descricao":"Resistência +13.75 por carta (máx 60).",
     "sprites":("Sprites/Deck/carta_defesa1.png","Sprites/Deck/carta_defesa2.png")},
]

# ── helpers ──────────────────────────────────────────────────────────────
def _frames(sprites):
    return [pygame.transform.scale(pygame.image.load(p).convert_alpha(),(CARTA_W,CARTA_H)) for p in sprites]

def _wrap(f, txt, maxw):
    words,lines,cur = txt.split(),[],""
    for w in words:
        t=(cur+" "+w).strip()
        if f.size(t)[0]<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def _ol(surf,f,txt,fg,ol,x,y,d=2):
    sh=f.render(txt,True,ol)
    for dx,dy in[(-d,0),(d,0),(0,-d),(0,d),(-d,-d),(-d,d),(d,-d),(d,d)]: surf.blit(sh,(x+dx,y+dy))
    surf.blit(f.render(txt,True,fg),(x,y))

def _add(deck,nome,cnt):
    if len(deck)>=MAX_CARTAS: return False
    if nome=="Trembo" and cnt.get("Trembo",0)>=1: return False
    deck.append(nome); return True

def _rm(deck,nome):
    for i in range(len(deck)-1,-1,-1):
        if deck[i]==nome: deck.pop(i); return True
    return False

# ── Apolo UCB (copiado de GAME5_PLAYER) ──────────────────────────────────
def _carregar_pesos():
    arq="saves/memoria_cartas_apolo.json"
    base={n:{"N":1,"W":1} for n in [cd["nome"] for cd in CARTAS_DATA]}
    if os.path.exists(arq):
        try:
            with open(arq,"r") as f: s=json.load(f)
            for k,v in s.items():
                if isinstance(v,dict) and "N" in v: base[k]=v
        except: pass
    return base

def _build_apolo(qtd=100):
    pesos=_carregar_pesos()
    opcoes=list(pesos.keys())
    escolhas=[]
    total_j=sum(v["N"] for v in pesos.values()) or 1
    C=math.sqrt(2)
    for _ in range(qtd):
        validas=[o for o in opcoes if o in [cd["nome"] for cd in CARTAS_DATA]]
        if escolhas.count("Trembo")>=1 and "Trembo" in validas: validas.remove("Trembo")
        if not validas: break
        best,bv=None,-float('inf')
        for op in validas:
            n=pesos.get(op,{"N":1,"W":1})
            ni,wi=n["N"],n["W"]
            ucb=(wi/ni)+C*math.sqrt(math.log(total_j)/ni) if ni>0 else float('inf')
            if ucb>bv: bv=ucb; best=op
        if best: escolhas.append(best)
    return escolhas

def _build_random(qtd=100):
    deck=[]
    nomes=[cd["nome"] for cd in CARTAS_DATA]
    cnt=collections.Counter()
    for _ in range(qtd):
        opts=[n for n in nomes if not(n=="Trembo" and cnt["Trembo"]>=1)]
        if not opts: break
        c=random.choice(opts); deck.append(c); cnt[c]+=1
    return deck

# ── TELA PRINCIPAL ────────────────────────────────────────────────────────
def tela_loja_endgame():
    pygame.init()
    W,H=largura_mapa,altura_mapa
    tela=pygame.display.set_mode((W,H))
    pygame.display.set_caption("Loja da Ruptura — Monte sua Build")
    clock=pygame.time.Clock()

    try:
        bg=pygame.transform.scale(pygame.image.load("Sprites/Cartas_back.png").convert(),(W,H))
    except:
        bg=pygame.Surface((W,H)); bg.fill((15,10,30))
    dim=pygame.Surface((W,H),pygame.SRCALPHA); dim.fill((0,0,0,145))

    frs=[_frames(cd["sprites"]) for cd in CARTAS_DATA]

    fT=pygame.font.Font(None,42)
    fN=pygame.font.Font(None,22)
    fI=pygame.font.Font(None,20)
    fB=pygame.font.Font(None,34)
    fM=pygame.font.Font(None,17)
    fQ=pygame.font.Font(None,28)
    fC=pygame.font.Font(None,44)

    # layout
    grid_w=GRID_COLS*CARTA_W+(GRID_COLS-1)*GAP_X
    grid_h=3*CARTA_H+2*GAP_Y
    bloco=grid_w+MARGEM+PAINEL_W
    gx0=(W-bloco)//2
    gy0=112

    px=gx0+grid_w+MARGEM
    py=gy0
    ph=grid_h

    # botões na parte inferior
    BOT_Y=gy0+grid_h+14
    BW,BH=175,42
    GAP_B=12
    total_bw=3*BW+2*GAP_B
    bx0=(W-total_bw)//2

    btn_apolo =pygame.Rect(bx0,          BOT_Y,BW,BH)
    btn_rand  =pygame.Rect(bx0+BW+GAP_B, BOT_Y,BW,BH)
    btn_start =pygame.Rect(bx0+2*(BW+GAP_B),BOT_Y,BW,BH)

    # estado
    deck=[]; sel=0; fanim=0; tanim=0
    hover_idx=-1; hover_start=0; TIPDELAY=3000
    hold_ativo=False; hold_nome=""; hold_start=0; last_aa=0
    mouse_held=False
    HOLD_TH=1800; AUTO_IV=85

    flash_msg=""; flash_t=0; FLASH_DUR=2000

    running=True
    while running:
        dt=clock.tick(60)
        now=pygame.time.get_ticks()
        tanim+=dt
        if tanim>=500: tanim=0; fanim=1-fanim

        cnt=collections.Counter(deck)
        total=len(deck)
        nome_sel=CARTAS_DATA[sel]["nome"]

        # auto-add hold
        if hold_ativo and total<MAX_CARTAS:
            if now-hold_start>=HOLD_TH and now-last_aa>=AUTO_IV:
                _add(deck,hold_nome,cnt); cnt=collections.Counter(deck); total=len(deck); last_aa=now

        # cancelar hold do mouse se saiu da carta
        if mouse_held:
            if hover_idx<0 or CARTAS_DATA[hover_idx]["nome"]!=hold_nome:
                mouse_held=False
                if not pygame.mouse.get_pressed()[0]: hold_ativo=False

        mx,my=pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()

            elif ev.type==pygame.KEYDOWN:
                if ev.key in(pygame.K_d,pygame.K_RIGHT): sel=(sel+1)%len(CARTAS_DATA)
                elif ev.key in(pygame.K_a,pygame.K_LEFT): sel=(sel-1)%len(CARTAS_DATA)
                elif ev.key in(pygame.K_s,pygame.K_DOWN): sel=(sel+GRID_COLS)%len(CARTAS_DATA)
                elif ev.key in(pygame.K_w,pygame.K_UP): sel=(sel-GRID_COLS)%len(CARTAS_DATA)
                elif ev.key==pygame.K_SPACE:
                    if _add(deck,nome_sel,cnt):
                        hold_ativo=True; hold_nome=nome_sel; hold_start=now; last_aa=now
                elif ev.key==pygame.K_q: _rm(deck,nome_sel)
                elif ev.key==pygame.K_BACKSPACE:
                    if deck: deck.pop()
                elif ev.key in(pygame.K_RETURN,pygame.K_KP_ENTER):
                    if total>0: running=False
                elif ev.key==pygame.K_r:      # Apolo
                    deck=_build_apolo(100); flash_msg="✦ Build Apolo carregada!"; flash_t=now
                elif ev.key==pygame.K_t:      # Aleatório
                    deck=_build_random(100); flash_msg="🎲 Build Aleatória carregada!"; flash_t=now

            elif ev.type==pygame.KEYUP:
                if ev.key==pygame.K_SPACE and not mouse_held: hold_ativo=False

            elif ev.type==pygame.MOUSEBUTTONDOWN:
                if ev.button==1:
                    # cartas
                    for i,cd in enumerate(CARTAS_DATA):
                        col,row=i%GRID_COLS,i//GRID_COLS
                        cx=gx0+col*(CARTA_W+GAP_X); cy=gy0+row*(CARTA_H+GAP_Y)
                        if pygame.Rect(cx,cy,CARTA_W,CARTA_H).collidepoint(mx,my):
                            sel=i
                            if _add(deck,cd["nome"],cnt):
                                mouse_held=True; hold_ativo=True; hold_nome=cd["nome"]; hold_start=now; last_aa=now
                    # botões
                    if btn_apolo.collidepoint(mx,my):
                        deck=_build_apolo(100); flash_msg="✦ Build Apolo carregada!"; flash_t=now
                    elif btn_rand.collidepoint(mx,my):
                        deck=_build_random(100); flash_msg="🎲 Build Aleatória carregada!"; flash_t=now
                    elif btn_start.collidepoint(mx,my) and total>0: running=False
                elif ev.button==3:
                    for i,cd in enumerate(CARTAS_DATA):
                        col,row=i%GRID_COLS,i//GRID_COLS
                        cx=gx0+col*(CARTA_W+GAP_X); cy=gy0+row*(CARTA_H+GAP_Y)
                        if pygame.Rect(cx,cy,CARTA_W,CARTA_H).collidepoint(mx,my): _rm(deck,cd["nome"])

            elif ev.type==pygame.MOUSEBUTTONUP:
                if ev.button==1: mouse_held=False; hold_ativo=False

        # hover
        nh=-1
        for i in range(len(CARTAS_DATA)):
            col,row=i%GRID_COLS,i//GRID_COLS
            if pygame.Rect(gx0+col*(CARTA_W+GAP_X),gy0+row*(CARTA_H+GAP_Y),CARTA_W,CARTA_H).collidepoint(mx,my):
                nh=i; break
        if nh!=hover_idx: hover_idx=nh; hover_start=now
        show_tip=hover_idx>=0 and now-hover_start>=TIPDELAY

        # ── RENDER ──────────────────────────────────────────────────────
        tela.blit(bg,(0,0)); tela.blit(dim,(0,0))

        # título
        tt="MONTE SUA BUILD"
        _ol(tela,fT,tt,(255,215,50),(0,0,0),W//2-fT.size(tt)[0]//2,10)

        # contador + barra
        frac=total/MAX_CARTAS
        cc=(80,255,120) if frac<0.6 else(255,200,50) if frac<0.9 else(255,80,80)
        ct=f"{total} / {MAX_CARTAS}"
        _ol(tela,fC,ct,cc,(0,0,0),W//2-fC.size(ct)[0]//2,50)
        BRW=340; brx=W//2-BRW//2; bry=96
        pygame.draw.rect(tela,(40,40,40),(brx,bry,BRW,8),border_radius=4)
        if frac>0: pygame.draw.rect(tela,cc,(brx,bry,int(BRW*frac),8),border_radius=4)
        pygame.draw.rect(tela,(160,160,160),(brx,bry,BRW,8),1,border_radius=4)

        # grid
        for i,cd in enumerate(CARTAS_DATA):
            col,row=i%GRID_COLS,i//GRID_COLS
            cx=gx0+col*(CARTA_W+GAP_X); cy=gy0+row*(CARTA_H+GAP_Y)
            is_sel=(i==sel)
            esc=1.09 if is_sel else 1.0
            cw2,ch2=int(CARTA_W*esc),int(CARTA_H*esc)
            ox,oy=(cw2-CARTA_W)//2,(ch2-CARTA_H)//2
            tela.blit(pygame.transform.scale(frs[i][fanim],(cw2,ch2)),(cx-ox,cy-oy))
            if is_sel:
                pygame.draw.rect(tela,(255,200,0),(cx-ox-2,cy-oy-2,cw2+4,ch2+4),3,border_radius=3)

            # badge qtd
            q=cnt.get(cd["nome"],0)
            if q>0:
                qs=fQ.render(f"×{q}",True,(255,240,80))
                bgs=pygame.Surface((qs.get_width()+5,qs.get_height()+2),pygame.SRCALPHA)
                bgs.fill((0,0,0,175)); tela.blit(bgs,(cx+CARTA_W-qs.get_width()-7,cy+CARTA_H-qs.get_height()-4))
                tela.blit(qs,(cx+CARTA_W-qs.get_width()-5,cy+CARTA_H-qs.get_height()-3))

            # nick — centralizado no gap abaixo
            ns=fN.render(cd["nick"],True,cd["cor"])
            tela.blit(ns,(cx+CARTA_W//2-ns.get_width()//2, cy+CARTA_H+5))

        # painel lateral
        ps=pygame.Surface((PAINEL_W,ph),pygame.SRCALPHA); ps.fill((8,8,22,215))
        pygame.draw.rect(ps,(90,70,180),(0,0,PAINEL_W,ph),2,border_radius=8)
        tela.blit(ps,(px,py))
        _ol(tela,fN,"SEU DECK",(200,180,255),(0,0,0),px+10,py+8)
        ly=py+32
        if total==0:
            tela.blit(fM.render("Nenhuma carta ainda",True,(110,110,140)),(px+10,ly))
        else:
            for cd in CARTAS_DATA:
                q=cnt.get(cd["nome"],0)
                if not q: continue
                tela.blit(fM.render(cd["nome"][:18],True,cd["cor"]),(px+8,ly))
                qs=fM.render(f"×{q}",True,(255,240,100))
                tela.blit(qs,(px+PAINEL_W-qs.get_width()-8,ly))
                ly+=19
                if ly>py+ph-12: break

        # tooltip
        if show_tip:
            cd=CARTAS_DATA[hover_idx]
            col2,row2=hover_idx%GRID_COLS,hover_idx//GRID_COLS
            tcx=gx0+col2*(CARTA_W+GAP_X); tcy=gy0+row2*(CARTA_H+GAP_Y)
            TW=210; lines=_wrap(fI,cd["descricao"],TW-12); TH=12+len(lines)*17+8
            tx=tcx+CARTA_W+6
            if tx+TW>W-8: tx=tcx-TW-6
            ty=min(tcy,H-TH-8)
            ts=pygame.Surface((TW,TH),pygame.SRCALPHA); ts.fill((10,10,28,240))
            pygame.draw.rect(ts,cd["cor"],(0,0,TW,TH),2,border_radius=5)
            _ol(ts,fI,cd["nick"],cd["cor"],(0,0,0),6,5)
            for li,ln in enumerate(lines): ts.blit(fI.render(ln,True,(210,210,210)),(6,20+li*17))
            tela.blit(ts,(tx,ty))

        # flash message
        if flash_msg and now-flash_t<FLASH_DUR:
            alpha=255 if now-flash_t<1400 else int(255*(1-(now-flash_t-1400)/600))
            fs=fB.render(flash_msg,True,(255,230,80))
            fsurf=pygame.Surface((fs.get_width()+20,fs.get_height()+10),pygame.SRCALPHA)
            fsurf.fill((0,0,0,int(180*alpha/255)))
            fsurf.blit(fs,(10,5))
            tela.blit(fsurf,(W//2-fsurf.get_width()//2, BOT_Y-50))

        # ── botões inferiores ────────────────────────────────────────────
        def draw_btn(rect,label,sub,cor_main,cor_borda,ativo=True):
            hov=rect.collidepoint(mx,my) and ativo
            c=tuple(min(255,v+25) for v in cor_main) if hov else cor_main if ativo else (60,60,60)
            pygame.draw.rect(tela,c,rect,border_radius=8)
            pygame.draw.rect(tela,cor_borda if ativo else(100,100,100),rect,2,border_radius=8)
            ls=fB.render(label,True,(255,255,255) if ativo else(130,130,130))
            tela.blit(ls,(rect.centerx-ls.get_width()//2,rect.centery-ls.get_height()//2-5))
            ss=fM.render(sub,True,(200,200,200) if ativo else(100,100,100))
            tela.blit(ss,(rect.centerx-ss.get_width()//2,rect.bottom-15))

        draw_btn(btn_apolo,"⭐ Apolo IA","[R] Recomendação",(60,40,120),(160,120,255))
        draw_btn(btn_rand, "🎲 Aleatório","[T] 100 cartas",(40,80,120),(80,180,255))
        draw_btn(btn_start,"▶ INICIAR","[ENTER]",(40,160,70) if total>0 else(50,50,50),(100,255,120),total>0)

        # aviso Trembo
        if nome_sel=="Trembo" and cnt.get("Trembo",0)>=1:
            av=fI.render("⚠ Trembo: máximo 1 cópia",True,(255,100,80))
            tela.blit(av,(W//2-av.get_width()//2,BOT_Y+BH+6))

        # hints
        h="[A/D/W/S] Navegar  [ESPAÇO/Mouse] Adicionar  [Dir/Q] Remove 1  [R] Apolo  [T] Random  [ENTER] Iniciar"
        hs=fM.render(h,True,(130,130,160))
        tela.blit(hs,(W//2-hs.get_width()//2,H-18))

        pygame.display.flip()

    return deck


# ── aplicação do balanceamento ────────────────────────────────────────────
def aplicar_deck_endgame(deck, v):
    IE=INIMIGOS_ELIMINADOS
    for k,d in[("multiplicador_dano_umbra",1.0),("reducao_cooldown_umbra",1.0),
               ("resistencia_umbra",0.0),("bonus_cura_sifon",0.0)]: v.setdefault(k,d)

    for carta in deck:
        if carta=="Speed Boost":
            v["velocidade_personagem"]+=0.09+(IE//200)*0.002; v["dano_person_hit"]+=10+(IE//50)*1.0
        elif carta=="Porção":
            av=650+(IE//50)*8; v["vida_maxima"]+=av; v["vida"]+=int(v["vida_maxima"]*0.30)
            v["vida_petro"]+=int(v["vida_maxima_petro"]*0.25)
            if v["vida_petro"]>v["vida_maxima_petro"]: v["vida_maxima_petro"]=v["vida_petro"]
        elif carta=="Disparo crescente": v["dano_person_hit"]+=10+(IE//50)*1.5
        elif carta=="Trembo":
            v["trembo"]=True; v["Tempo_cura"]=max(500,int(v["Tempo_cura"]*0.85))
            v["porcentagem_cura"]+=0.005+(IE//400)*0.001
        elif carta=="Tempestade":
            v["dano_person_hit"]+=2.5+(IE//100)*1; v["chance_critico"]+=0.01+(IE//300)*0.002
        elif carta=="Cura":
            v["roubo_de_vida"]+=0.25+(IE//500)*0.001; v["quantidade_roubo_vida"]+=0.30+(IE//500)*0.001
        elif carta=="Speed Atack": v["intervalo_disparo"]=max(70,int(v["intervalo_disparo"]*0.95))
        elif carta=="Teleporte":
            r=0.95-min(0.15,(IE//1000)*0.02); v["tempo_cooldown_dash"]=max(0.4,v["tempo_cooldown_dash"]*r)
        elif carta=="Defesa": v["Resistencia"]=min(60,v["Resistencia"]+10+(IE//200)*0.25)

    aps=1000/max(50,v["intervalo_disparo"]); mc=1+v["chance_critico"]*2.0
    dps=min(v["dano_person_hit"]*aps*mc,1200)
    v["vida_maxima_umbra"]=int(25000+dps*24+IE*25)

    qtd_u=len(deck)//3
    CU=["Essência Obscura","Projétil Devastador","Frenesi Temporal","Armadura de Matéria Escura","Sifão Aprimorado"]
    reg=[]
    for _ in range(qtd_u):
        cu=random.choice(CU); reg.append(cu)
        if cu=="Essência Obscura": v["vida_maxima_umbra"]=int(v["vida_maxima_umbra"]*1.25)
        elif cu=="Projétil Devastador": v["multiplicador_dano_umbra"]+=0.05+(IE//500)*0.005
        elif cu=="Frenesi Temporal": v["reducao_cooldown_umbra"]*=0.92
        elif cu=="Armadura de Matéria Escura": v["resistencia_umbra"]+=2.5
        elif cu=="Sifão Aprimorado": v["bonus_cura_sifon"]+=0.05

    v["vida"]=v["vida_maxima"]; v["vida_umbra"]=v["vida_maxima_umbra"]
    print(f"\n[ LOJA ] {len(deck)} cartas | Umbra {qtd_u} cartas")
    for c,q in sorted(collections.Counter(deck).items(),key=lambda x:x[1],reverse=True): print(f"  [{q}x] {c}")
    print("="*50)
    return v
