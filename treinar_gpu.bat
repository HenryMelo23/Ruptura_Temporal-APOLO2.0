@echo off
:: treinar_gpu.bat -- Atalho para rodar o treino GPU
:: Uso: Duplo clique ou: treinar_gpu.bat [--curriculum] [--geracoes 3000]
chcp 65001 > nul

if not exist ".venv312\Scripts\python.exe" (
    echo [ERRO] Ambiente GPU nao configurado!
    echo        Execute setup_gpu.bat primeiro.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   APOLO LASER TREINO GPU  -  GTX 1650
echo ============================================================
echo.

:: Passa todos os argumentos da linha de comando para o script Python
.venv312\Scripts\python treino_laser_gpu.py --limpar --curriculum --geracoes 5000 --salvar 200 %*

echo.
echo Treino finalizado! Pressione qualquer tecla para sair.
pause
