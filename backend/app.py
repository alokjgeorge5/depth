import os
import json
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timedelta
from personas import PersonaManager
import gc


load_dotenv()


app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["https://depth-chi.vercel.app", "https://depth-qiu9wulnc-jins-projects-ee877f80.vercel.app", "*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})


# Initialize API client
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key)


# Token tracking (simple in-memory)
token_usage = {
    "used": 0,
    "limit": 100000,
    "reset_time": None
}


# API timeout constraint
API_TIMEOUT = 120


# Initialize PersonaManager for knowledge-rich prompts
try:
    persona_manager = PersonaManager()
    print("[INIT] PersonaManager loaded successfully")
except Exception as e:
    print(f"[ERROR] Failed to load PersonaManager: {e}")
    persona_manager = None


# =============================================================================
# PIPELINE PROMPTS (Psychological Brief, Routing, Synthesis)
# =============================================================================
# Note: Persona prompts are now loaded dynamically from PersonaManager


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
    Brain Router: Routes ALL tasks to Groq (Llama 3.3 70B).
    Temperature varies by task type for optimal performance.
    """
    # Determine temperature based on task type
    # Lower temp (0.6) for structured/analytical tasks
    # Higher temp (0.9) for creative/empathetic personas
    creative_tasks = ['analysis', 'synthesis', 'jung', 'siddhartha']
    temperature = 0.9 if task_type in creative_tasks else 0.6
    
    return call_groq(prompt, require_json=require_json, temperature=temperature)



def call_groq(prompt, require_json=False, temperature=0.7):
    """Call Groq API with Llama 3.3 70B"""
    global token_usage
    
    try:
        print(f"[GROQ] Calling API with temperature={temperature}, require_json={require_json}")
        
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 1000,
            "timeout": 10.0  # Fix #3: 10 second timeout to prevent long waits
        }
        
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}
        
        completion = groq_client.chat.completions.create(**kwargs)
        
        # Track tokens
        if hasattr(completion, 'usage') and completion.usage:
            token_usage["used"] += completion.usage.total_tokens
            print(f"[GROQ] Tokens used: {completion.usage.total_tokens}, Total: {token_usage['used']}")
        
        response = completion.choices[0].message.content.strip()
        print(f"[GROQ] Response received ({len(response)} chars)")
        
        return response
        
    except Exception as e:
        print(f"[GROQ ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
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
    print("\n" + "="*60)
    print(f"[PIPELINE START] Question: {question}")
    print("="*60)
    
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
        print("\n[STAGE 1] Starting Psychological Brief...")
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
            print(f"[STAGE 1] ✓ Brief parsed: {brief_json.get('hidden_fear', 'N/A')}")
        except json.JSONDecodeError as e:
            print(f"[STAGE 1] ⚠ JSON parse failed: {e}")
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
        print("\n[STAGE 2] Starting Debate Parameters...")
        routing_prompt = ROUTING_PROMPT.format(brief=json.dumps(brief_json))
        routing_response = get_model_response('routing', routing_prompt, require_json=True)
        
        try:
            routing_json = json.loads(routing_response.strip())
            print(f"[STAGE 2] ✓ Routing parsed: {routing_json.get('speaking_order', [])}")
        except json.JSONDecodeError as e:
            print(f"[STAGE 2] ⚠ JSON parse failed: {e}")
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
        print("\n[STAGE 3] Starting Parallel Persona Generation...")
        speaking_order = routing_json.get("speaking_order", ["marcus", "jung", "alex", "siddhartha"])
        
        # Map persona keys to PersonaManager names
        # Note: We're mapping the 4 council members to the 4 available knowledge bases
        persona_mapping = {
            "marcus": "MARCUS",      # Risk Officer (Taleb) - fits Marcus perfectly
            "alex": "ALEX",          # Strategist (Thiel/Helmer) - fits Alex perfectly
            "jung": "MAYA",          # Customer Researcher (Mom Test) - Jung asks questions about users
            "siddhartha": "TURING"   # Engineer (Brooks) - Siddhartha simplifies/removes complexity
        }
        
        persona_names = {
            "marcus": "Marcus",
            "alex": "Alex", 
            "jung": "Maya",
            "siddhartha": "Turing"
        }
        
        context = f"""The user asks: "{question}"


Psychological insight: {brief_json.get('hidden_fear', 'Unknown')}
Emotional tone: {brief_json.get('emotional_tone', 'uncertain')}


Give YOUR perspective. Be distinct. Be sharp."""
        
        debate_messages = []
        
        # Generate responses in parallel using ThreadPoolExecutor
        def generate_persona_response(persona_key):
            print(f"[STAGE 3] Generating response for {persona_names[persona_key]}...")
            # Get knowledge-rich system prompt from PersonaManager
            try:
                if persona_manager:
                    manager_key = persona_mapping.get(persona_key, "MARCUS")
                    system_prompt = persona_manager.get_system_prompt(manager_key)
                    print(f"[STAGE 3] Loaded prompt for {persona_names[persona_key]} ({manager_key})")
                else:
                    # Fallback if PersonaManager failed to load
                    print(f"[STAGE 3] ⚠ PersonaManager unavailable, using fallback for {persona_names[persona_key]}")
                    system_prompt = f"You are {persona_names[persona_key]}. Critically evaluate the user's idea."
            except Exception as e:
                print(f"[STAGE 3] ERROR loading prompt for {persona_key}: {e}")
                system_prompt = f"You are {persona_names[persona_key]}. Critically evaluate the user's idea."
            
            # Combine system prompt with context
            full_prompt = f"{system_prompt}\n\n{context}"
            response = get_model_response(persona_key, full_prompt)
            
            # Fix #2: Truncate long responses
            MAX_RESPONSE_LENGTH = 2000
            if len(response) > MAX_RESPONSE_LENGTH:
                response = response[:MAX_RESPONSE_LENGTH] + "..."
                print(f"[STAGE 3] ✓ {persona_names[persona_key]} responded (truncated to {MAX_RESPONSE_LENGTH} chars)")
            else:
                print(f"[STAGE 3] ✓ {persona_names[persona_key]} responded ({len(response)} chars)")
            
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
                    print(f"[STAGE 3] ERROR for {persona}: {e}")
                    import traceback
                    traceback.print_exc()
                    results[persona] = {
                        "speaker": persona_names[persona],
                        "persona_id": persona,
                        "message": f"[{persona_names[persona]} is contemplating...]"
                    }
        
        # Maintain speaking order
        for persona in speaking_order:
            if persona in results:
                debate_messages.append(results[persona])
        
        print(f"[STAGE 3] ✓ Generated {len(debate_messages)} responses")
        
        pipeline_result["debate"] = debate_messages
        pipeline_result["stages_completed"].append("debate")
        
        # =====================================================================
        # STAGE 4: SYNTHESIS (Gemini)
        # =====================================================================
        print("\n[STAGE 4] Starting Synthesis...")
        transcript = "\n\n".join([
            f"**{msg['speaker']}**: {msg['message']}"
            for msg in debate_messages
        ])
        
        synthesis_prompt = SYNTHESIS_PROMPT.format(
            question=question,
            transcript=transcript
        )
        
        synthesis_response = get_model_response('synthesis', synthesis_prompt)
        print(f"[STAGE 4] ✓ Synthesis complete ({len(synthesis_response)} chars)")
        
        pipeline_result["synthesis"] = synthesis_response
        pipeline_result["stages_completed"].append("synthesis")
        
        print("\n" + "="*60)
        print(f"[PIPELINE COMPLETE] All {len(pipeline_result['stages_completed'])} stages finished")
        print("="*60 + "\n")
        
        return pipeline_result
        
    except Exception as e:
        # Graceful failure with full error logging
        print("\n" + "="*60)
        print(f"[PIPELINE ERROR] {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        
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



# Store conversation history (simple in-memory)
conversations = {}


@app.route("/api/getResponses", methods=["POST"])
def get_responses():
    """
    Frontend-friendly endpoint that matches the API contract:
    
    Request: { question, conversation_id }
    Response: { conversation_id, responses: [{ persona, title, content, confidence }] }
    """
    import uuid
    
    print("\n" + "="*60)
    print("[REQUEST] /api/getResponses called")
    print("="*60)
    
    data = request.json or {}
    print(f"[DATA] Received: {data}")
    
    question = data.get("question", "").strip()
    conversation_id = data.get("conversation_id")
    
    print(f"[QUESTION] '{question[:100]}...' ({len(question)} chars)")
    print(f"[CONVERSATION_ID] {conversation_id}")
    
    # Fix #1: Input length limit
    MAX_QUESTION_LENGTH = 1000
    if len(question) > MAX_QUESTION_LENGTH:
        print(f"[ERROR] Question too long: {len(question)} chars")
        return jsonify({
            "error": f"Question too long (max {MAX_QUESTION_LENGTH} characters)"
        }), 400
    
    if not question:
        print("[ERROR] No question provided")
        return jsonify({"error": "Question required"}), 400
    
    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        print(f"[CONVERSATION_ID] Generated new: {conversation_id}")
    
    # Run the pipeline
    print("\n[CALLING] run_council_pipeline...")
    result = run_council_pipeline(question)
    
    # Check for pipeline errors
    if result.get("error"):
        print(f"[ERROR] Pipeline failed: {result['error']}")
        return jsonify({
            "conversation_id": conversation_id,
            "responses": [],
            "error": result["error"]
        })
    
    # Transform debate responses to frontend format
    persona_map = {
        "marcus": "MARCUS",
        "alex": "ALEX",
        "jung": "MAYA",
        "siddhartha": "TURING"
    }
    
    title_map = {
        "MARCUS": "Risk Assessment",
        "ALEX": "Strategic Vision",
        "MAYA": "Customer Insight",
        "TURING": "Technical Analysis"
    }
    
    responses = []
    debate = result.get("debate", [])
    
    # Log if debate is empty
    if not debate:
        print(f"[WARNING] Empty debate array!")
        print(f"[DEBUG] Pipeline stages completed: {result.get('stages_completed', [])}")
        print(f"[DEBUG] Full result: {json.dumps(result, indent=2)}")
    else:
        print(f"[SUCCESS] Debate has {len(debate)} responses")
    
    for msg in debate:
        persona_id = msg.get("persona_id", "marcus")
        persona_name = persona_map.get(persona_id, "MARCUS")
        
        # Calculate confidence based on urgency
        urgency = result.get("debate_parameters", {}).get("urgency", 5)
        base_confidence = 70 + (10 - urgency) * 2
        confidence = min(95, max(60, base_confidence + len(msg.get("message", "")) % 15))
        
        responses.append({
            "persona": persona_name,
            "title": title_map.get(persona_name, "Analysis"),
            "content": msg.get("message", ""),
            "confidence": confidence
        })
    
    print(f"[RESPONSES] Formatted {len(responses)} responses for frontend")
    
    # Store in conversation history
    conversations[conversation_id] = {
        "question": question,
        "responses": responses
    }
    
    response_data = {
        "conversation_id": conversation_id,
        "responses": responses
    }
    
    print(f"[RESPONSE] Returning {len(responses)} responses")
    print("="*60 + "\n")
    
    return jsonify(response_data)



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
    """Quick sanity check - is everything actually working?"""
    try:
        # Test Groq API
        test_call = call_groq(
            "Say 'OK'", 
            temperature=0.1
        )
        groq_status = "✓" if test_call else "✗"
    except Exception as e:
        print(f"[HEALTH CHECK ERROR] {e}")
        groq_status = "✗"
    
    return jsonify({
        "status": "ok",
        "groq_api": groq_status,
        "personas_loaded": len(persona_manager.personas) if persona_manager else 0,
        "port": 5000,
        "model": "llama-3.3-70b-versatile"
    })



# =============================================================================
# LEGACY ENDPOINTS (kept for backwards compatibility)
# =============================================================================


@app.route("/chat", methods=["POST"])
def chat():
    """Legacy single-persona chat endpoint - now uses PersonaManager"""
    data = request.json or {}
    persona = data.get("persona")
    message = data.get("message")
    
    # Map legacy persona names to PersonaManager keys
    legacy_mapping = {
        "stoic": "MARCUS",
        "monk": "TURING",
        "ceo": "ALEX",
        "therapist": "MAYA"
    }
    
    if persona not in legacy_mapping:
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



# =============================================================================
# FRONTEND SERVING (fixes file:// protocol issue)
# =============================================================================


@app.route('/')
def serve_frontend():
    """Serve the frontend HTML file"""
    # Get the directory where app.py lives (backend/)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to mentor/, then into frontend/cf/
    frontend_path = os.path.join(backend_dir, '..', 'frontend', 'cf')
    frontend_path = os.path.abspath(frontend_path)  # Normalize the path
    print(f"[DEBUG] Serving from: {frontend_path}")  # Debug
    return send_from_directory(frontend_path, 'depth-ai-council-final.html')



def validate_startup():
    """Run before starting server"""
    errors = []
    
    # Check 1: API key exists
    if not os.getenv("GROQ_API_KEY"):
        errors.append("❌ GROQ_API_KEY missing in .env")
    
    # Check 2: API key works
    try:
        print("[STARTUP] Testing Groq API connection...")
        test = call_groq("Say OK", temperature=0.1)
        if not test:
            errors.append("❌ Groq API call returned empty")
    except Exception as e:
        errors.append(f"❌ Groq connection failed: {e}")
    
    # Check 3: Personas loaded
    if not persona_manager or len(persona_manager.personas) != 4:
        count = len(persona_manager.personas) if persona_manager else 0
        print(f"[DEBUG] Personas count: {count}")
        errors.append(f"[X] Expected 4 personas, got {count}")
    
    # Check 4: Port available
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        # Try binding to port 5000 (test if we CAN start)
        sock.bind(('0.0.0.0', 5000))
        sock.close()
    except Exception as e:
        errors.append(f"[X] Port 5000 unavailable: {e}")
    
    if errors:
        print("\n" + "="*60)
        print("[!] STARTUP VALIDATION FAILED")
        print("="*60)
        for err in errors:
            print(err)
        print("="*60 + "\n")
        exit(1)
    else:
        print("\n" + "="*60)
        print("[OK] STARTUP VALIDATION PASSED")
        print(f"[OK] Groq API: Connected")
        print(f"[OK] Personas: {len(persona_manager.personas)} loaded")
        print(f"[OK] Port 5000: Available")
        print("="*60 + "\n")


import atexit
import signal

def cleanup():
    """Called when server stops"""
    print("\n" + "="*60)
    print("[SHUTDOWN] Cleaning up...")
    print("="*60)
    # Force close ThreadPoolExecutor if it exists
    import concurrent.futures
    # Shutdown any active executors
    for obj in gc.get_objects():
        if isinstance(obj, concurrent.futures.ThreadPoolExecutor):
            obj.shutdown(wait=False)

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: (cleanup(), exit(0)))
signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), exit(0)))


if __name__ == "__main__":
    validate_startup()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*60}")
    print(f"[STARTUP] Depth AI Council Backend")
    print(f"[STARTUP] Port: {port}")
    print(f"[STARTUP] Groq API Key: {'✓ Configured' if groq_api_key else '✗ Missing'}")
    print(f"[STARTUP] PersonaManager: {'✓ Loaded' if persona_manager else '✗ Failed'}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
