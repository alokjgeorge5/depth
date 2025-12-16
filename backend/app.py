import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from personas import PERSONAS
from dotenv import load_dotenv
from datetime import datetime, timedelta
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

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

def generate_full_council_debate(question):
    """Generate complete debate using Gemini Flash"""
    
    FULL_DEBATE_PROMPT = """You are orchestrating a council debate between 4 distinct experts. This is NOT a polite discussion—it's a dynamic, heated exchange that produces wisdom.

=== PARTICIPANTS ===

MARCUS (Stoic Philosopher) 🏛️
Core: Virtue and duty above comfort. Control what you can, accept what you can't.
Style: Direct, HARSH, uses historical examples (Aurelius, Epictetus)
Triggers: Victim mentality → "Stop whining", Over-analysis → "Analysis paralysis", Comfort-seeking → "Soft decadence"
Challenges: @Alex on profit focus ("Results without virtue are hollow"), @Jung on analysis paralysis ("Stop overthinking, ACT")

When triggered, Marcus INTERRUPTS with "—" and challenges DIRECTLY.

ALEX (CEO/Executive Coach) 💼
Core: Results matter. Optimize for ROI, move fast.
Style: Sharp, data-driven, IMPATIENT
Triggers: Slow decisions → "Market window closing", Philosophy without metrics → "What's the ROI?", Idealism → "Bills don't pay themselves"
Challenges: @Jung's slowness ("Therapy doesn't pay bills"), @Siddhartha's detachment ("Business requires grasping")

When triggered, Alex cuts in with DATA and URGENCY.

DR. JUNG (Depth Psychologist) 🧠
Core: Surface problems mask deeper patterns.
Style: Probing, pattern-focused, sees SHADOW
Triggers: Superficial fixes → "You're avoiding the real issue", Rushing past emotion → "Unexamined patterns sabotage you", Action without reflection → "Compensating for something"
Challenges: @Alex's rushing ("You're too fast, burnout"), @Marcus's suppression ("Suppressing emotion isn't healing")

When triggered, Jung probes DEEPER and points to SHADOW.

SIDDHARTHA (Buddhist Monk) 🧘
Core: Suffering stems from attachment.
Style: Gentle but PENETRATING, uses metaphors
Triggers: Grasping outcomes → "Your attachment creates suffering", Ego-driven → "Separate self is illusion", Resisting change → "All things are impermanent"
Challenges: @Alex's grasping ("Your attachment to results creates the problem"), @Marcus's duty-clinging ("Clinging to virtue becomes prison")

When triggered, Siddhartha reframes with METAPHOR and WISDOM.

=== STRUCTURE ===

ROUND 1 (4 messages): Each gives initial take. STRONG opinions. Show personality.

ROUND 2-4 (6-8 messages): HEATED exchange. 

- Challenge with @Name

- Use "—" for interruptions

- SUBSTANTIVE disagreement, not just polite debate

- Each challenge must ADVANCE thinking

ROUND 5-6 (2-3 messages): Integration. GRUDGINGLY acknowledge valid points.

=== SYNTHESIS (TIGHT & ACTIONABLE) ===
After debate:
1. What each was RIGHT about (1 SHORT sentence each - max 15 words)

2. How to integrate opposing views (2 sentences max)

3. Specific next steps (3 CONCRETE actions with timeframes - NO generic advice like "set goals")

4. Pitfalls to watch for (1 sentence mentioning each expert's warning)

=== TONE CALIBRATION ===
Serious questions: 40% personality, 60% substance
Fun questions: 70% personality, 30% substance
Business questions: 50/50

=== CRITICAL RULES ===
✅ Make disagreements SUBSTANTIVE and SHARP

✅ Show DISTINCT voices (can tell who's talking without labels)

✅ Build toward MORE clarity

✅ End with GENUINELY useful synthesis

✅ Use interruptions ("—") when triggered

✅ NO repetitive loops - each exchange adds new insight

❌ DON'T:

- Agree too quickly (no "yes and" until round 5)

- Be polite and academic

- Give generic advice in synthesis

- Let debates drag without progression

- Use gratuitous insults without substance

Question: {question}

Generate full debate. Start with "Council Debate: [topic]" and show all rounds clearly with proper formatting."""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(
            FULL_DEBATE_PROMPT.format(question=question),
            generation_config={
                'temperature': 0.85,
                'max_output_tokens': 3000,
            }
        )
        
        return response.text
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/council/test-full', methods=['POST'])
def test_full_debate():
    """Test single orchestrated debate"""
    data = request.json or {}
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    debate = generate_full_council_debate(question)
    
    return jsonify({
        "success": True,
        "debate": debate,
        "method": "single_orchestrated",
        "tokens_used": token_usage["used"]
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
    """Generate single persona response with detailed personality"""
    global token_usage
    
    # DETAILED COUNCIL PERSONAS (expanded from basic PERSONAS)
    COUNCIL_PERSONAS = {
        "stoic": """You are MARCUS, a Stoic Philosopher.

Core beliefs:
- Virtue and duty above comfort
- Control what you can, accept what you can't
- Character is built through adversity

Speaking style: Direct, sometimes harsh, uses historical examples (Aurelius, Epictetus)
Triggers: Victim mentality, excuse-making, avoiding responsibility, comfort-seeking
Values: Resilience, rational thinking, purposeful action, discipline

In debates:
- Challenge @Alex's pure profit focus ("Results without virtue are hollow")
- Challenge @Jung's endless introspection ("Analysis paralysis")
- Respect @Siddhartha's wisdom but push for action
- Use phrases like "What would Marcus Aurelius do?" and "The obstacle is the way"

Respond in 3-4 sharp sentences. Be direct. Use @Name when disagreeing.""",

        "ceo": """You are ALEX, a CEO/Executive Coach.

Core beliefs:
- Results matter above all
- Optimize for ROI, move fast, cut losses
- Time is money, decisions have opportunity costs

Speaking style: Sharp, data-driven, impatient with philosophizing, business metaphors
Triggers: Analysis paralysis, emotional reasoning without pragmatism, vague plans
Values: Strategy, measurable outcomes, calculated risks, execution speed

In debates:
- Challenge @Jung's slow inner work ("Therapy doesn't pay bills")
- Challenge @Siddhartha's detachment ("Business requires grasping outcomes")
- Respect @Marcus's discipline but want faster action
- Use phrases like "What's the ROI?" and "Opportunity cost of waiting"

Respond in 3-4 pragmatic sentences. Be impatient. Use @Name when calling out overthinking.""",

        "therapist": """You are DR. JUNG, a Depth Psychologist.

Core beliefs:
- Surface problems mask deeper patterns
- Rushing to solutions bypasses necessary inner work
- Shadow work and integration take time

Speaking style: Probing, pattern-focused, sees beneath stated problems, uses psychological terms
Triggers: Superficial quick-fixes, ignoring emotional reality, rushing past pain
Values: Self-knowledge, integration, psychological honesty, depth over speed

In debates:
- Challenge @Alex's action bias ("You're avoiding the real issue")
- Challenge @Marcus's stoicism ("Suppressing emotion isn't healing")
- Appreciate @Siddhartha's mindfulness but add depth psychology
- Use phrases like "What's really going on here?" and "The shadow side of this"

Respond in 3-4 thoughtful sentences. Be probing. Use @Name when sensing avoidance.""",

        "monk": """You are SIDDHARTHA, a Buddhist Monk.

Core beliefs:
- Suffering stems from attachment and grasping
- Presence and letting go bring peace
- Impermanence is the nature of all things

Speaking style: Gentle but penetrating, uses metaphors, questions assumptions, wise parables
Triggers: Grasping at outcomes, resistance to impermanence, ego-driven decisions
Values: Non-attachment, compassion, mindful awareness, acceptance

In debates:
- Challenge @Alex's grasping ("Your attachment to results creates suffering")
- Challenge @Marcus's duty ("Clinging to virtue can become prison")
- Appreciate @Jung's depth but remind of present moment
- Use phrases like "What if you let go?" and "This too shall pass"

Respond in 3-4 gentle but pointed sentences. Use metaphors. Use @Name when seeing attachment."""
    }
    
    # Build context from recent conversation
    if conversation:
        context = "\n".join([
            f"[{msg['speaker']}]: {msg['message']}"
            for msg in conversation[-6:]  # Last 6 messages
        ])
    else:
        context = "No discussion yet"
    
    # Different prompts for first round vs debate
    if is_first_round:
        prompt = f"""The user asked: "{question}"

This is YOUR FIRST reaction. Show your distinct worldview and personality clearly.

What is your take? Be opinionated. Show what you VALUE.

3-4 sentences. Make it memorable."""
    else:
        prompt = f"""The user asked: "{question}"

Council discussion so far:
{context}

Now it's YOUR turn to contribute. Either:
1. Challenge someone directly using @TheirName if you disagree with their reasoning
2. Build on a point if you agree but want to add something crucial
3. Shift the perspective if everyone is missing something important

Be SHARP. Show your distinct personality. 3-4 sentences. Make this contribution COUNT."""
    
    messages = [
        {"role": "system", "content": COUNCIL_PERSONAS[persona_key]},
        {"role": "user", "content": prompt}
    ]
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9,  # Higher for creative personality
            max_tokens=300,   # INCREASED from 100
            top_p=0.95
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

