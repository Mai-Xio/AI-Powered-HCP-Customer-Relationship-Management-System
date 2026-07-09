from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HCPProfile, Interaction
from app.schemas import InteractionDraft


SEED_HCPS = [
    {
        "name": "Dr. Meera Kapoor",
        "specialty": "Cardiology",
        "segment": "KOL",
        "territory": "Mumbai Central",
        "preferences": {
            "channel": "In-person meeting",
            "content": "Clinical data, safety updates, patient adherence",
            "best_time": "Evenings",
        },
        "last_interaction_summary": "Interested in real-world evidence and concise patient education material.",
    },
    {
        "name": "Dr. Arjun Menon",
        "specialty": "Endocrinology",
        "segment": "A",
        "territory": "Bengaluru South",
        "preferences": {
            "channel": "WhatsApp follow-up",
            "content": "Renal dosing, sample availability, comparative efficacy",
            "best_time": "Friday afternoon",
        },
        "last_interaction_summary": "Requested renal dosing clarification before recommending new starts.",
    },
    {
        "name": "Dr. Priya Shah",
        "specialty": "Internal Medicine",
        "segment": "B",
        "territory": "Ahmedabad West",
        "preferences": {
            "channel": "Clinic visit",
            "content": "Patient affordability, starter packs, safety cards",
            "best_time": "Lunch hour",
        },
        "last_interaction_summary": "Responds well to short leave-behind material and patient affordability data.",
    },
]


def seed_hcp_profiles(db: Session) -> None:
    for payload in SEED_HCPS:
        exists = db.scalar(select(HCPProfile).where(HCPProfile.name == payload["name"]))
        if not exists:
            db.add(HCPProfile(**payload))
    db.commit()


def list_hcp_profiles(db: Session) -> list[HCPProfile]:
    return list(db.scalars(select(HCPProfile).order_by(HCPProfile.name)).all())


def save_interaction(db: Session, draft: InteractionDraft) -> Interaction:
    interaction = Interaction(**draft.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction
