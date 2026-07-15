"""
Mailbox Classifier
------------------
Classifies incoming "Delivery mailbox" emails into categories, assigns
priority/SLA, drafts a reply for common categories, and routes anything
that needs a human to the right stakeholder.
"""
import json
from typing import Optional
from core.llm_client import call_llm

CATEGORIES = ["complaint", "status_check", "escalation", "info_request", "other"]

SLA_HOURS = {
    "escalation": 4,
    "complaint": 12,
    "status_check": 24,
    "info_request": 24,
    "other": 48,
}

PRIORITY_MAP = {
    "escalation": "high",
    "complaint": "high",
    "status_check": "medium",
    "info_request": "low",
    "other": "low",
}

ROUTING_MAP = {
    "escalation": "Operations Lead",
    "complaint": "Quality Team",
    "status_check": "Delivery Coordination",
    "info_request": "Delivery Coordination",
    "other": "General Ops Inbox",
}

CLASSIFY_PROMPT = """You are a mailbox triage assistant for a delivery operations team. Classify the email below and draft a reply.

Categories: complaint, status_check, escalation, info_request, other
- complaint: customer unhappy about service/delivery quality, no urgent safety issue
- escalation: urgent, needs immediate manager attention (repeated failures, threats to cancel, legal/compliance mention)
- status_check: customer just asking where their delivery/order is
- info_request: general question about policy, process, hours, etc.
- other: anything that doesn't fit above

Respond ONLY with valid JSON:
{
  "category": "<one of the categories above>",
  "confidence": <0-1 float>,
  "suggested_reply": "<a professional, concise draft reply, 2-4 sentences. For escalation/complaint, draft an acknowledgment only - do not promise specific resolutions>",
  "reasoning": "<one sentence on why this category>"
}

EMAIL SUBJECT: {subject}
EMAIL BODY:
{body}
"""


def classify_email(subject: str, body: str, model: Optional[str] = None) -> dict:
    prompt = CLASSIFY_PROMPT.replace("{subject}", subject).replace("{body}", body)

    raw_text = call_llm(prompt, max_tokens=600, model=model)
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    parsed = json.loads(raw_text)
    category = parsed.get("category", "other")
    if category not in CATEGORIES:
        category = "other"

    return {
        "category": category,
        "priority": PRIORITY_MAP[category],
        "sla_hours": SLA_HOURS[category],
        "routed_to": ROUTING_MAP[category],
        "suggested_reply": parsed.get("suggested_reply", ""),
        "reasoning": parsed.get("reasoning", ""),
        "confidence": parsed.get("confidence", 0.0),
    }


if __name__ == "__main__":
    sample_subject = "Package not delivered - 3rd time this week!!"
    sample_body = (
        "This is the third time my delivery has been late this week. "
        "I need a manager to call me back today or I'm cancelling my account."
    )
    result = classify_email(sample_subject, sample_body)
    print(json.dumps(result, indent=2))
