from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.plan import Plan


DEFAULT_PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Plan de base pour petits volumes.",
        "monthly_price_cents": 4900,
        "monthly_document_quota": 1000,
        "monthly_api_quota": 10000,
        "is_active": True,
    },
    {
        "code": "growth",
        "name": "Growth",
        "description": "Plan pour croissance des usages.",
        "monthly_price_cents": 14900,
        "monthly_document_quota": 10000,
        "monthly_api_quota": 100000,
        "is_active": True,
    },
    {
        "code": "scale",
        "name": "Scale",
        "description": "Plan pour gros volumes et industrialisation.",
        "monthly_price_cents": 49900,
        "monthly_document_quota": 100000,
        "monthly_api_quota": 1000000,
        "is_active": True,
    },
]


def seed_default_plans() -> None:
    db = SessionLocal()
    try:
        for plan_data in DEFAULT_PLANS:
            existing_plan = db.execute(
                select(Plan).where(Plan.code == plan_data["code"])
            ).scalar_one_or_none()

            if existing_plan is None:
                db.add(Plan(**plan_data))
                continue

            existing_plan.name = str(plan_data["name"])
            existing_plan.description = str(plan_data["description"])
            existing_plan.monthly_price_cents = int(plan_data["monthly_price_cents"])
            existing_plan.monthly_document_quota = int(plan_data["monthly_document_quota"])
            existing_plan.monthly_api_quota = int(plan_data["monthly_api_quota"])
            existing_plan.is_active = bool(plan_data["is_active"])
            db.add(existing_plan)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_default_plans()
