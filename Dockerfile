FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    LOCAL_DATABASE_DIR=/app/database

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dépendances seules, depuis le lockfile : couche réutilisée tant que uv.lock ne change pas
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-install-project

# Package oceens (code, templates, static, import), installé en éditable dans /app/.venv
COPY src ./src
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"


# Le répertoire database/ est créé automatiquement par database.py au démarrage.
# Monter /app/database comme volume pour persister la base SQLite entre les redémarrages.
# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.

CMD ["uvicorn", "oceens.main:app", "--host", "0.0.0.0", "--port", "8000"]
