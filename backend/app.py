import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from personas import PERSONAS
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Token tracking (simple in-memory for now)
token_usage = {
    "used": 0,
    "limit": 100000,
    "reset_time": None
}

def estimate_tokens(text):
    """Rough estimate: 1 token ≈ 4 characters"""
    return len(text) // 4

def check_usage():
    """Check if we're approaching or at limit"""
    usage_percent = (token_usage["used"] / token_usage["limit"]) * 100
    
    if usage_percent >= 100:
        return {
            "status": "exceeded",
            "message": "Daily limit reached. Please try again later or upgrade.",
            "reset_in_minutes": 60  # Placeholder
        }
    elif usage_percent >= 90:
        return {
            "status": "warning",
            "message": f"Approaching daily limit ({int(usage_percent)}% used)",
            "remaining": token_usage["limit"] - token_usage["used"]
        }
    else:
        return {"status": "ok", "usage_percent": int(usage_percent)}

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    persona = data.get("persona")
    message = data.get("message")
    history = data.get("history", [])

    if persona not in PERSONAS:
        return jsonify({"error": "Invalid persona"}), 400
    if not message:
        return jsonify({"error": "Message required"}), 400

    # Check usage before processing
    usage_check = check_usage()
    if usage_check["status"] == "exceeded":
        return jsonify({
            "error": "rate_limit_exceeded",
            "message": "You've reached the daily free limit (100k tokens).",
            "suggestions": [
                "Wait ~1 hour for limit reset",
                "Upgrade to unlimited access (coming soon)",
                "Use shorter conversations to conserve tokens"
            ],
            "usage": usage_check
        }), 429

    messages = [{"role": "system", "content": PERSONAS[persona]}] + history + [
        {"role": "user", "content": message}
    ]

    # Estimate tokens for this request
    estimated_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            max_tokens=512,
            top_p=0.9,
        )
        
        reply = completion.choices[0].message.content
        
        # Update token usage tracking
        actual_tokens = completion.usage.total_tokens
        token_usage["used"] += actual_tokens
        
        # Check if warning needed after this request
        post_usage = check_usage()
        
        response = {
            "reply": reply,
            "usage": {
                "status": post_usage["status"],
                "tokens_used": token_usage["used"],
                "tokens_limit": token_usage["limit"],
                "percent": int((token_usage["used"] / token_usage["limit"]) * 100)
            }
        }
        
        # Add warning if approaching limit
        if post_usage["status"] == "warning":
            response["warning"] = post_usage["message"]
        
        return jsonify(response)
    
    except Exception as e:
        error_msg = str(e)
        
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": "Groq API daily limit reached (100k tokens).",
                "suggestions": [
                    "Wait ~1 hour for automatic reset",
                    "Upgrade to paid tier for unlimited access",
                    "Try again with shorter messages"
                ],
                "upgrade_link": "https://console.groq.com/settings/billing"
            }), 429
        else:
            return jsonify({
                "error": "api_error",
                "message": "Something went wrong. Please try again.",
                "details": error_msg
            }), 500

@app.route("/usage", methods=["GET"])
def get_usage():
    """Endpoint to check current usage"""
    usage_check = check_usage()
    return jsonify({
        "used": token_usage["used"],
        "limit": token_usage["limit"],
        "percent": int((token_usage["used"] / token_usage["limit"]) * 100),
        "status": usage_check["status"]
    })

@app.route("/council/debate", methods=["POST"])
def council_debate():
    """
    New endpoint for council debate feature.
    All 4 personas debate the user's question.
    """
    data = request.json or {}
    question = data.get("question")
    max_turns = 10  # Hard cap on debate length
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    # Check usage before processing
    usage_check = check_usage()
    if usage_check["status"] == "exceeded":
        return jsonify({
            "error": "rate_limit_exceeded",
            "message": "Daily limit reached."
        }), 429
    
    # Define council members (same personas, different names for debate)
    council_members = {
        "stoic": {"name": "Marcus", "persona_key": "stoic"},
        "ceo": {"name": "Alex", "persona_key": "ceo"},
        "therapist": {"name": "Dr. Jung", "persona_key": "therapist"},
        "monk": {"name": "Siddhartha", "persona_key": "monk"}
    }
    
    conversation = []
    turn_count = 0
    
    # ROUND 1: Everyone speaks once (4 API calls)
    for member_id, member in council_members.items():
        response = generate_council_response(
            member["persona_key"],
            question,
            conversation,
            is_first_round=True
        )
        
        conversation.append({
            "speaker": member["name"],
            "persona_id": member_id,
            "message": response,
            "turn": turn_count + 1
        })
        turn_count += 1
    
    # ROUNDS 2-3: Debate continues if needed (max 6 more turns)
    while turn_count < max_turns:
        # Check if should continue (moderator call)
        should_continue = check_debate_needed(conversation[-4:], question)
        if not should_continue:
            break
        
        # Find next speaker (not same as last 2)
        next_speaker_id = find_next_speaker(conversation, list(council_members.keys()))
        if not next_speaker_id:
            break
        
        next_member = council_members[next_speaker_id]
        response = generate_council_response(
            next_member["persona_key"],
            question,
            conversation,
            is_first_round=False
        )
        
        conversation.append({
            "speaker": next_member["name"],
            "persona_id": next_speaker_id,
            "message": response,
            "turn": turn_count + 1
        })
        turn_count += 1
    
    # FINAL: Synthesis (1 API call)
    synthesis = generate_synthesis(question, conversation)
    conversation.append({
        "speaker": "Council",
        "persona_id": "synthesis",
        "message": synthesis,
        "turn": turn_count + 1
    })
    
    return jsonify({
        "success": True,
        "conversation": conversation,
        "total_turns": len(conversation)
    })

def generate_council_response(persona_key, question, conversation, is_first_round=False):
    """Generate single persona response for council debate"""
    global token_usage
    
    # Build context from recent messages
    context = "\n".join([
        f"[{msg['speaker']}]: {msg['message'][:100]}..."
        for msg in conversation[-6:]  # Last 6 messages only
    ])
    
    if is_first_round or len(conversation) == 0:
        prompt = f"""User asked: "{question}"

Give your direct perspective (2 sentences max). Show your personality clearly."""
    else:
        prompt = f"""User asked: "{question}"

Recent discussion:

{context}

Add to conversation. Challenge someone with @Name if you disagree, or build on their point.

2 sentences max. Be sharp and direct."""
    
    messages = [
        {"role": "system", "content": PERSONAS[persona_key]},
        {"role": "user", "content": prompt}
    ]
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.8,  # Higher for personality
            max_tokens=100,   # Force brevity
            top_p=0.9
        )
        
        reply = completion.choices[0].message.content
        
        # Update token usage
        actual_tokens = completion.usage.total_tokens
        token_usage["used"] += actual_tokens
        
        return reply.strip()
        
    except Exception as e:
        return f"[Error: {str(e)[:50]}]"

def check_debate_needed(recent_messages, question):
    """Moderator decides if debate should continue"""
    context = "\n".join([
        f"[{msg['speaker']}]: {msg['message'][:80]}..."
        for msg in recent_messages
    ])
    
    prompt = f"""Recent council discussion on "{question}":

{context}

Should they continue debating (unresolved disagreement) or stop now (consensus reached)?

Answer ONLY: CONTINUE or STOP"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.3
        )
        
        decision = completion.choices[0].message.content.upper()
        
        # Update token usage
        actual_tokens = completion.usage.total_tokens
        token_usage["used"] += actual_tokens
        
        return "CONTINUE" in decision
        
    except:
        return False  # Default to stopping on error

def find_next_speaker(conversation, all_persona_ids):
    """Pick next speaker (avoid repetition)"""
    if len(conversation) < 3:
        return all_persona_ids[0] if all_persona_ids else None
    
    # Get last 3 speakers
    recent_speakers = [msg["persona_id"] for msg in conversation[-3:]]
    
    # Pick first persona that hasn't spoken recently
    for persona_id in all_persona_ids:
        if persona_id not in recent_speakers:
            return persona_id
    
    # If all spoke recently, return first
    return all_persona_ids[0] if all_persona_ids else None

def generate_synthesis(question, conversation):
    """Generate final council conclusion"""
    context = "\n".join([
        f"[{msg['speaker']}]: {msg['message']}"
        for msg in conversation[-8:]  # Last 8 messages
    ])
    
    prompt = f"""User asked: "{question}"

Council discussion:

{context}

Synthesize into actionable conclusion (3 sentences):
1. Key insight from the debate
2. Concrete next step
3. Main tradeoff to consider

Start with "Council Consensus:" """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.6
        )
        
        # Update token usage
        actual_tokens = completion.usage.total_tokens
        token_usage["used"] += actual_tokens
        
        return completion.choices[0].message.content.strip()
        
    except:
        return "Council consensus: Consider all perspectives shared and decide based on your values."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

