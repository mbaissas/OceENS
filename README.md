# OcéEns II

Course evaluation platform built for the EPF engineering school.

## Overview

**OcéEns II** lets program managers, facilitators, campus directors and administrators create and manage course evaluation surveys (*sondages*) for EPF's programs, and lets students answer them. Answers can be exported, visualised, and summarised by an LLM (*synthèses*). The interface uses EPF's official visual identity.

> Code, issues, ADRs and documentation are in English. Product vocabulary stays in French where it names something users see (*sondage*, *synthèse*, *verbatim*…).

### Tech stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth 2.0 / MSAL, Microsoft Graph; a development sign-in without an identity provider (`AUTH_MODE=dev`) |
| **Database** | SQLite (via SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Logging** | Standard Python `logging` module, through the Uvicorn handlers |
| **Exports** | Pandas (CSV) |
| **Verbatim summaries** | Separate daemon calling an LLM (`requests-cache`, `markdown-it-py`) |

---

## Roles

- `student`: answers the surveys they are enrolled in (a user with no role row is a student).
- `program_manager:<code>`: manages the surveys of their program(s).
- `facilitator:<code>`: runs the surveys of their program(s).
- `campus_manager:<campus>`: campus-wide scope.
- `admin`: general administration.

A user can hold several roles, each with its own scope (program codes or campuses separated by `;`).

---

## Main pages and routes

| Route | Description |
|-------|-------------|
| `/` | Home, authentication hub. |
| `/login`, `/auth/callback`, `/logout` | Microsoft Entra ID authentication flow. |
| `/dev/login` | Development sign-in: user picker on `GET`, sign-in on `POST` (only with `AUTH_MODE=dev`, see [Development sign-in](#development-sign-in)). |
| `/dashboard/student` | Student dashboard. |
| `/dashboard/program-manager` | Program manager dashboard. |
| `/dashboard/facilitator` | Facilitator dashboard. |
| `/dashboard/campus-manager` | Campus director dashboard. |
| `/dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by year / semester / program. Available to `campus_manager` and `program_manager`, scoped to each one's perimeter. |
| `/dashboard/admin` | Administrator dashboard. |
| `/dashboard/survey-create` | Survey creation and settings. |
| `/api/surveys/{survey_id}` | Questionnaire (answering a survey). |
| `/api/surveys/{survey_id}/status` | Survey status change. |
| `/api/surveys/{survey_id}/students` | Students enrolled in a survey. |
| `/api/surveys/{survey_id}/export` | CSV export of the answers. |
| `/api/surveys/{survey_id}/visualisation` | Answers visualisation. Accepts `?teacher=<name>` to open pre-filtered on a teacher. |
| `/api/surveys/{survey_id}/generate-summaries` | Queues LLM summaries for a closed survey. |
| `/api/surveys/{survey_id}/destroy-summaries` | Deletes the generated summaries. |
| `/api/users/{user_id}/role` | Changes a user's role. |
| `/backend/prompts` | LLM prompts list (admin only). |
| `/backend/prompts/new` | Prompt creation form. |
| `/backend/prompts/{id}/edit` | Prompt edit form. |
| `/api/prompts` | Creates a prompt (POST, form). |
| `/api/prompts/{id}` | Updates a prompt (PUT, fetch). Refused if the prompt is referenced in `summaries`. |
| `/api/prompts/{id}/delete` | Deletes a prompt (POST, form). Refused if the prompt is referenced in `summaries`. |

---

## Getting started

The full procedure, with the expected result of every step on Windows (PowerShell) and macOS / Linux (bash), is [`docs/smoke-test.md`](docs/smoke-test.md). It is the reference: this README does not repeat its commands.

### Prerequisites

- Python 3.12. If your `python` is another version (Anaconda, 3.13+…), [`uv`](https://docs.astral.sh/uv/) can fetch it: `uv venv --python 3.12 .venv`.
- Docker, to run the container (Docker Desktop with the WSL 2 backend on Windows).

### First start of a fork

1. Copy the configuration: `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`).

   `.env.example` ships `AUTH_MODE=dev`, so the application starts **without any Entra credential or LLM key** (see [Configuration](#configuration)). Without `.env`, `docker compose up` fails with `env file .env not found`: that is on purpose, the first command in a fork is this copy.

2. Start it, either way:
   - **Docker**: `docker compose up --build`
   - **Locally**: create `.venv` with Python 3.12, install `requirements.txt` into it, then run `uvicorn main:app --port 8000` from the repository root (exact commands per system in the smoke test).

3. Open **http://localhost:8000**. Type `http://` explicitly: some browsers upgrade `localhost` to `https://`, which Uvicorn answers with `Invalid HTTP request received`.

On first start the SQLite database is created and filled with the demo data set (users, four surveys and their answers), in `./database/` by default; set `LOCAL_DATABASE_DIR` to put it elsewhere. The demo data is only inserted into an empty database. [Development sign-in](#development-sign-in) lists the seeded users.

With Docker Compose, `./database` (or `LOCAL_DATABASE_DIR`) and `./import` are mounted into the container, so the database survives `docker compose down`. The image has no `--reload`: rebuild with `docker compose up --build` after a code change.

### LLM summaries (optional)

Without `LLM_API_KEY` everything works except summaries: a requested summary is marked as a configuration error and no call is made to the provider. To generate them, set the key in `.env`, then run the daemon next to the application:

```bash
python summaries_generator_daemon.py
```

It loops, writes to the database and calls an external LLM service: only run it when needed. For local development, `RUN_SUMMARIES_DAEMON=1` in `.env` makes Uvicorn start and stop it with the application. Leave it empty in production, where `launch.sh` already runs the daemon in its own `screen` session.

---

## Logging

Application logs use the standard Python `logging` module and the `uvicorn` logger, so that messages from the application, `auth.py` and `seed.py` share the format, colours and handlers the server already configured.

Levels are used according to severity:

| Level | Use |
|-------|-----|
| `DEBUG` | Detailed information for development and seeding. |
| `INFO` | Start, stop and normal application operations. |
| `WARNING` | Expected resource missing, or a non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | Required configuration missing, which prevents startup. |

Example:

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Operation done")

try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

New diagnostics should use the appropriate logger rather than `print()`. The application level is currently set to `DEBUG` in `core/dependencies.py`. Application logs go through the Uvicorn handler, usually to `stderr`; with a separate redirection, use for example `2> error.log` to capture them.

---

## Configuration

Every variable is described once, in [`.env.example`](.env.example), which is the reference. What each authentication mode needs:

| Variable | `AUTH_MODE=dev` (fork, local) | `AUTH_MODE=entra` (default, deployment) |
|---|---|---|
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | not needed | required, otherwise startup stops with exit code 1 |
| `REDIRECT_URI` | not needed | required |
| `SECRET_KEY` | optional (random key, sessions lost on restart) | required, otherwise startup stops with exit code 1 |
| `DEV_LOGIN_KEY` | optional (empty = open sign-in) | ignored, with a warning |
| `ALLOWED_DOMAINS` | applies | applies |
| `LLM_API_KEY` | optional (summaries only) | optional (summaries only) |
| `LOCAL_DATABASE_DIR` | optional (default `./database/`) | optional |
| `RUN_SUMMARIES_DAEMON` | optional | leave empty (`launch.sh` runs the daemon) |

An invalid `AUTH_MODE` also stops startup with exit code 1.

`SECRET_KEY` signs the session cookies: anyone who knows it can forge an admin session. Generate it with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

> [!CAUTION]
> Never commit `.env`. It is already listed in `.gitignore`, as are the `*.db` files (`database/db_oceens.db`, `cache_llm.db`).

---

## LLM providers (verbatim summaries)

Verbatim summaries are generated by an LLM. The provider is **configurable from the interface** (`/backend/providers`, admin only), without touching the code. The default provider is **Ollama EPF** (`https://locallm.mde.epf.fr/ollama`), created automatically on first start.

### Supported API types

| `api_type` | Covers |
|------------|--------|
| `ollama`    | Ollama servers (local, EPF, third-party) |
| `openai`    | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Claude API (Anthropic) |

### Security principle: no key in the database

The SQLite database is not encrypted and ends up in backups. **No API key is therefore stored in it.** The `llm_providers` table only holds the *name* of the environment variable (`api_key_env`, e.g. `OPENAI_API_KEY`); the value stays in `.env` and is only resolved at call time. That name is checked against an allow-list (`LLM_*` or `*_API_KEY`), so it cannot point to a system secret (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…).

### Adding a provider

1. **Add the key to `.env`** under a compliant name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the summaries daemon** (`.env` is only read at startup):

   ```bash
   python summaries_generator_daemon.py
   ```

3. **Create the provider** in `/backend/providers` → *+ Nouveau fournisseur*: name, API type, base URL, environment variable name (`OPENAI_API_KEY`) and a default model. The **"key present / absent"** indicator confirms the variable is loaded. The **Test** button checks that the URL and key answer, then sends a one-token generation to confirm the account can actually generate (see below).

4. **Link a prompt** to the provider: in `/backend/prompts`, a `<select>` picks a prompt's provider. A prompt without a provider (`provider_id` NULL) falls back to Ollama EPF.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted (so as not to break those prompts' configuration).

### Exhausted credit and other provider errors

Each provider reports failures in its own format: exhausted credit is a `429 insufficient_quota` at OpenAI, but a `400 "Your credit balance is too low"` at Anthropic. `services/llm_client.py` normalises these answers into categories (`quota`, `rate_limit`, `auth`, `model`, `server`) and derives a readable message from them:

> ⚠️ Crédit ou quota épuisé chez le fournisseur : la clé est valide mais le
> compte ne peut plus générer. Rechargez le compte ou choisissez un autre
> fournisseur. (fournisseur OpenAI, modèle gpt-4o-mini, HTTP 429)

This message is written to `Summary.metadata_text` instead of the raw JSON, so it is visible from the interface when a summary fails. The provider's raw answer stays in the daemon logs for diagnosis.

> [!IMPORTANT]
> The **Test** button does not only list the models: at OpenAI as at Anthropic, `GET /v1/models` still answers normally with a zero balance. A one-token generation ping (negligible cost) is therefore sent next: it is the only way to spot exhausted credit **before** starting a summary campaign.

---

## Cost of summaries

The cost of each summary is **measured, not estimated**. At generation time the daemon records the token counters returned by the provider (`Summary.input_tokens`, `output_tokens`, `model_used`): it is the only chance to capture them, no API lets you ask for them afterwards. The amount is then obtained by crossing these counters with the price list.

> [!NOTE]
> This section replaces the former `llm-utils/token-counting/` scripts, which counted the tokens of the **repository's source code** and multiplied them by a hard-coded price. That measure said nothing about the application's real spending. Tracking now covers the calls actually billed.

### Price list — `/backend/llm/prices`

Prices live in the database (`llm_model_prices` table), in **dollars per million tokens**, as providers publish them. They are editable from the administration: no release is needed to follow a price change, nor to cover a provider added locally.

Pre-filled at startup (`seed_model_prices`, idempotent — a price corrected by hand is never overwritten):

| Model | Input $/M | Output $/M |
| --- | ---: | ---: |
| `claude-opus-5` | 5.00 | 25.00 |
| `claude-sonnet-5` | 3.00 | 15.00 |
| `claude-haiku-4-5` | 1.00 | 5.00 |
| `gemma4:26b` (Ollama EPF, self-hosted) | 0.00 | 0.00 |

Other providers' prices (OpenAI, Mistral, Groq…) are **to be entered**: they are not guessed. A provider-specific price wins over a generic price with the same model name.

### Where to look

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Overall cost, broken down by survey and by model (admin) |
| 💰 button on a survey row | Cost of that survey's summaries |

### What is not priced

A summary cannot be priced when its counters are missing (generated before this feature, or a provider that does not expose them) or when its model has no recorded price. It is then **counted separately**, never estimated nor rounded to zero: an invented amount would do more harm than a missing one, since it would display with the authority of a real amount. The screens say explicitly when a total is partial.

Not to be confused with a **zero** cost: self-hosted models really cost $0.00, which is not the same information as "unknown".

> [!IMPORTANT]
> Tracking starts when the feature goes live: summaries generated before it have no counters in the database and cannot be priced retroactively.

---

## Project structure

```
OceENS/
├── main.py                       # FastAPI factory, middlewares and router assembly
├── sondage_loader.py             # Loads a complete survey for export
├── survey_loader_from_xlsx.py    # Imports surveys from an Excel file
├── summaries_generator_daemon.py # Asynchronous LLM summary processing (separate process)
├── launch.sh                     # Launch script (production, without Docker)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Application Docker image
├── docker-compose.yaml           # Local container start (reads .env)
├── .dockerignore                 # Files excluded from the Docker build
├── .env.example                  # Reference for every environment variable
├── .env                          # Environment variables (⚠️ not committed)
├── .gitignore                    # Files and folders ignored by Git
├── CONTEXT.md                    # Domain vocabulary
│
├── docs/
│   ├── smoke-test.md             #   Manual smoke test: how to run and check the project
│   └── adr/                      #   Architecture decision records
│
├── core/                         # Low-level access and security
│   ├── auth.py                   #   Microsoft Entra ID authentication (login, logout, callback) and development sign-in
│   ├── database.py               #   SQLite engine and SessionDep dependency
│   ├── security.py               #   Roles, scopes, access control
│   ├── dependencies.py           #   Shared Jinja templates and logger
│   └── seed.py                   #   Initial data and program synchronisation
│
├── models/                       # SQLModel schema, one file per table
│   ├── __init__.py               #   Re-exports every class (see its docstring)
│   └── User.py, Survey.py, ...
│
├── routers/                      # Routes split by business domain
│   ├── pages.py                  #   Home and per-role dashboards
│   ├── surveys.py                #   Surveys: CRUD, status, export, visualisation
│   ├── students.py               #   Student enrolment in a survey
│   ├── users.py                  #   User role management
│   ├── summaries.py              #   Triggering LLM summaries
│   ├── prompts.py                #   Prompt administration
│   ├── survey_templates.py       #   Survey template administration
│   ├── sections_questions.py     #   Section and question administration
│   └── llm/                      #   LLM administration (URLs unchanged)
│       ├── _access.py            #     Shared access control of the LLM screens
│       ├── providers.py          #     LLM providers (CRUD + connection test)
│       ├── prices.py             #     Price list per model
│       └── costs.py              #     Overall and per-survey cost
│
├── services/                     # Business logic
│   ├── helpers.py                #   Navigation, statistics, filters, sorting
│   ├── visualisation_data.py     #   Aggregations and visualisation context
│   ├── llm_client.py             #   Multi-provider LLM client (ollama/openai/anthropic)
│   ├── llm_costs.py              #   Summary cost (measured tokens × price list)
│   ├── settings_store.py         #   Application settings stored in the database (USD → EUR rate)
│   └── export_csv.py             #   CSV export of the answers
│
├── import/                       # CSV data read by the seed (programs, demo answers)
│
├── llm-utils/                    # LLM tools outside the application
│   └── README.md                 # (cost tracking moved into the app, see above)
│
├── templates/                    # HTML templates (Jinja2)
│   ├── index.html                     # Home / login page
│   ├── dashboard/
│   │   ├── admin.html
│   │   ├── student.html
│   │   ├── program_manager.html
│   │   ├── facilitator.html
│   │   ├── campus_manager.html
│   │   ├── teachers-analytics.html       # Teacher satisfaction (campus_manager, program_manager)
│   │   ├── survey.html                   # Answering a survey
│   │   ├── survey_create.html            # Survey creation
│   │   └── visualisation.html            # Answers visualisation
│   ├── backend/                       # Administration pages (admin only)
│   │   ├── prompts.html               # LLM prompts list
│   │   ├── prompt_form.html           # Shared create/edit form
│   │   └── llm/                       # LLM screens (providers, prices, costs)
│   │       ├── providers.html
│   │       ├── provider_form.html
│   │       ├── prices.html            # Editable price list
│   │       └── costs.html             # Overall and per-survey cost
│   └── template_parts/                # Fragments reused across dashboards
│       ├── part_site_header.html
│       ├── part_dashboard_navigation.html
│       ├── part_theme_switcher.html
│       └── ...
│
├── static/
│   ├── css/                      # admin.css, student.css, program_manager.css, survey.css,
│   │                              # survey_create.css, visualisation.css, prompt_form.css,
│   │                              # llm_backend.css (LLM screens), theme.css, site_header.css,
│   │                              # dashboard_navigation.css, responsive.css
│   ├── js/
│   │   └── survey.js
│   └── img/
│
├── database/                     # SQLite database, created on first start (ignored by Git)
│   └── db_oceens.db
│
└── .venv/                        # Python virtual environment (not committed)
```

---

## Authentication (OAuth 2.0)

The authentication flow relies on **Microsoft Entra ID** through the MSAL library:

```
1. The user clicks "Sign in"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to the Microsoft login page

2. The user authenticates at Microsoft
   → Microsoft redirects to /auth/callback with a code + state

3. The server exchanges the code for an access token
   → User details fetched through Microsoft Graph
   → Database lookup of the role(s) and their scope
   → Session created {name, email, roles}
   → Redirect to the matching dashboard

4. On sign-out (/logout)
   → Session and cookies deleted
   → Signed out at Microsoft
   → Back to the home page
```

Authentication alone authorises no business action: each route then checks the role and the scope (program or campus) through `require_roles()` and its helpers.

---

## Development sign-in

To work on a fork without an Azure application, the **development sign-in** lets you sign in as any user, without proof of identity. It must **never** be used in production.

| Variable | Role |
|----------|------|
| `AUTH_MODE` | `entra` (default) or `dev`, case- and whitespace-insensitive. Any other value stops the application at startup. In `dev`, the `ENTRA_*` variables are not needed. |
| `DEV_LOGIN_KEY` | Optional, `dev` mode only. If set, every sign-in must provide it (`key` field), otherwise `401`. If not, sign-in is open. Ignored (with a warning) in `entra`. |
| `SECRET_KEY` | Optional in `dev`: if missing, a random key is drawn at each start (with a warning) and sessions are lost on restart. Required in `entra`. |
| `ALLOWED_DOMAINS` | Also applies in `dev` (`403` for another domain); defaults to `epf.fr,epfedu.fr` in this mode. |

In `dev` mode, the session cookie is no longer restricted to HTTPS (`http://localhost` works), `/login` redirects to `/dev/login`, `/auth/callback` does not exist and `/logout` clears the session then goes back to `/`. A warning is logged at startup. A red, non-dismissable banner is shown at the top of every page that includes the shared header: it recalls the signed-in address, offers "Changer d'utilisateur" (`/dev/login`) and says "accès ouvert à tous" when `DEV_LOGIN_KEY` is not set.

`POST /dev/login` expects a form with `email`, `name` (optional) and `key` (if `DEV_LOGIN_KEY` is set). The user is fetched or created as on return from Entra: an unknown email becomes a new student. Without `name`, the display name is built from the email (`bob.leponge@epfedu.fr` → "Bob Leponge"). A new sign-in replaces the session: that is how you switch user.

In a browser, `GET /dev/login` lists the database's users, grouped by role name without scope (a user with no role appears under `student`, a user with several roles under each of them). One click signs in as the chosen user; a free field accepts another address, with an optional name. If `DEV_LOGIN_KEY` is set, a single key field is shown and used for every sign-in on the page; the key is never stored in the session. Come back to this page to switch user.

The seed provides at least one user per role, holding that role alone:

| Email | Role |
|---|---|
| `etienne.gibaud@epf.fr` | `admin` only |
| `bob.leponge@epfedu.fr` | student (no role row) |
| `oceens.facilitator@epf.fr` | `facilitator:MDAI5` only |
| `oceens.program-manager@epf.fr` | `program_manager:MDAI5` only |
| `oceens.campus-manager@epf.fr` | `campus_manager:Montpellier` only |

`antoine.gademer@epf.fr` (`admin` + `program_manager:MDAI5`) and `yassine.gharbi@epfedu.fr` (`admin` + `campus_manager:Montpellier`) combine roles.

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=my-key uvicorn main:app

# Sign in as the seed's admin; -c stores the session cookie
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for the following requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

> [!WARNING]
> `dev` mode does not require `SECRET_KEY`. Without it, the key is random and unknown; but if a known `SECRET_KEY` is set (shared, copied from an example…), anyone who knows it can forge a session cookie and bypass `DEV_LOGIN_KEY`: `dev` mode accepts it, since it is only meant for local use.

---

## Notable features

### Teacher analytics

The `/dashboard/teachers/analytics` route (`campus_manager`, `program_manager`) aggregates the satisfaction score per `(teacher, survey)` from the `QCU_Satisfaction` answers that carry an `Answer.teacher` (ME sections). The teacher list is sorted with `teacher_sort_key()`, case- and accent-insensitive, and stays filterable by school year, semester, program and teacher.

### Teacher filter in the visualisation

A client-side selector filters the visualisation without reloading: only the chosen teacher's modules remain, the Campus and Program sections being hidden. The page reads `?teacher=<name>` on load to pre-filter itself; links from the analytics pass this parameter, so a click on a teacher's score opens their view directly.

### Surveys imported from Excel

Surveys loaded by `survey_loader_from_xlsx.py` have no `QCU_Attendance` question: `services/visualisation_data.py` then uses `satisfaction_responses_count` as the fallback denominator for the teacher score. Teacher names are normalised with `.title()` on import and on aggregation, to merge case variants (`"GADEMER Antoine"` and `"Gademer Antoine"` = one entry). Questions are sorted by `question_id` in the template, which guarantees charts before verbatims whatever the insertion order.

### Campus director scope

The `campus_manager` dashboard only shows closed surveys with at least one respondent. The questionnaire link and the QR code are hidden there (`can_view_survey_link=False`): this role reads results without distributing surveys. The `{% if can_view_survey_link | default(true) %}` guard leaves the other dashboards unchanged.

### Cleaning up orphan students

When a survey is deleted, the students no longer attached to **any other** survey are deleted too, to avoid piling up unused accounts (`services/helpers.py`, `_delete_orphan_students`). A safeguard protects users with a privileged role (`admin`, `program_manager`, `facilitator`, `campus_manager`): a teacher or manager who answered a survey is never deleted.

### Adding a user by email

The "Utilisateurs" tab of the administrator dashboard has a **"+ Ajouter un utilisateur"** button: an email is enough to create the account, with the `student` role by default (`POST /api/users`, admin only). The email is validated (format + allowed domain) and duplicates are refused.

---

## Deployment checklist

- [ ] `.env` created with the real Azure credentials and a dedicated `SECRET_KEY` (required outside `AUTH_MODE=dev`, otherwise the application refuses to start)
- [ ] `AUTH_MODE` unset or `entra`
- [ ] Valid SSL certificate (Let's Encrypt or equivalent)
- [ ] `https_only=True` in the SessionMiddleware (automatic outside `AUTH_MODE=dev`)
- [ ] Database present (`database/db_oceens.db`) or Docker volume mounted
- [ ] Environment variables secured, including `LLM_API_KEY`
- [ ] **Docker Compose**: `.env` loaded through `env_file`, never copied into the image; `LOCAL_DATABASE_DIR` pointing to the right directory
- [ ] `RUN_SUMMARIES_DAEMON` empty, and `summaries_generator_daemon.py` running if LLM summaries are used

---

## Before contributing

The repository has no automated test suite and no CI yet. Before proposing a change, run [`docs/smoke-test.md`](docs/smoke-test.md), then test the affected routes by hand on a throwaway SQLite database (never a copy of production), with the relevant roles and survey statuses.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**OcéEns team** — EPF
