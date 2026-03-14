# Database Migrations (Alembic)

Run commands from the `backend/` directory.

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Generate a new revision

```bash
alembic -c alembic.ini revision --autogenerate -m "describe_change"
```

## 3. Upgrade database

```bash
alembic -c alembic.ini upgrade head
```

## 4. Downgrade database

```bash
alembic -c alembic.ini downgrade -1
```

Or downgrade to a specific revision:

```bash
alembic -c alembic.ini downgrade <revision_id>
```
