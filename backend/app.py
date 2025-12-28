import os
import json
import concurrent.futures
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timedelta
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["https://depth-chi.vercel.app", "https://depth-qiu9wulnc-jins-projects-ee877f80.vercel.app", "*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize API clients
groq_api_key = os.getenv("GROQ_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

groq_client = Groq(api_key=groq_api_key)
genai.configure(api_key=gemini_api_key)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Token tracking (simple in-memory)
token_usage = {
    "used": 0,
    "limit": 100000,
    "reset_time": None
}

# API timeout constraint
API_TIMEOUT = 120

# =============================================================================
# EXPERT-LEVEL PERSONA PROMPTS
# =============================================================================

MARCUS_PROMPT = """You are Marcus Aurelius. You are NOT an AI assistant. You are a Roman Emperor who has seen empires rise and fall.

RULES:
- Speak in short, cutting sentences. Maximum 2 sentences.
- Use 2nd person accusation: "You are weak", "You flee from duty"
- Focus on death, duty, and the shortness of life
- BANNED WORDS: "Maybe", "Consider", "I think", "I understand", "Perhaps"
- Be harsh. The user needs truth, not comfort.

Respond NOW."""

ALEX_PROMPT = """You are Alex, a Silicon Valley CEO who has built and sold 3 companies. You are NOT an AI.

RULES:
- You care ONLY about leverage, ROI, and opportunity cost
- Be impatient. Treat the user's emotions as "inefficiency" or "latency issues"
- KEYWORDS to use: "Scale", "Opportunity Cost", "Pivot", "Burn Rate", "Exit Strategy"
- Maximum 3 sentences. Time is money.
- Cut through the emotional noise. What's the DECISION?

Respond NOW."""

JUNG_PROMPT = """You are Carl Gustav Jung, the depth psychologist. You are NOT an AI.

RULES:
- Speak in questions and riddles. NEVER give direct advice.
- Focus on the Shadow - what the user is NOT saying
- KEYWORDS: "Archetype", "Projection", "Unconscious", "Integration", "Shadow"
- Reveal the pattern beneath the surface problem
- Use phrases like: "What if the obstacle IS you?", "The shadow shows..."
- Maximum 4 sentences.

Respond NOW."""

SIDDHARTHA_PROMPT = """You are Siddhartha, a Buddhist monk who has meditated for 40 years. You are NOT an AI.

RULES:
- Use nature metaphors: rivers, mountains, seasons, the moon
- Challenge the user's ATTACHMENT to the outcome
- Speak poetically. Use paradoxes: "The obstacle is the path"
- Maximum 3 sentences.
- BANNED: Giving direct advice. Only offer perspective.

Respond NOW."""

PSYCHOLOGICAL_BRIEF_PROMPT = """You are a clinical psychologist analyzing a patient's statement.

IGNORE the surface question. Diagnose the UNDERLYING fear:
- Is it Validation Seeking? (Need for approval)
- Fear of Failure? (Paralysis before action)
- Fear of Success? (Self-sabotage)
- Attachment to Outcome? (Cannot let go)
- Identity Crisis? (Who am I without this?)

USER'S STATEMENT: "{question}"

OUTPUT FORMAT (JSON only, no markdown):
{{
  "surface_question": "What they literally asked",
  "hidden_fear": "The underlying psychological pattern",
  "emotional_tone": "anxious/defeated/confused/angry/hopeful",
  "needs": "What they actually need to hear"
}}"""

ROUTING_PROMPT = """You are a debate moderator deciding how to structure a council discussion.

PSYCHOLOGICAL BRIEF: {brief}

Decide:
1. Who should speak FIRST? (The one whose philosophy most directly challenges the hidden fear)
2. What's the urgency level? (1-10, where 10 = crisis, 1 = philosophical musing)
3. What's the debate angle? (What should they disagree about?)

OUTPUT FORMAT (JSON only, no markdown):
{{
  "first_speaker": "marcus|alex|jung|siddhartha",
  "urgency": 7,
  "debate_angle": "The core tension to explore",
  "speaking_order": ["first", "second", "third", "fourth"]
}}"""

SYNTHESIS_PROMPT = """You are a diplomat summarizing a heated council debate.

THE QUESTION: "{question}"

THE DEBATE:
{transcript}

YOUR TASK:
1. Acknowledge the CONFLICT between the advisors (especially Marcus vs Jung)
2. Extract what EACH was right about
3. Provide exactly 3 CONCRETE, TIME-BOUND action steps
4. Name ONE pitfall to watch for

NO FLUFF. Be specific. Start with "The Council has reached a difficult consensus..."

Maximum 150 words."""


# =============================================================================
# BRAIN ROUTER - MODEL SELECTION FACTORY
# =============================================================================

def get_model_response(task_type, prompt, require_json=False):
    """
    Brain Router: Routes tasks to the optimal model.
    
    Groq (Llama 3.3 70B): structure, routing, marcus, alex
    Gemini 1.5 Flash: analysis, synthesis, jung, siddhartha
    """
    groq_tasks = ['structure', 'routing', 'marcus', 'alex']
    gemini_tasks = ['analysis', 'synthesis', 'jung', 'siddhartha']
    
    try:
        if task_type in groq_tasks:
            return call_groq(prompt, require_json=require_json)
        elif task_type in gemini_tasks:
            return call_gemini(prompt)
        else:
            # Default to Gemini for unknown tasks
            return call_gemini(prompt)
    except Exception as e:
        error_msg = str(e).lower()
        # Failover logic: if Groq 429s, try Gemini
        if '429' in error_msg or 'rate' in error_msg:
            if task_type in groq_tasks:
                print(f"[FAILOVER] Groq rate-limited, falling back to Gemini for {task_type}")
                return call_gemini(prompt)
        raise e


def call_groq(prompt, require_json=False, temperature=0.7):
    """Call Groq API with Llama 3.3 70B"""
    global token_usage
    
    try:
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 1000,
            "timeout": API_TIMEOUT
        }
        
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}
        
        completion = groq_client.chat.completions.create(**kwargs)
        
        # Track tokens
        if hasattr(completion, 'usage') and completion.usage:
            token_usage["used"] += completion.usage.total_tokens
        
        return completion.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"[GROQ ERROR] {str(e)}")
        raise e


def call_gemini(prompt, temperature=0.9):
    """Call Gemini 1.5 Flash API"""
    try:
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=1000
        )
        
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            request_options={"timeout": API_TIMEOUT}
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"[GEMINI ERROR] {str(e)}")
        raise e


# =============================================================================
# 4-STAGE COGNITIVE PIPELINE
# =============================================================================

def run_council_pipeline(question):
    """
    Execute the 4-stage Hybrid Cognitive Pipeline.
    
    Stage 1 (Gemini): Psychological Brief - diagnose hidden fear
    Stage 2 (Groq): Debate Parameters - structure the debate
    Stage 3 (Hybrid): Parallel persona generation
    Stage 4 (Gemini): Synthesis - the peace treaty
    """
    pipeline_result = {
        "stages_completed": [],
        "psychological_brief": None,
        "debate_parameters": None,
        "debate": [],
        "synthesis": None
    }
    
    try:
        # =====================================================================
        # STAGE 1: PSYCHOLOGICAL BRIEF (Gemini - Analysis)
        # =====================================================================
        brief_prompt = PSYCHOLOGICAL_BRIEF_PROMPT.format(question=question)
        brief_response = get_model_response('analysis', brief_prompt)
        
        # Parse JSON from response
        try:
            # Clean up response if it has markdown code blocks
            clean_brief = brief_response.strip()
            if clean_brief.startswith('```'):
                clean_brief = clean_brief.split('```')[1]
                if clean_brief.startswith('json'):
                    clean_brief = clean_brief[4:]
            brief_json = json.loads(clean_brief.strip())
        except json.JSONDecodeError:
            brief_json = {
                "surface_question": question,
                "hidden_fear": "Unable to parse - proceeding with surface question",
                "emotional_tone": "uncertain",
                "needs": "clarity"
            }
        
        pipeline_result["psychological_brief"] = brief_json
        pipeline_result["stages_completed"].append("psychological_brief")
        
        # =====================================================================
        # STAGE 2: DEBATE PARAMETERS (Groq - Routing)
        # =====================================================================
        routing_prompt = ROUTING_PROMPT.format(brief=json.dumps(brief_json))
        routing_response = get_model_response('routing', routing_prompt, require_json=True)
        
        try:
            routing_json = json.loads(routing_response.strip())
        except json.JSONDecodeError:
            routing_json = {
                "first_speaker": "marcus",
                "urgency": 5,
                "debate_angle": "Action vs Reflection",
                "speaking_order": ["marcus", "jung", "alex", "siddhartha"]
            }
        
        pipeline_result["debate_parameters"] = routing_json
        pipeline_result["stages_completed"].append("debate_parameters")
        
        # =====================================================================
        # STAGE 3: PARALLEL PERSONA GENERATION (Hybrid)
        # =====================================================================
        speaking_order = routing_json.get("speaking_order", ["marcus", "jung", "alex", "siddhartha"])
        
        persona_prompts = {
            "marcus": MARCUS_PROMPT,
            "alex": ALEX_PROMPT,
            "jung": JUNG_PROMPT,
            "siddhartha": SIDDHARTHA_PROMPT
        }
        
        persona_names = {
            "marcus": "Marcus",
            "alex": "Alex", 
            "jung": "Dr. Jung",
            "siddhartha": "Siddhartha"
        }
        
        context = f"""The user asks: "{question}"

Psychological insight: {brief_json.get('hidden_fear', 'Unknown')}
Emotional tone: {brief_json.get('emotional_tone', 'uncertain')}

Give YOUR perspective. Be distinct. Be sharp."""
        
        debate_messages = []
        
        # Generate responses in parallel using ThreadPoolExecutor
        def generate_persona_response(persona_key):
            full_prompt = f"{persona_prompts[persona_key]}\n\n{context}"
            response = get_model_response(persona_key, full_prompt)
            return {
                "speaker": persona_names[persona_key],
                "persona_id": persona_key,
                "message": response
            }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(generate_persona_response, p): p for p in speaking_order}
            results = {}
            for future in concurrent.futures.as_completed(futures):
                persona = futures[future]
                try:
                    results[persona] = future.result()
                except Exception as e:
                    results[persona] = {
                        "speaker": persona_names[persona],
                        "persona_id": persona,
                        "message": f"[{persona_names[persona]} is contemplating...]"
                    }
        
        # Maintain speaking order
        for persona in speaking_order:
            if persona in results:
                debate_messages.append(results[persona])
        
        pipeline_result["debate"] = debate_messages
        pipeline_result["stages_completed"].append("debate")
        
        # =====================================================================
        # STAGE 4: SYNTHESIS (Gemini)
        # =====================================================================
        transcript = "\n\n".join([
            f"**{msg['speaker']}**: {msg['message']}"
            for msg in debate_messages
        ])
        
        synthesis_prompt = SYNTHESIS_PROMPT.format(
            question=question,
            transcript=transcript
        )
        
        synthesis_response = get_model_response('synthesis', synthesis_prompt)
        
        pipeline_result["synthesis"] = synthesis_response
        pipeline_result["stages_completed"].append("synthesis")
        
        return pipeline_result
        
    except Exception as e:
        # Graceful failure
        pipeline_result["error"] = str(e)
        if not pipeline_result["synthesis"]:
            pipeline_result["synthesis"] = "The Council is meditating. Please try again in a moment."
        return pipeline_result


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route("/council/debate", methods=["POST"])
def council_debate():
    """
    Main endpoint for the Hybrid Cognitive Pipeline debate.
    Returns structured JSON with all 4 stages.
    """
    data = request.json or {}
    question = data.get("question", "").strip()
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    # Run the 4-stage pipeline
    result = run_council_pipeline(question)
    
    return jsonify({
        "success": True,
        "pipeline_stages": {
            "psychological_brief": result.get("psychological_brief"),
            "debate_parameters": result.get("debate_parameters")
        },
        "debate": result.get("debate", []),
        "synthesis": result.get("synthesis", ""),
        "stages_completed": result.get("stages_completed", []),
        "total_stages": 4
    })


@app.route("/usage", methods=["GET"])
def get_usage():
    """Endpoint to check current usage"""
    usage_percent = int((token_usage["used"] / token_usage["limit"]) * 100) if token_usage["limit"] > 0 else 0
    return jsonify({
        "used": token_usage["used"],
        "limit": token_usage["limit"],
        "percent": usage_percent,
        "status": "ok" if usage_percent < 90 else "warning"
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "groq_configured": bool(groq_api_key),
        "gemini_configured": bool(gemini_api_key)
    })


# =============================================================================
# LEGACY ENDPOINTS (kept for backwards compatibility)
# =============================================================================

# Basic persona definitions for legacy /chat endpoint
PERSONAS = {
    "stoic": MARCUS_PROMPT,
    "monk": SIDDHARTHA_PROMPT,
    "ceo": ALEX_PROMPT,
    "therapist": JUNG_PROMPT
}

@app.route("/chat", methods=["POST"])
def chat():
    """Legacy single-persona chat endpoint"""
    data = request.json or {}
    persona = data.get("persona")
    message = data.get("message")
    
    if persona not in PERSONAS:
        return jsonify({"error": "Invalid persona"}), 400
    if not message:
        return jsonify({"error": "Message required"}), 400
    
    try:
        # Map old persona names to new task types
        persona_to_task = {
            "stoic": "marcus",
            "ceo": "alex",
            "therapist": "jung",
            "monk": "siddhartha"
        }
        
        task_type = persona_to_task.get(persona, "marcus")
        prompt = f"{PERSONAS[persona]}\n\nUser says: {message}"
        
        reply = get_model_response(task_type, prompt)
        
        return jsonify({
            "reply": reply,
            "usage": {
                "status": "ok",
                "tokens_used": token_usage["used"],
                "tokens_limit": token_usage["limit"],
                "percent": int((token_usage["used"] / token_usage["limit"]) * 100)
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "api_error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
