# TrustAI : comment fonctionne le projet

TrustAI est une application web qui **analyse des CV et des offres d'emploi avec une IA**, calcule un **score de compatibilité** entre les deux, puis **explique** ce score (points forts, compétences manquantes).

## 1. Vue d'ensemble

```
Navigateur ──► Frontend (React, :5173) ──► API (FastAPI, :8000/api) ──► PostgreSQL (:5432)
                                                │
                                                ├─► uploads/   (CV importés)
                                                └─► API LLM    (extraction CV et offre en JSON)
```

| Partie | Technologies | Dossier |
| --- | --- | --- |
| Frontend | React, Vite, TypeScript, Tailwind CSS, React Router, TanStack Query + Axios | `frontend/` |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy + Alembic | `backend/` |
| Base de données | PostgreSQL 16 (colonnes JSONB pour profils, offres, résultats) | service `db` |

## 2. Parcours fonctionnel

1. **Compte** : inscription et connexion (JWT), gestion du compte (US01, US02).
2. **CV** : import PDF/DOCX (US03), puis analyse : extraction du texte, appel au LLM, profil structuré en JSON, en français ou en anglais (US05). Le profil peut aussi être saisi à la main (US06), consulté et corrigé (US07).
3. **Offre** : ajout par URL ou par texte (US08), puis analyse par le LLM en un format comparable au profil (US09).
4. **Matching** : comparaison profil / offre avec pondération fixe, d'où un **score de compatibilité** (US12), son **explication** (US13) et les **compétences manquantes** (US33).
5. **Analyse ATS** du CV (US24) et **tableau de bord** de synthèse (US31).

L'idée centrale : le CV et l'offre sont transformés en **JSON de même forme** (schémas Pydantic communs), ce qui rend la comparaison simple et testable.

## 3. Organisation du code

**Backend** (`backend/app/`)
- `main.py` : crée l'application FastAPI (CORS, routes sous `/api`).
- `api/routes/` : un fichier par domaine (`health.py` aujourd'hui) ; à enregistrer dans `api/router.py`.
- `schemas/` : modèles Pydantic (profil, offre, résultat du matching).
- `models/` : tables SQLAlchemy ; à importer dans `models/__init__.py` pour Alembic.
- `services/` : logique métier (extraction du CV, appel LLM, matching).
- `core/config.py` : configuration lue depuis les variables d'environnement (`.env`).
- `alembic/` : migrations de la base.

**Frontend** (`frontend/src/`)
- `pages/` : un écran par page ; routes déclarées dans `App.tsx`.
- `components/` : composants partagés (`Layout.tsx`).
- `lib/api.ts` : client Axios unique ; `lib/queryClient.ts` : cache TanStack Query.

## 4. Lancer le projet

```bash
cp .env.example .env
docker compose up --build
```

- Application : http://localhost:5173
- API : http://localhost:8000/api/health, documentation Swagger : http://localhost:8000/docs
- Arrêt : `docker compose down`

Les migrations Alembic s'exécutent automatiquement au démarrage de l'API.
Sans Docker : voir le [README](../README.md).

## 5. Qualité et workflow Git

- **Branches** : `main` (stable) ← `develop` (intégration) ← `feature/US03-nom-court`.
- **Pull request** vers `develop`, avec **1 approbation** d'un autre membre ; `main` et `develop` sont protégées.
- **Commits** préfixés par le ticket : `US03: vérifier le type et la taille du fichier`.
- **Qualité** : Ruff + Black (Python), ESLint + Prettier (frontend), via `pre-commit install`.
- **Tests** : `cd backend && pytest` ; `cd frontend && npm test`.

Détails complets : [CONTRIBUTING.md](../CONTRIBUTING.md).

## 6. État actuel

Le squelette est en place (T-01 à T-04) : API de santé, application React, base PostgreSQL et Docker Compose. Les fonctionnalités (US01 à US33) sont à développer selon le backlog du Sprint 1.
