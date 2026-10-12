"""Configuration commune des tests, appliquée avant tout import du code.

`oceens.core.database` crée son moteur SQLite à l'import, dans
`LOCAL_DATABASE_DIR` : on le pointe vers un dossier temporaire, pour qu'un test
ne touche jamais la base de développement.

Importer un module de `oceens.core` importe `oceens.core.auth`, qui arrête le
processus sans credentials Entra : les tests tournent en `AUTH_MODE=dev`.

Le code appelle `load_dotenv()` à l'import : on le neutralise avant, pour qu'un
test donne le même résultat avec ou sans `.env`, la CI n'en ayant pas.
"""

import os
import tempfile

import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False

os.environ["LOCAL_DATABASE_DIR"] = tempfile.mkdtemp(prefix="oceens-tests-")
os.environ["AUTH_MODE"] = "dev"
