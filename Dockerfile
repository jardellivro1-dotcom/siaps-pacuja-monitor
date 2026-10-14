# Imagem base leve e segura
FROM python:3.12-slim

# Evita geração de bytecode e garante flush imediato de logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_ENV=production

WORKDIR /app

# Instala dependências de compilação mínimas e limpa o cache do apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python fixadas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Cria usuário não-root por segurança
RUN useradd -u 1000 -m appuser \
    && chown -R appuser:appuser /app

USER appuser

# Inicializa banco de dados se necessário
RUN python -c "from siaps.models import init_db; from pathlib import Path; init_db(Path('data/siaps_monitor.db'))"

# Verificação de saúde nativa do container
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

EXPOSE 5000

# Execução com Gunicorn WSGI de produção
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
