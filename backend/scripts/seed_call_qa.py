"""
Seed the DB with real-shaped call transcripts from a public dataset, so the
Call QA dashboard has realistic data to show instead of empty tables.

Dataset: talkmap/telecom-conversation-corpus (Hugging Face, MIT license)
  - 3.7M rows of synthetic telecom customer-service dialogue, one row per
    speaker turn: {conversation_id, speaker (agent/client), date_time, text}
  - Synthetic data, so no PII/privacy concerns - safe to use freely.

Usage:
    cd backend
    python -m scripts.seed_call_qa --limit 20              # ingest only
    python -m scripts.seed_call_qa --limit 20 --score       # ingest + LLM QA score
    python -m scripts.seed_call_qa --limit 5 --score --agents 3

--score calls the LLM (costs a small amount / needs an API key set) - see
core/llm_client.py for provider config. Without --score, calls are stored
with a transcript but no QAScore (dashboard will just show them unscored).
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import init_db, SessionLocal
from db.models import Agent, Call, QAScore

DEMO_AGENT_NAMES = [
    ("Priya Sharma", "priya.sharma@company.com"),
    ("Rohan Mehta", "rohan.mehta@company.com"),
    ("Ananya Iyer", "ananya.iyer@company.com"),
    ("Karan Verma", "karan.verma@company.com"),
]


def get_or_create_demo_agents(db, count: int):
    agents = db.query(Agent).filter(Agent.team == "Delivery Ops (seeded)").all()
    if len(agents) >= count:
        return agents[:count]
    existing_emails = {a.email for a in agents}
    for name, email in DEMO_AGENT_NAMES[:count]:
        if email not in existing_emails:
            a = Agent(name=name, email=email, team="Delivery Ops (seeded)")
            db.add(a)
    db.commit()
    return db.query(Agent).filter(Agent.team == "Delivery Ops (seeded)").all()[:count]


def fetch_conversations(limit: int):
    """
    Streams the dataset and reconstructs full transcripts by grouping rows
    that share a conversation_id (rows for the same conversation are
    contiguous in this dataset). Uses streaming mode so we never download
    the full ~738MB dataset - we just pull what we need.
    """
    from datasets import load_dataset

    print(f"Streaming talkmap/telecom-conversation-corpus (need {limit} conversations)...")
    ds = load_dataset("talkmap/telecom-conversation-corpus", split="train", streaming=True)

    conversations = {}   # cid -> list of (speaker, text)
    order = []            # cids in first-seen order

    for row in ds:
        cid = row["conversation_id"]
        if cid not in conversations:
            if len(order) >= limit:
                # We've already collected enough distinct conversations and
                # this is a new one starting - safe to stop.
                break
            order.append(cid)
            conversations[cid] = []
        conversations[cid].append((row["speaker"], row["text"]))

    transcripts = []
    for cid in order[:limit]:
        turns = conversations[cid]
        lines = [f"{'Agent' if spk == 'agent' else 'Customer'}: {text}" for spk, text in turns]
        transcripts.append("\n".join(lines))
    return transcripts


def seed(limit: int, do_score: bool, num_agents: int):
    init_db()
    db = SessionLocal()

    agents = get_or_create_demo_agents(db, num_agents)
    print(f"Using {len(agents)} agent(s): {[a.name for a in agents]}")

    transcripts = fetch_conversations(limit)
    print(f"Fetched {len(transcripts)} transcripts.")

    if do_score:
        from call_qa.scorer import score_and_explain
        from tasks.service import create_task_from_qa_flag

    for i, transcript in enumerate(transcripts):
        agent = agents[i % len(agents)]
        call = Call(agent_id=agent.id, transcript=transcript)
        db.add(call)
        db.commit()
        db.refresh(call)

        if do_score:
            try:
                result = score_and_explain(transcript)
            except Exception as e:
                print(f"  [call {call.id}] scoring failed: {e}")
                continue

            qa = QAScore(
                call_id=call.id,
                overall_score=result["overall_score"],
                greeting_score=result["greeting_score"],
                compliance_score=result["compliance_score"],
                resolution_score=result["resolution_score"],
                tone_score=result["tone_score"],
                sentiment=result["sentiment"],
                flagged=result["flagged"],
                violations=result.get("violations", []),
                coaching_notes=result.get("coaching_notes", ""),
                raw_llm_response=result.get("raw_llm_response", {}),
            )
            db.add(qa)
            db.commit()
            db.refresh(qa)
            if qa.flagged:
                create_task_from_qa_flag(db, qa)
            print(f"  [call {call.id}] scored {qa.overall_score} ({agent.name})")
        else:
            print(f"  [call {call.id}] ingested, unscored ({agent.name})")

    db.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed call QA data from a public HF dataset.")
    parser.add_argument("--limit", type=int, default=20, help="Number of conversations to ingest")
    parser.add_argument("--score", action="store_true", help="Run each transcript through the LLM QA scorer")
    parser.add_argument("--agents", type=int, default=4, help="Number of demo agents to distribute calls across")
    args = parser.parse_args()

    seed(limit=args.limit, do_score=args.score, num_agents=args.agents)
