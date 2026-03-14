# DocSentinel

Plateforme intelligente de traitement documentaire orientée documents administratifs et financiers.

DocSentinel permet de :
- ingérer des documents (PDF/images),
- extraire des données structurées,
- normaliser les champs,
- détecter des signaux de fraude,
- exposer des résultats via API sécurisée et multi-tenant.

## Fonctionnalités principales

- API FastAPI avec authentification par clé API.
- Isolation multi-tenant (`Tenant`, `ApiKey`, `Document` rattachés au tenant).
- Upload sécurisé :
  - limite de taille (20 MB),
  - détection MIME réelle (`python-magic`),
  - scan antivirus ClamAV,
  - empreinte SHA-256 + déduplication par tenant.
- Pipeline asynchrone Celery avec retries et backoff exponentiel.
- OCR exécuté dans un conteneur sandbox dédié.
- Stockage objets MinIO par couches :
  - `raw` (fichier source),
  - `bronze` (texte OCR),
  - `silver` (données extraites/normalisées),
  - `gold` (analyse fraude).
- Observabilité Prometheus (`/metrics` protégé).
- Metering et quotas mensuels par tenant :
  - documents uploadés,
  - requêtes API,
  - OCR traités,
  - fraudes scorées.

## Stack technique

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Redis
- Celery
- MinIO
- OCR sandbox (FastAPI + Tesseract + pdf2image)
- Prometheus Client

## Architecture simplifiée

1. `POST /documents/upload` (authentifié) reçoit un fichier.
2. Validation sécurité (taille, MIME, antivirus, quota, déduplication tenant).
3. Écriture en MinIO `raw` + création `Document`.
4. Enqueue du job Celery.
5. Worker :
   - télécharge `raw`,
   - appelle OCR sandbox (`http://ocr-sandbox:8080/ocr`),
   - stocke `bronze`,
   - extraction + normalisation,
   - scoring fraude,
   - stockage `silver` + `gold`,
   - met à jour les statuts.

## Lancement local (Docker)

Prérequis :
- Docker
- Docker Compose

Depuis la racine du projet :

```bash
docker compose up --build
```

Services démarrés :
- `postgres` (5432)
- `redis` (6379)
- `minio` API (9000) / console (9001)
- `backend` API (8000)
- `worker` Celery
- `ocr-sandbox` (interne, port 8080 exposé uniquement au réseau Docker)

## Variables d’environnement clés

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_SECURE`
- `MINIO_RAW_BUCKET`
- `CLAMD_HOST`
- `CLAMD_PORT`

## Sécurité API

- Header requis : `X-API-Key: <clé>`
- La clé reçue est hashée SHA-256 et comparée au `key_hash` en base.
- Le tenant et la clé API doivent être actifs.
- Limitation de débit (Redis) : 100 req/min par clé hashée.
- Quota API mensuel appliqué à chaque requête authentifiée.

## Endpoints principaux

- `GET /health`
- `POST /documents/upload`
- `GET /documents/{id}/status`
- `GET /documents/{id}/results`
- `GET /usage/current-month`
- `GET /metrics` (protégé)

## Metering et quotas

Événements enregistrés :
- `document_uploaded`
- `api_request`
- `ocr_processed`
- `fraud_scored`

Quotas tenant :
- `monthly_document_quota` (défaut 1000)
- `monthly_api_quota` (défaut 10000)

## Licence

Ce projet est distribué sous **PolyForm Noncommercial License 1.0.0**.

L’utilisation commerciale est interdite sans autorisation explicite du titulaire des droits.

Voir le fichier [LICENSE](./LICENSE).
