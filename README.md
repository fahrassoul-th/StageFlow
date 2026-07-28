# StageFlow

[![codecov](https://codecov.io/github/fahrassoul-th/StageFlow/graph/badge.svg?token=31DVBHFVKF)](https://codecov.io/github/fahrassoul-th/StageFlow)

API interne de gestion des stages pour un Master DSIA : offres de stage, candidatures,
validation pédagogique — chaque rôle ne voit et ne modifie que ce qui le concerne.

Réalisé dans le cadre de l'examen FastAPI du Master 1 DSIA (Sujet 1), en alignant
l'implémentation sur le style asynchrone enseigné en cours (SQLAlchemy async,
`BaseRepository` générique, JWT access + refresh) tout en respectant strictement
l'architecture et les règles métier imposées par le sujet.

## Rôles

| Rôle | Peut faire |
|---|---|
| `student` | Consulter les offres publiées, candidater, retirer une candidature (si non acceptée) |
| `company` | Créer des offres brouillon, les soumettre, consulter les candidatures de ses propres offres |
| `program_manager` | Publier/refuser une offre soumise, accepter/refuser une candidature, consulter les statistiques |
| `admin` | Voit toutes les offres au même titre qu'un `program_manager` (pas de gestion fine des comptes implémentée dans ce périmètre) |

## Architecture

```
app/
  main.py                 point d'entrée FastAPI
  api/routes/               auth, users, offers, applications, stats
  core/                      config, security (JWT access+refresh), permissions (RBAC), errors
  db/                        session SQLAlchemy async, base déclarative
  models/                    User, Role, Offer, Application (SQLAlchemy 2.0, async)
  schemas/                   DTO Pydantic v2 : entrée client / persistance / sortie séparées
  repositories/              base.py (CRUD générique) + repositories spécialisés
  middlewares/               request_id, security_headers, cors, rate_limit
  utils/                     hashing, pagination, time
tests/
  unit/                      repositories, sécurité, permissions, schémas (sans HTTP)
  integration/               routes testées via httpx.AsyncClient (HTTP async réel)
alembic/                     migrations (async)
.github/workflows/ci.yml     tests + couverture + build/push Docker
```

Toute la chaîne est asynchrone (`async def`/`await` de bout en bout). Les routes ne
touchent jamais SQLAlchemy directement : elles passent systématiquement par un
repository, qui hérite d'un `BaseRepository` générique (`Generic[Model, CreateSchema,
UpdateSchema]`). L'autorisation est centralisée dans `core/permissions.py`, jamais
dispersée dans les routes.

## Variables d'environnement

Copier `.env.example` vers `.env` et ajuster si besoin :

```bash
cp .env.example .env
```

| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | DSN PostgreSQL (driver async `asyncpg`) | `postgresql+asyncpg://stageflow:stageflow@db:5432/stageflow` |
| `SECRET_KEY` | Clé de signature des JWT | à changer en production |
| `ALGORITHM` | Algorithme JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token d'accès | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée de vie du refresh token | `7` |
| `ALLOWED_ORIGINS` | Origines autorisées pour CORS | `["http://localhost:3000"]` |

## Lancement avec Docker (recommandé)

```bash
docker compose up --build
```

L'API démarre sur `http://localhost:8000` (rechargement à chaud actif), avec Postgres
dans un conteneur séparé. Documentation interactive : `http://localhost:8000/docs`.

Le `Dockerfile` est multi-stage (builder + production, utilisateur non-root, servi par
gunicorn + workers uvicorn) ; `docker-compose.yml` réutilise cette même image mais
surcharge sa commande avec `uvicorn --reload` pour le confort de développement.

Les migrations ne sont pas appliquées automatiquement au démarrage du conteneur :

```bash
docker compose exec api alembic upgrade head
```

## Lancement en local (sans Docker)

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt

# Une base Postgres locale est nécessaire (driver asyncpg), ou pointer DATABASE_URL
# vers du SQLite async pour un essai rapide, ex. : sqlite+aiosqlite:///./dev.db
alembic upgrade head
uvicorn app.main:app --reload
```

## Lancer les tests

```bash
pytest --cov=app --cov-report=term-missing
```

La suite (48 tests, unitaires + intégration) ne nécessite **aucune base de données
réelle** : chaque test tourne contre une base SQLite async (`aiosqlite`) fraîche et en
mémoire, injectée via un override de la dépendance `get_db`. Couverture actuelle : 99 %
(100 % sur tout le code applicatif).

> Note technique si vous modifiez la config de couverture : `pyproject.toml` déclare
> `concurrency = ["greenlet", "thread"]` sous `[tool.coverage.run]`. Sans ça, `coverage.py`
> sous-évalue massivement le code — SQLAlchemy async traverse des greenlets et FastAPI
> exécute les dépendances synchrones dans un threadpool, deux contextes que le traceur
> par défaut ne suit pas.

## CI et Codecov

Le pipeline `.github/workflows/ci.yml` lance les tests, envoie la couverture à Codecov,
puis construit **et publie** l'image Docker sur GitHub Container Registry. Pour
l'activer sur un dépôt GitHub :

1. Pousser ce dépôt sur GitHub.
2. Se connecter sur [app.codecov.io](https://app.codecov.io) avec le compte GitHub et
   autoriser l'accès au dépôt.
3. Dans Codecov : Configuration → General → copier le *Repository upload token*.
4. Dans GitHub : Settings → Secrets and variables → Actions → New repository secret,
   nom `CODECOV_TOKEN`, valeur = le token copié.
5. Un push sur `main` (ou une pull request) déclenche le pipeline.

## Endpoints principaux

| Méthode | Route | Rôle | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Créer un compte (username + email + mot de passe) |
| POST | `/auth/login` | public | OAuth2 password flow (login par username) → access + refresh token |
| POST | `/auth/refresh` | public | Échanger un refresh token contre une nouvelle paire de tokens |
| GET | `/users/me` | authentifié | Profil courant |
| POST | `/offers` | company | Créer une offre brouillon |
| GET | `/offers` | authentifié | Catalogue (adapté au rôle) |
| GET | `/offers/{id}` | authentifié | Détail d'une offre (404 si non visible) |
| PATCH | `/offers/{id}/submit` | company | draft → submitted |
| PATCH | `/offers/{id}/review` | program_manager | submitted → published/rejected |
| POST | `/offers/{id}/applications` | student | Candidater à une offre publiée |
| GET | `/applications/me` | student | Mes candidatures |
| GET | `/offers/{id}/applications` | company/program_manager/admin | Candidatures d'une offre |
| PATCH | `/applications/{id}/decision` | program_manager | Accepter/refuser une candidature |
| DELETE | `/applications/{id}` | student | Retirer une candidature (transition vers `withdrawn`) |
| GET | `/stats` | program_manager | Offres/candidatures par statut |

Documentation OpenAPI complète et interactive : `/docs` (Swagger) ou `/redoc`.

## Choix de conception qui s'écartent du fil rouge du cours

Le style général (async, `BaseRepository` générique, refresh token, CORS, rate
limiting) suit le projet fil rouge vu en cours. Quelques divergences assumées, dictées
par le sujet d'examen lui-même :

- **Codes d'erreur** : le sujet impose strictement 400/401/403/404 ; le fil rouge utilise
  409 pour les doublons. Ici, doublon email/username → 400.
- **Chemin de connexion** : `/auth/login` (nommé explicitement par le sujet), pas
  `/auth/token` comme dans le fil rouge.
- **Autorisation par rôle**, pas par scopes OAuth2 : le modèle `User` du fil rouge n'a
  volontairement pas de rôle (c'est un TODO laissé par l'enseignant) — l'architecture
  imposée par l'examen (`models/role.py`, `core/permissions.py`) est précisément cette
  extension.
- **404, jamais 403**, quand une ressource existe mais n'est pas visible pour l'appelant
  (offre d'un concurrent, candidatures d'une autre entreprise) — pour ne jamais confirmer
  l'existence d'une ressource à quelqu'un qui n'y a pas droit.
