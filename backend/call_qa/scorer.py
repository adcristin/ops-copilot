"""
Call QA Scorer
--------------
Takes a call transcript + a rubric, sends it to an LLM, and gets back
a structured JSON evaluation. This mirrors what Observe.AI / Level AI call
"Auto QA" - the same rubric-scoring pattern, minus the enterprise infra.

LLM backend is provider-agnostic - see core/llm_client.py to switch between
Anthropic direct and OpenRouter.
"""
import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field, ValidationError
from core.llm_client import call_llm

class Violation(BaseModel):
    category: str
    quote: str
    note: str

class RubricResult(BaseModel):
    greeting_score: int = Field(ge=0, le=100)
    compliance_score: int = Field(ge=0, le=100)
    resolution_score: int = Field(ge=0, le=100)
    tone_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    sentiment: str
    violations: List[Violation]
    coaching_notes: str

RUBRIC_PROMPT = """You are a call center QA analyst. Evaluate the following customer service call transcript against these criteria. Be strict and evidence-based - only flag violations you can point to directly in the transcript.

CRITERIA (score each 0-100):
1. Greeting & Opening - Did the agent identify themselves, the company, and offer to help clearly?
2. Compliance - Did the agent avoid prohibited statements, follow required disclosures, and stay within policy?
3. Resolution - Was the customer's issue actually resolved or a clear next step given?
4. Tone & Empathy - Was the agent's tone professional, patient, and empathetic (not curt or dismissive)?

Also determine:
- Overall sentiment of the call (positive/neutral/negative)
- Any specific violations (quote the exact line, category, and a one-line note on why it's a violation)
- 2-3 sentences of coaching feedback for the agent

Respond ONLY with valid JSON in this exact structure, no other text:
{
  "greeting_score": <int 0-100>,
  "compliance_score": <int 0-100>,
  "resolution_score": <int 0-100>,
  "tone_score": <int 0-100>,
  "overall_score": <int 0-100, weighted average>,
  "sentiment": "<positive|neutral|negative>",
  "violations": [
    {"category": "<compliance|tone|resolution|greeting>", "quote": "<exact quote>", "note": "<why this is a problem>"}
  ],
  "coaching_notes": "<2-3 sentences of actionable feedback>"
}

TRANSCRIPT:
{transcript}
"""

FLAG_THRESHOLD = 70  # overall_score below this gets auto-flagged for manager review


def score_transcript(transcript: str, model: Optional[str] = None) -> dict:
    """
    Send a transcript to the LLM and get back a structured QA score.
    Returns a dict matching the QAScore model fields (minus call_id/scored_at).
    """
    prompt = RUBRIC_PROMPT.replace("{transcript}", transcript)

    raw_text = call_llm(prompt, max_tokens=1000, model=model)

    # Improved JSON extraction: find the first '{' and last '}'
    start_idx = raw_text.find('{')
    end_idx = raw_text.rfind('}')

    if start_idx == -1 or end_idx == -1:
        raise ValueError(f"LLM response did not contain a JSON object.\nRaw output: {raw_text}")

    json_text = raw_text[start_idx:end_idx + 1]

    try:
        # Parse and validate with Pydantic
        parsed_obj = RubricResult.model_validate_json(json_text)
        parsed = parsed_obj.model_dump()
    except ValidationError as e:
        raise ValueError(f"LLM returned JSON that failed validation: {e}\nRaw output: {raw_text}")
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output: {raw_text}")

    parsed["flagged"] = parsed.get("overall_score", 100) < FLAG_THRESHOLD
    parsed["raw_llm_response"] = parsed.copy()
    return parsed


def score_and_explain(transcript: str) -> dict:
    """Convenience wrapper - use this from the API layer."""
    result = score_transcript(transcript)
    return result


if __name__ == "__main__":
    # Quick manual test with a sample transcript
    logging.basicConfig(level=logging.INFO)
    sample = """
    Agent: Yeah hi, uh, what do you want?
    Customer: Hi, I'm calling about my delivery, it's been delayed 3 days now.
    Agent: Okay let me check... yeah it's delayed. Nothing I can do about it honestly.
    Customer: Can I at least get a refund or some compensation?
    Agent: Not really our policy. You'll have to just wait it out.
    Customer: This is really frustrating.
    Agent: I understand but there's nothing more I can do. Anything else?
    """
    result = score_and_explain(sample)
    logging.info(f"Result: {json.dumps(result, indent=2)}")
