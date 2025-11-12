#!/usr/bin/env bash
# build.sh
# Script de build para o Render (ou qualquer servidor Linux)

# Para de executar se algum comando falhar
set -e

# 1. Atualiza o pip
pip install --upgrade pip

# 2. Instala todas as bibliotecas do requirements.txt
pip install -r requirements.txt