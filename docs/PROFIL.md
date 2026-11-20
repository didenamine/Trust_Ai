# Profil candidat commun (T-09)

Le profil est le **format unique** qui décrit un candidat. Il est rempli de trois façons et lu par la plupart des fonctionnalités :

| Qui | Story | Utilisation |
| --- | --- | --- |
| Diden | US05 Analyse du CV | le LLM transforme le CV importé en profil |
| Fourat | US06 Saisie manuelle | le formulaire produit le même profil |
| Diden | US07 Consultation et correction | affiche et modifie le profil |
| Fourat | US09 Analyse de l'offre | réutilise les mêmes briques (`schemas/shared.py`) pour l'offre |
| Eya | US12 / US13 Matching | compare profil et offre, champ par champ |
| Azza | US14 Adaptation du CV | part du profil pour adapter le CV à une offre |
| Ikram | US31 / US33 | tableau de bord, compétences manquantes |

Code de référence : [`backend/app/schemas/profile.py`](../backend/app/schemas/profile.py) (Pydantic) et [`frontend/src/lib/profile.ts`](../frontend/src/lib/profile.ts) (types TypeScript). Exemples complets : [`profile_fr.json`](../backend/tests/fixtures/profile_fr.json), [`profile_en.json`](../backend/tests/fixtures/profile_en.json).

## Structure

```
CandidateProfile
├── schema_version      1
├── language            "fr" | "en"   (seul champ obligatoire)
├── personal_info       full_name, headline, email, phone, location, links[]
├── summary             texte libre
├── skills[]            name, category (hard | soft), level
├── experiences[]       id, job_title, company, location, employment_type,
│                       start_date, end_date, is_current, description, achievements[], skills[]
├── education[]         id, degree, level, field_of_study, institution, location,
│                       start_date, end_date, is_current, description
├── languages[]         name, code (ISO 639-1), level (A1…C2 | native)
├── certifications[]    id, name, issuer, issue_date, url
└── projects[]          id, name, description, start_date, end_date, is_current, skills[], url
```

## Valeurs possibles

| Champ | Valeurs |
| --- | --- |
| `skills[].category` | `hard` (technique, outil, méthode), `soft` (savoir-être) |
| `skills[].level` | `beginner`, `intermediate`, `advanced`, `expert`, ou `null` |
| `languages[].level` | `A1`, `A2`, `B1`, `B2`, `C1`, `C2`, `native`, ou `null` |
| `education[].level` | `secondary` (Bac), `associate` (Bac+2), `bachelor` (Bac+3, Licence), `master` (Bac+5, Master, ingénieur), `doctorate`, ou `null` |
| `experiences[].employment_type` | `full_time`, `part_time`, `internship` (stage), `apprenticeship` (alternance), `freelance`, `volunteer`, ou `null` |

Les valeurs sont stockées en anglais ; le frontend les traduit (libellés français dans `profile.ts`).

## Règles appliquées automatiquement

Le schéma nettoie les données, qu'elles viennent du LLM ou d'un formulaire :

- **Textes vides → `null`** et espaces superflus supprimés.
- **Dates partielles** : `"2021"` ou `"2021-03"`. Les formats courants sont convertis (`03/2021`, `2021-3`, `2021-03-15` → `2021-03`). Une date de fin antérieure au début est refusée. Si `is_current` est vrai, `end_date` est vidée.
- **Liens** : `github.com/moi` devient `https://github.com/moi`.
- **Doublons fusionnés** : `Python` et `python ` ne font qu'une compétence (en gardant le meilleur niveau) ; `Anglais` et `English` ne font qu'une langue grâce au `code`.
- **Identifiants** : chaque expérience, formation, certification et projet reçoit un `id` stable s'il n'en a pas. Le frontend doit le renvoyer tel quel lors d'une modification.
- **Champs inconnus ignorés**, pour qu'un champ en trop renvoyé par le LLM ne fasse pas échouer l'analyse.
- **Limites** : 150 compétences, 50 expériences, 30 formations, 20 langues, 50 certifications, 50 projets.

## Volontairement absent

Photo, âge ou date de naissance, genre, nationalité, situation familiale. Ces informations ne doivent jouer **aucun rôle** dans le matching : le profil ne les stocke donc pas.

## Fonctions utiles pour le matching

```python
profile.skill_keys()                 # toutes les compétences normalisées (liste + expériences + projets)
profile.total_experience_months()    # mois d'expérience, chevauchements comptés une fois, bénévolat exclu
profile.total_experience_months(include_internships=False)
profile.highest_education_level()    # EducationLevel le plus élevé, comparable via .rank
normalize_skill_name("Node.JS")      # "node.js" : clé de comparaison (sans accents, minuscules)
```

La normalisation reste simple : rapprocher `ReactJS` et `React` relève de US12 (RapidFuzz).

## Stockage et API

- Table `candidate_profiles` : un profil par candidat, contenu en **JSONB** (`data`), avec `source` (`cv_analysis` ou `manual`), le CV d'origine (`cv_document_id`) et `updated_at`.
- Côté backend, toujours passer par `app/services/profile_service.py` :
  - `save_profile(db, user_id=..., profile=..., source=ProfileSource.CV_ANALYSIS, cv_document_id=...)` (US05)
  - `get_candidate_profile(db, user_id)` → `CandidateProfile | None` (US12, US14, US31…)
- API (authentification requise) :
  - `GET /api/profile/me` → `{ profile, source, cv_document_id, updated_at }`, ou 404 si aucun profil
  - `PUT /api/profile/me` → crée ou remplace le profil (US06, US07) ; renvoie le profil normalisé, 422 si invalide
- Côté frontend : `fetchMyProfile()`, `saveMyProfile(profile)`, `emptyProfile()` dans `lib/profile.ts`.

## Faire évoluer le schéma

1. Modifier `schemas/profile.py` **et** `lib/profile.ts`, puis mettre à jour ce document et les exemples JSON.
2. Un champ ajouté doit être **optionnel** (avec une valeur par défaut) pour que les profils déjà enregistrés restent valides.
3. Un changement incompatible (renommage, suppression) demande d'incrémenter `schema_version` et de migrer les données existantes.
