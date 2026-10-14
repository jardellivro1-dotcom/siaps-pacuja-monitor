"""
Entrypoint serverless WSGI oficial para Vercel.
Importa a instância da aplicação Flask com roteamento para /tmp.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path do Python
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Sinaliza para a aplicação que está rodando em ambiente Vercel
os.environ["VERCEL"] = "1"

from app import app
