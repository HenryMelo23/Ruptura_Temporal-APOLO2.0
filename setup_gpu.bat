@echo off
:: ============================================================
:: setup_gpu.bat -- Configura ambiente Python 3.12 + PyTorch CUDA
:: Para: GTX 1650 NVIDIA / Windows / AMD Ryzen 5 4600G
:: ============================================================
chcp 65001 > nul
echo.
echo ============================================================
echo   SETUP GPU -- APOLO LASER TREINO
echo   GTX 1650 + CUDA 12.4 + PyTorch 2.5
echo ============================================================
echo.

:: --- Verifica winget ---------------------------------------------------
winget --version > nul 2>&1
if errorlevel 1 (
    echo [ERRO] winget nao encontrado.
    echo        Abra a Microsoft Store e instale o "App Installer".
    pause
    exit /b 1
)

:: --- Instala Python 3.12 via winget (se necessario) --------------------
echo [1/4] Verificando Python 3.12...
py -3.12 --version > nul 2>&1
if errorlevel 1 (
    echo       Python 3.12 nao encontrado. Instalando via winget...
    winget install --id Python.Python.3.12 -e --source winget --silent
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar Python 3.12.
        echo        Instale manualmente: https://www.python.org/downloads/release/python-3129/
        echo        Marque "Add to PATH" durante a instalacao.
        pause
        exit /b 1
    )
    echo       Python 3.12 instalado!
    :: Atualiza PATH da sessao
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
) else (
    echo       Python 3.12 ja instalado. OK
)

:: --- Cria ambiente virtual .venv312 ------------------------------------
echo.
echo [2/4] Criando ambiente virtual .venv312...
if exist ".venv312" (
    echo       .venv312 ja existe. Pulando criacao.
) else (
    py -3.12 -m venv .venv312
    if errorlevel 1 (
        echo [ERRO] Falha ao criar venv. Verifique se Python 3.12 esta no PATH.
        pause
        exit /b 1
    )
    echo       Ambiente .venv312 criado!
)

:: --- Instala PyTorch CUDA 12.4 -----------------------------------------
echo.
echo [3/4] Instalando PyTorch com CUDA 12.4 (GTX 1650 - Compute 7.5)...
echo       (Download ~2.5GB -- pode demorar varios minutos)
echo.
.venv312\Scripts\pip install torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124 --index-url https://download.pytorch.org/whl/cu124 --quiet
if errorlevel 1 (
    echo.
    echo [AVISO] Falha com CUDA 12.4. Tentando CUDA 12.1...
    .venv312\Scripts\pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121 --quiet
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar PyTorch CUDA.
        echo        Verifique sua conexao com a internet.
        pause
        exit /b 1
    )
)
echo       PyTorch CUDA instalado!

:: --- Instala dependencias extras ---------------------------------------
echo.
echo [4/4] Instalando dependencias extras...
.venv312\Scripts\pip install numpy --quiet
echo       Dependencias instaladas!

:: --- Verifica CUDA ----------------------------------------------------
echo.
echo ============================================================
echo   VERIFICANDO CUDA...
echo ============================================================
.venv312\Scripts\python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NAO DETECTADA'); print('VRAM:', round(torch.cuda.get_device_properties(0).total_memory/1e9,1), 'GB' if torch.cuda.is_available() else '')"

echo.
echo ============================================================
if errorlevel 1 (
    echo   [ERRO] Verificacao falhou! Veja mensagem acima.
) else (
    echo   SETUP CONCLUIDO COM SUCESSO!
    echo.
    echo   Para treinar com a GPU, use:
    echo   .venv312\Scripts\python treino_laser_gpu.py --curriculum --geracoes 3000
    echo.
    echo   Para verificar o ambiente:
    echo   .venv312\Scripts\python treino_laser_gpu.py --verificar
)
echo ============================================================
echo.
pause
