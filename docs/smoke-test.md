# Smoke test manuel

Le dépôt ne contient pas de suite de tests automatisés ni de CI (les premiers
tests sont #85, la CI #78). Cette procédure se passe entièrement **à
l'extérieur du processus** : on part d'un clone neuf, on lance l'application
et on observe ce qu'elle répond et avec quel code de sortie.

À dérouler avant de proposer un changement qui touche au démarrage, à la
configuration, aux dépendances ou au conteneur.

## Conventions selon le système

Les commandes sont données pour **Windows (PowerShell)** puis pour **macOS /
Linux (bash)**. Seules quatre choses changent :

| | Windows (PowerShell) | macOS / Linux (bash) |
|---|---|---|
| Interpréteur de l'environnement virtuel | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Définir une variable pour une commande | `$env:VAR = "x"` puis `Remove-Item Env:VAR` | `VAR=x commande` |
| Lire le code de sortie | `$LASTEXITCODE` | `echo $?` |
| Copier / renommer un fichier | `Copy-Item`, `Rename-Item` | `cp`, `mv` |

Les commandes appellent l'interpréteur **par son chemin** (`.venv\Scripts\python.exe`)
plutôt que d'activer l'environnement : sous Windows, `Activate.ps1` est bloqué
par défaut par la politique d'exécution de PowerShell, et ce n'est pas le sujet
de ce test.

## Vérifications statiques

Identique sur les deux systèmes (une seule ligne, sans continuation) :

```
python -m compileall -q src
git diff --check
```

## 1. Démarrage local, sans credentials

Dans un clone neuf de la branche, sans environnement virtuel. Il faut
[`uv`](https://docs.astral.sh/uv/) : `uv sync` crée `.venv` avec le Python
de `.python-version` (3.12), y installe les versions figées dans `uv.lock`, et
installe le package `oceens` en mode éditable.

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
uv sync
.venv\Scripts\python.exe -m uvicorn oceens.main:app --port 8000
```

Si Windows bloque le `python.exe` de `.venv` créé par uv (« Une stratégie de
contrôle d'application a bloqué ce fichier »), supprimer `.venv`, le recréer
avec l'interpréteur standard, puis relancer `uv sync`, qui le réutilise :

```powershell
& (uv python find 3.12) -m venv .venv
uv sync
```

**macOS / Linux (bash)**

```bash
cp .env.example .env
uv sync
.venv/bin/uvicorn oceens.main:app --port 8000
```

Attendu, sans aucun credential Entra ni clé LLM :

| Route | Réponse |
|---|---|
| `GET /` | 200 |
| `GET /dev/login` | 200 |
| `GET /nope` | 303 vers `/` (middleware 404 → `/`) |

Les logs de démarrage créent les tables, insèrent le jeu de démonstration et
ne contiennent ni erreur ni trace d'exception.

## 1 bis. Démarrage depuis un autre répertoire

L'application ne dépend pas du répertoire courant : templates, fichiers
statiques, CSV du seed, base et `.env` sont trouvés à partir du package. On
relance la même commande depuis un autre dossier, en appelant l'interpréteur
par son chemin absolu. Arrêter d'abord l'instance de l'étape 1.

**Windows (PowerShell)**

```powershell
$repo = (Get-Location).Path
Push-Location $env:TEMP
& "$repo\.venv\Scripts\python.exe" -m uvicorn oceens.main:app --port 8000
Pop-Location
```

**macOS / Linux (bash)**

```bash
repo=$(pwd)
(cd /tmp && "$repo/.venv/bin/uvicorn" oceens.main:app --port 8000)
```

Attendu : les mêmes réponses qu'à l'étape 1, et la même base (pas de nouveau
seed dans les logs). `GET /dev/login` en 200 prouve que le `.env` du dépôt a
été lu : la route n'existe qu'avec `AUTH_MODE=dev`, que seul le `.env` fournit.

## 2. Démarrage avec Docker

Il faut un **démon Docker en cours d'exécution** — Docker Desktop sous Windows
(avec le backend WSL 2) comme sous macOS, le démon natif sous Linux. La
commande est la même partout :

```
docker compose up --build
```

Attendu : l'image se construit, le conteneur démarre sans redémarrer en
boucle, et `/`, `/dev/login` et `/nope` répondent comme à l'étape 1.

Sans `.env`, `docker compose` échoue avec `env file .env not found` — c'est
voulu, la première commande d'un fork est la copie de `.env.example`.

Pour arrêter et nettoyer :

```
docker compose down
```

## 3. Codes de sortie sur configuration invalide

Une configuration de démarrage invalide doit sortir en **code 1**, pour qu'un
superviseur ou une CI voie l'échec.

Le `.env` doit être écarté pour les deux derniers cas : `load_dotenv()` y relirait
`AUTH_MODE=dev` et l'application démarrerait normalement, en code 0.

À lancer depuis la racine du dépôt : avec `python -c`, `load_dotenv()` cherche
le `.env` dans le répertoire courant, et non à partir du package.

**Windows (PowerShell)**

```powershell
# AUTH_MODE invalide
$env:AUTH_MODE = "bogus"
.venv\Scripts\python.exe -c "import oceens.main"; $LASTEXITCODE   # 1
Remove-Item Env:AUTH_MODE

# ENTRA_* manquantes, sans .env
Rename-Item .env .env.bak
'AUTH_MODE','ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
.venv\Scripts\python.exe -c "import oceens.main"; $LASTEXITCODE   # 1

# SECRET_KEY manquante en entra, sans .env
$env:ENTRA_CLIENT_ID = "x"; $env:ENTRA_CLIENT_SECRET = "x"; $env:ENTRA_TENANT_ID = "x"
Remove-Item Env:SECRET_KEY -ErrorAction SilentlyContinue
.venv\Scripts\python.exe -c "import oceens.main"; $LASTEXITCODE   # 1
'ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" }
Rename-Item .env.bak .env
```

**macOS / Linux (bash)**

```bash
# AUTH_MODE invalide
AUTH_MODE=bogus .venv/bin/python -c "import oceens.main"; echo $?   # 1

# ENTRA_* manquantes, sans .env
mv .env .env.bak
env -u AUTH_MODE -u ENTRA_CLIENT_ID -u ENTRA_CLIENT_SECRET -u ENTRA_TENANT_ID \
  .venv/bin/python -c "import oceens.main"; echo $?   # 1

# SECRET_KEY manquante en entra, sans .env
env -u AUTH_MODE -u SECRET_KEY ENTRA_CLIENT_ID=x ENTRA_CLIENT_SECRET=x ENTRA_TENANT_ID=x \
  .venv/bin/python -c "import oceens.main"; echo $?   # 1
mv .env.bak .env
```

Attendu : la ligne de log `INVALID AUTH_MODE 'bogus'` pour le premier cas,
`MISSING ENTRA INFO. Please check .env` pour le deuxième,
`MISSING SECRET_KEY. Required with AUTH_MODE=entra, please check .env` pour le
troisième. En témoin, `AUTH_MODE=dev` sort en 0, même sans `SECRET_KEY`.

## 4. Absence de clé LLM

`.env.example` livre `LLM_API_KEY` **vide** : l'application démarre
normalement, seules les synthèses sont indisponibles. Avec le daemon lancé
(`.venv\Scripts\python.exe -m oceens.summaries_generator_daemon` sous Windows,
`.venv/bin/oceens-summaries` sous macOS / Linux), une demande de synthèse est marquée en
erreur de configuration (`http_status` 500, « variable d'environnement
absente ou vide ») et aucun appel n'est fait au fournisseur.

## 5. Avec une clé LLM

Chaque étudiant récupère sa propre clé sur <https://locallm.mde.epf.fr> en se
connectant avec son compte EPF, puis la renseigne dans son `.env` :

```
LLM_API_KEY=<votre clé>
```

Vérification rapide, sans passer par l'interface. **La clé doit se trouver dans
l'environnement de cette commande, et pas seulement dans le `.env`** :
`load_dotenv()` est appelé par l'application, par le daemon et par le module
d'authentification, mais pas par `src/oceens/services/llm_client.py`, seul module importé
ici. Sans le préfixe ci-dessous, la commande lève `LLMConfigError` quel que
soit le contenu du `.env`.

La ligne `python -c` tient sur une ligne et est identique sur les deux
systèmes ; seuls le chemin de l'interpréteur et la façon de définir la
variable changent.

**Windows (PowerShell)**

```powershell
$env:LLM_API_KEY = "<votre clé>"
.venv\Scripts\python.exe -c "from types import SimpleNamespace; from oceens.services import llm_client as c; p = SimpleNamespace(name='Ollama EPF', api_type='ollama', base_url='https://locallm.mde.epf.fr/ollama', api_key_env='LLM_API_KEY', default_model='gemma4:26b'); print(c.check_model(p, 'gemma4:26b')); print(c.ping_generation(p, 'gemma4:26b'))"
Remove-Item Env:LLM_API_KEY
```

**macOS / Linux (bash)**

```bash
LLM_API_KEY=<votre clé> .venv/bin/python -c "from types import SimpleNamespace; from oceens.services import llm_client as c; p = SimpleNamespace(name='Ollama EPF', api_type='ollama', base_url='https://locallm.mde.epf.fr/ollama', api_key_env='LLM_API_KEY', default_model='gemma4:26b'); print(c.check_model(p, 'gemma4:26b')); print(c.ping_generation(p, 'gemma4:26b'))"
```

Attendu : `True`, puis `(True, None, None)`. `check_model` seul ne suffit pas —
la liste des modèles répond encore normalement avec un compte sans crédit,
seul l'appel de génération le révèle. Avec une valeur vide, ou sans la
variable, la même commande lève `LLMConfigError` : c'est le comportement de
l'étape 4.

Ensuite, bout en bout : demander la génération des synthèses d'un sondage avec
le daemon lancé (commandes de l'étape 4). Cette moitié-là n'a pas besoin du
préfixe : le daemon, lui, lit le `.env`. Les lignes passent de `http_status` 0
à 200, une à la fois (le daemon est séquentiel), et la synthèse s'affiche en
HTML. Ne jamais committer la clé : `.env` est ignoré par Git.

## Ensuite

Tester manuellement les routes concernées par le changement, sur une base
SQLite jetable (jamais une copie de production), avec les rôles et les
statuts de sondage pertinents.
