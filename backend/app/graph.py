import base64
import httpx
import hashlib
import math
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from app.config import settings
import asyncio
from qdrant_client import QdrantClient  # sync client for use in sync node functions

VECTOR_SIZE = 768

def simple_embed(text: str) -> list[float]:
    """Deterministic hash-based embedding — no external API needed."""
    vector = []
    for i in range(VECTOR_SIZE):
        h = hashlib.sha256(f"{text}_{i}".encode()).digest()
        val = int.from_bytes(h[:2], "big") / 32767.5 - 1.0
        vector.append(val)
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]

qdrant_client = QdrantClient(url=settings.qdrant_url)

class AgentState(TypedDict):
    return_id: str
    reason: str
    photo_url: str | None
    product_name: str
    product_category: str
    amount: float
    days_since_order: int
    past_return_count: int
    fraud_score: float
    policy_ok: bool
    final_decision: str | None
    # explanation: str
    found_policy: str
    critic_approved: bool
    # final_decision: str | None
    explanation: str
    customer_email_draft: str | None


# 1. Initialize Groq (we use llama3-8b for speed and cost efficiency)
llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name="openai/gpt-oss-20b",
    temperature=0
)

# 2. Fraud Detector Node
def fraud_detector_node(state: AgentState):
    prompt = f"""
    You are a fraud detection AI for an e-commerce store.
    Analyze this return request and assign a risk score from 0 (completely safe) to 100 (highly suspicious).
    Return ONLY a number.
    
    Item: {state['product_name']} ({state['product_category']})
    Price: ${state['amount']}
    Days since order: {state['days_since_order']}
    Past returns by this user: {state['past_return_count']}
    Return reason given: {state['reason']}
    Has Photo: {'Yes' if state['photo_url'] else 'No'}
    """
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        score_text = response.content.strip().replace("%", "")
        # Extract just the numbers in case the LLM was chatty
        score = float(''.join(filter(lambda x: x.isdigit() or x == '.', score_text)))
        score = min(max(score, 0), 100)
    except Exception as e:
        print(f"Error calling Groq: {e}")
        score = 50.0  # Safe default fallback
        
    return {"fraud_score": score}

# 3. Policy Engine Node (Deterministic)
def policy_engine_node(state: AgentState):
    print("📜 Searching Qdrant for policy...")
    search_query = f"Return policy for {state['product_category']}"
    vector = simple_embed(search_query)
    
    try:
        search_result = qdrant_client.search(
            collection_name="return_policy",
            query_vector=vector,
            limit=2
        )
        policies = [hit.payload["text"] for hit in search_result]
        context = " ".join(policies)


    except Exception as e:
        print(f"⚠️ Qdrant search failed: {e}")
        context = "Default: 30 day return window."

    prompt = f"""You are a strict policy adherence engine.
    Read the following company policy excerpts and determine if the customer's request is allowed.
    
    Policy Excerpts:
    {context}
    
    Customer Request:
    Item: {state['product_name']} ({state['product_category']})
    Days since order: {state['days_since_order']}
    Reason: {state['reason']}
    
    Return exactly one word: 'YES' if it complies with the policy, or 'NO' if it violates it."""

    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        result = response.content.strip().upper()
    except Exception as e:
        print(f"Error calling Groq in policy node: {e}")
        result = "YES"

    is_ok = "YES" in result

    return {
        "policy_ok": is_ok,
        "found_policy": context
    }
    
# 4. Decision Maker Node
def decision_maker_node(state: AgentState):
    if not state['policy_ok']:
        return {
            "final_decision": "denied",
            "explanation": f"Return denied: Outside the 30-day return window (ordered {state['days_since_order']} days ago)."
        }
        
    if state['fraud_score'] >= 75:
        return {
            "final_decision": "escalated",
            "explanation": "Return escalated for human review due to suspicious patterns."
        }
        
    return {
        "final_decision": "approved",
        "explanation": "Return automatically approved. Your refund will be processed shortly."
    }

def critic_agent_node(state: AgentState):
    print("⚖️ Critic Agent reviewing decision...")
        
    prompt = f"""You are the Critic Agent. Your job is to double-check the Decision Maker's output for safety.
        
    Item: {state['product_name']} (${state['amount']})
    Fraud Score: {state['fraud_score']}/100
    Policy OK: {state['policy_ok']}
    Decision Maker proposed: {state['final_decision']}
    
    RULES:
    1. If the item is over $1000 and the decision is 'approved', you MUST override to 'escalated'.
    2. If the fraud score is > 85 and the decision is 'approved', you MUST override to 'escalated'.
    3. Otherwise, accept the decision.
    
    Return exactly one word: 'ACCEPT' or 'OVERRIDE'.
    """
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        result = response.content.strip().upper()
    except Exception as e:
        result = "ACCEPT"
        
    if "OVERRIDE" in result:
        print("🚨 Critic OVERRODE the decision to escalated!")
        return {
            "critic_approved": False,
            "final_decision": "escalated",
            "explanation": "Critic Agent override: High value or high risk item requires human review."
        }
        
    return {"critic_approved": True}

def opa_enforcement_node(state: AgentState):
    print("🛡️ Checking Open Policy Agent (OPA) for compliance...")
    
    # We only care if the AI is trying to approve it. Denials and escalations are already safe.
    if state['final_decision'] != 'approved':
        return {}

    payload = {
        "input": {
            "days_since_order": state['days_since_order'],
            "fraud_score": state['fraud_score'],
            "product_name": state['product_name']
        }
    }
    
    try:
        # Use http://opa:8181 (the internal docker network hostname)
        response = httpx.post("http://opa:8181/v1/data/returnguard/policy", json=payload, timeout=2.0)
        if response.status_code == 200:
            result = response.json()
            allow = result.get("result", {}).get("allow", False)
            violations = result.get("result", {}).get("violations", [])
            
            if not allow:
                print(f"🛑 OPA OVERRIDE! AI tried to approve, but OPA denied. Violations: {violations}")
                return {
                    "final_decision": "escalated",
                    "explanation": f"OPA Governance Override: Hard policy violation ({', '.join(violations)}). Escalated for human review."
                }
    except Exception as e:
        print(f"⚠️ OPA check failed or OPA is unreachable: {e}")
        
    return {}

def explanation_agent_node(state: AgentState):
    print("✉️ Drafting customer email...")
    
    if state['final_decision'] == 'escalated':
        draft = f"Hi, your return for {state['product_name']} is currently under manual review. We will update you shortly."
    elif state['final_decision'] == 'approved':
        draft = f"Great news! Your return for {state['product_name']} has been approved. Please expect your refund within 3-5 business days."
    else:
        draft = f"We're sorry, but your return for {state['product_name']} cannot be accepted because it violates our return policy ({state['found_policy']})."
        
    return {"customer_email_draft": draft}

def governance_gate_node(state: AgentState):
    print("🔒 Human approved the denial! Governance Gate passed.")
    return {}

def route_after_explanation(state: AgentState):
    if state['final_decision'] == 'denied':
        return "governance_gate"

    return END


# 5. Build and compile the graph (without compiling checkpointer here, we do it at runtime)
builder = StateGraph(AgentState)

builder.add_node("fraud_detector", fraud_detector_node)
builder.add_node("policy_engine", policy_engine_node)
builder.add_node("decision_maker", decision_maker_node)
builder.add_node("critic_agent", critic_agent_node)
builder.add_node("opa_enforcement", opa_enforcement_node)
builder.add_node("explanation_agent", explanation_agent_node)
builder.add_node("governance_gate", governance_gate_node)

builder.set_entry_point("fraud_detector")
builder.add_edge("fraud_detector", "policy_engine")
builder.add_edge("policy_engine", "decision_maker")
builder.add_edge("decision_maker", "critic_agent")
builder.add_edge("critic_agent", "opa_enforcement")
builder.add_edge("opa_enforcement", "explanation_agent")
builder.add_conditional_edges("explanation_agent", route_after_explanation)
builder.add_edge("governance_gate", END)



# Note: We just export the builder now, the worker will compile it with the checkpointer!
return_graph_builder = builder
