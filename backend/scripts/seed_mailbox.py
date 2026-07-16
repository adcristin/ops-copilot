"""
Seed the DB with real customer-support emails from a public dataset, so the
Mailbox dashboard has realistic data instead of empty tables.

Dataset: Tobi-Bueck/customer-support-tickets (Hugging Face, CC-BY-NC-4.0)
  - 61.8k support tickets: {subject, body, answer, type, queue, priority,
    language, tag_1..tag_8}
  - English + German tickets - we filter to English by default.
  - Non-commercial license: fine for a portfolio/demo, not for resale.

Usage:
    cd backend
    python -m scripts.seed_mailbox --limit 20                 # ingest only
    python -m scripts.seed_mailbox --limit 20 --classify       # ingest + LLM classification

--classify calls the LLM (costs a small amount / needs an API key set) - see
core/llm_client.py for provider config. Without --classify, we map the
dataset's own `priority` field directly and skip the category/SLA logic.
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from db.session import init_db, SessionLocal
from db.models import MailboxItem

# Fallback mapping when --classify isn't used - reuse the dataset's own
# priority field instead of calling the LLM.
DATASET_PRIORITY_MAP = {"low": "low", "medium": "medium", "high": "high", "critical": "high"}
FALLBACK_SLA = {"high": 8, "medium": 24, "low": 48}
FAKE_SENDER_DOMAIN = "customer-example.com"


def fetch_tickets(limit: int, language: str = "en"):
    """Streams the dataset and pulls the first `limit` tickets in the given language."""
    from datasets import load_dataset

    print(f"Streaming Tobi-Bueck/customer-support-tickets (need {limit} '{language}' tickets)...")
    ds = load_dataset("Tobi-Bueck/customer-support-tickets", split="train", streaming=True)

    tickets = []
    for row in ds:
        if row.get("language") != language:
            continue
        if not row.get("subject") or not row.get("body"):
            continue
        tickets.append(row)
        if len(tickets) >= limit:
            break
    return tickets


def seed(limit: int, do_classify: bool, language: str):
    init_db()
    db = SessionLocal()

    tickets = fetch_tickets(limit, language=language)
    print(f"Fetched {len(tickets)} tickets.")

    if do_classify:
        from mailbox_ops.classifier import classify_email
        from tasks.service import create_task_from_mailbox_escalation

    for i, row in enumerate(tickets):
        subject = row["subject"]
        body = row["body"]
        sender = f"customer_{i:04d}@{FAKE_SENDER_DOMAIN}"

        if do_classify:
            try:
                result = classify_email(subject, body)
            except Exception as e:
                print(f"  [ticket {i}] classification failed: {e}")
                continue

            item = MailboxItem(
                sender=sender,
                subject=subject,
                body=body,
                category=result["category"],
                priority=result["priority"],
                sla_hours=result["sla_hours"],
                routed_to=result["routed_to"],
                suggested_reply=result["suggested_reply"],
                status="drafted",
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            if result["category"] == "escalation":
                create_task_from_mailbox_escalation(db, item)
            print(f"  [ticket {i}] classified as {result['category']} / {result['priority']}")
        else:
            # Use the dataset's own priority/queue fields directly, no LLM call
            raw_priority = (row.get("priority") or "medium").lower()
            priority = DATASET_PRIORITY_MAP.get(raw_priority, "medium")
            item = MailboxItem(
                sender=sender,
                subject=subject,
                body=body,
                category="other",   # unknown without classification
                priority=priority,
                sla_hours=FALLBACK_SLA[priority],
                routed_to=row.get("queue", "General Ops Inbox"),
                suggested_reply=row.get("answer", "")[:500],
                status="open",
            )
            db.add(item)
            db.commit()
            print(f"  [ticket {i}] ingested, unclassified (priority={priority})")

    db.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed mailbox data from a public HF dataset.")
    parser.add_argument("--limit", type=int, default=20, help="Number of tickets to ingest")
    parser.add_argument("--classify", action="store_true", help="Run each ticket through the LLM classifier")
    parser.add_argument("--language", default="en", choices=["en", "de"], help="Ticket language to filter to")
    args = parser.parse_args()

    seed(limit=args.limit, do_classify=args.classify, language=args.language)
