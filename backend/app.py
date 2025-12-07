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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

