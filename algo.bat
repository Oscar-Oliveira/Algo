@echo off
setlocal enabledelayedexpansion
rem Arranque do ALGO -- nao precisas de ativar nenhum ambiente virtual a
rem mao. Este script encontra (ou cria, na primeira vez) um venv ao lado
rem dele proprio, instala o pacote la dentro se for preciso, e depois
rem chama o 'algo' de dentro desse venv diretamente.

set "DIR=%~dp0"
rem %~dp0 vem sempre com uma barra invertida no fim (ex: "C:\pasta\").
rem Isso parte quando a metemos entre aspas mesmo antes de outra aspa de
rem fecho ("%DIR%") -- o Windows le "\"" como uma aspa escapada em vez de
rem fechar a string, e o argumento a seguir fica todo trocado. Por isso
rem tiramos essa barra final aqui, uma vez por todas.
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

set "VENV=%DIR%\.venv"

if not exist "%VENV%\Scripts\algo.exe" (
    echo Primeira utilizacao: a preparar o ambiente ^(so demora uns segundos^)...

    where python >nul 2>nul
    if errorlevel 1 (
        where py >nul 2>nul
        if errorlevel 1 (
            echo.
            echo Nao encontrei o Python instalado. Instala o Python 3 ^(python.org^) e tenta outra vez.
            echo Nota: no instalador do Python, marca a opcao "Add python.exe to PATH".
            pause
            exit /b 1
        )
        set "PYTHON=py"
    ) else (
        set "PYTHON=python"
    )

    !PYTHON! -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo Nao foi possivel criar o ambiente virtual ^(comando: !PYTHON! -m venv^).
        rmdir /s /q "%VENV%" 2>nul
        pause
        exit /b 1
    )
    if not exist "%VENV%\Scripts\python.exe" (
        echo.
        echo O comando "!PYTHON!" nao criou mesmo o ambiente virtual.
        echo Isto costuma acontecer quando "!PYTHON!" e so o atalho da Microsoft
        echo Store para instalar o Python, nao o Python instalado a serio.
        echo Instala o Python em https://www.python.org/downloads/ -- no
        echo instalador, marca a opcao para adicionar o Python ao PATH.
        rmdir /s /q "%VENV%" 2>nul
        pause
        exit /b 1
    )

    if not exist "%VENV%\Scripts\pip.exe" (
        echo.
        echo O ambiente virtual foi criado, mas ficou sem o pip la dentro.
        echo Tenta reinstalar o Python a partir de https://www.python.org/downloads/
        rmdir /s /q "%VENV%" 2>nul
        pause
        exit /b 1
    )

    "%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip
    if errorlevel 1 (
        echo.
        echo Nao foi possivel atualizar o pip dentro do ambiente virtual.
        rmdir /s /q "%VENV%" 2>nul
        pause
        exit /b 1
    )

    "%VENV%\Scripts\python.exe" -m pip install --quiet -e "%DIR%"
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar o ALGO ^(pip install -e "%DIR%"^).
        echo Confirma que esta pasta tem mesmo o ficheiro pyproject.toml.
        rmdir /s /q "%VENV%" 2>nul
        pause
        exit /b 1
    )

    echo Ambiente preparado.
    echo.
)

"%VENV%\Scripts\algo.exe" %*

rem Se foi aberto com duplo-clique (sem argumentos, ou seja a consola),
rem a janela fecharia logo a seguir ao 'sair' -- da tempo para ler antes
rem de fechar.
if "%~1"=="" pause
