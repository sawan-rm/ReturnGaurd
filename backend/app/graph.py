"""
graph.py - LangGraph AI Agent Workflow for ReturnGuard

Agents:
  1. data_gatherer   - Fetches order + return history from DB
  2. fraud_detector  - LLM-powered fraud scoring
  3. policy_engine   - Deterministic policy check (return window, etc.)
  4. decision_maker  - Final LLM verdict: approve / escalate / deny
"""

import os
import json
import base64
import httpx
from datetime import datetime, timezone
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage


# ── 1. Agent State ───────────────────────────────────────────────────────────

class AgentState(TypedDict):
    return_id: str
    reason: str
    photo_url: Optional[str]
    product_name: str
    product_category: str
    amount: float
    days_since_order: int
    past_return_count: int
    fraud_score: float           # 0-100 (0 = clean, 100 = very suspicious)
    policy_ok: bool              # True if within return window
    final_decision: Optional[str]   # "approved" | "denied" | "escalated"
    explanation: str


# Models tried in order — if the first is unavailable, the next is used
MODEL_FALLBACK_CHAIN = [
    "gemini-3.8-flash",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
]


def _get_llm(model: str | None = None):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    chosen = model or MODEL_FALLBACK_CHAIN[0]
    return ChatGoogleGenerativeAI(
        model=chosen,
        google_api_key=api_key,
        temperature=0.2,
    )


def _invoke_with_fallback(content: list | str) -> str:
    """Try each model in the fallback chain. Return raw text or raise."""
    last_error = None
    for model_name in MODEL_FALLBACK_CHAIN:
        try:
            llm = _get_llm(model_name)
            response = llm.invoke([HumanMessage(content=content)])
            print(f"✅ LLM call succeeded with model: {model_name}")
            return response.content.strip()
        except Exception as e:
            print(f"⚠️  Model {model_name} failed: {e}. Trying next...")
            last_error = e
    raise RuntimeError(f"All models failed. Last error: {last_error}")


# ── 2. Agent Nodes ───────────────────────────────────────────────────────────

def fraud_detector(state: AgentState) -> AgentState:
    """Ask Gemini to evaluate the fraud risk of this return."""
    prompt = f"""You are a fraud analyst for an e-commerce return system.
Evaluate the risk of this return request and return a JSON object only.

Return details:
- Product: {state['product_name']} (Category: {state['product_category']})
- Order amount: ${state['amount']:.2f}
- Days since purchase: {state['days_since_order']}
- Customer's stated reason: "{state['reason']}"
- Customer's past return count (last 6 months): {state['past_return_count']}

Respond ONLY with a JSON object like this (no markdown, no extra text):
{{"fraud_score": <number 0-100>, "reasoning": "<one sentence>"}}

Rules for scoring:
- High-value electronics with vague reasons -> high score (70-100)
- Normal wear/size reasons with cheap items -> low score (0-20)
- Many past returns -> add 15 points
- Very late return (>25 days) -> add 10 points
- If a photo is provided and it DOES NOT match the damage claim -> add 40 points
- If a photo is provided and it clearly shows the damage -> subtract 20 points"""

    content = [{"type": "text", "text": prompt}]

    if state.get("photo_url"):
        try:
            # Replace localhost with minio since worker runs inside docker network
            internal_url = state["photo_url"].replace("localhost", "minio")
            img_data = httpx.get(internal_url).content
            b64_image = base64.b64encode(img_data).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
            })
            print(f"📸 Attached photo to fraud_detector LLM prompt")
        except Exception as e:
            print(f"⚠️ Could not load photo for LLM: {e}")

    try:
        raw = _invoke_with_fallback(content)
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        fraud_score = float(data.get("fraud_score", 50))
    except Exception as e:
        print(f"⚠️  Fraud detector error: {e}. Defaulting to score 50.")
        fraud_score = 50.0

    return {**state, "fraud_score": fraud_score}


def policy_engine(state: AgentState) -> AgentState:
    """Deterministic policy: return must be within 30 days."""
    RETURN_WINDOW_DAYS = 30
    policy_ok = state["days_since_order"] <= RETURN_WINDOW_DAYS
    return {**state, "policy_ok": policy_ok}


def decision_maker(state: AgentState) -> AgentState:
    """Apply business rules then ask Gemini to write the explanation."""
    fraud_score = state["fraud_score"]
    policy_ok = state["policy_ok"]

    # Deterministic routing
    if not policy_ok:
        final_decision = "denied"
    elif fraud_score >= 70:
        final_decision = "escalated"
    else:
        final_decision = "approved"

    llm = _get_llm()
    prompt = f"""You are a friendly customer support manager writing a return decision letter.

Product: {state['product_name']}
Amount: ${state['amount']:.2f}
Customer's reason: "{state['reason']}"
Days since purchase: {state['days_since_order']}
Fraud risk score: {fraud_score:.0f}/100
Policy window (30 days): {"WITHIN window" if policy_ok else "OUTSIDE window"}
Decision: {final_decision.upper()}

Write a single, professional, empathetic 2-sentence explanation for the customer.
Do NOT start with "Dear" or use any salutation. Just the explanation."""

    try:
        explanation = _invoke_with_fallback(prompt)
    except Exception as e:
        print(f"⚠️  Decision maker LLM error: {e}. Using fallback explanation.")
        explanations = {
            "approved": "Your return request has been approved based on our review. A refund will be processed to your original payment method within 5-7 business days.",
            "denied": f"Unfortunately your return request cannot be approved as the {state['days_since_order']}-day return window has closed. Our policy allows returns within 30 days of purchase.",
            "escalated": "Your return request has been flagged for manual review by our team. A representative will contact you within 24 hours.",
        }
        explanation = explanations[final_decision]

    return {**state, "final_decision": final_decision, "explanation": explanation}


# ── 3. Build & Compile the Graph ─────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fraud_detector", fraud_detector)
    graph.add_node("policy_engine", policy_engine)
    graph.add_node("decision_maker", decision_maker)

    # Run fraud detection and policy check in sequence, then decide
    graph.set_entry_point("fraud_detector")
    graph.add_edge("fraud_detector", "policy_engine")
    graph.add_edge("policy_engine", "decision_maker")
    graph.add_edge("decision_maker", END)

    return graph.compile()


# Compiled graph (singleton, imported by worker)
return_graph = build_graph()
