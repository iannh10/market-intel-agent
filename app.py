"""
Flask web server for the Multi-Agent Market Intelligence System.
Routes:
  GET  /              → serve index.html
  POST /run           → start pipeline, return {run_id}
  GET  /stream/<id>  → SSE stream of log lines + final report
"""

import json
import os
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

# Import pipeline agents
from market_intel import data_agent, trend_agent, strategy_agent, risk_agent, voice_agent

app = Flask(__name__)
CORS(app)

# run_id → Queue of SSE messages
_runs: dict[str, queue.Queue] = {}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sse(event: str, data: str) -> str:
    """Format a Server-Sent Event message."""
    payload = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {payload}\n\n"


def _run_pipeline(run_id: str, topic: str, include_voice: bool):
    """Execute the pipeline in a background thread, pushing SSE messages to the queue."""
    q = _runs[run_id]

    def emit(msg: str):
        q.put(_sse("log", msg))

    try:
        emit(f"🚀 Pipeline started for topic: '{topic}'")

        # Agent 1 — Data
        emit("🔍 [Data Agent] Searching for recent news...")
        articles = data_agent(topic, emit=emit)
        if not articles:
            q.put(_sse("error", "No news articles retrieved. Pipeline aborted."))
            return

        # Agent 2 — Trend
        emit("📈 [Trend Agent] Detecting market trends and sentiment shifts...")
        trends = trend_agent(articles, emit=emit)

        # Agent 3 — Strategy
        emit("💡 [Strategy Agent] Generating strategic opportunities...")
        strategy = strategy_agent(trends, emit=emit)

        # Agent 4 — Risk
        emit("⚠️  [Risk Agent] Identifying risks and weak signals...")
        risks = risk_agent(trends, strategy, emit=emit)

        # Optional Voice
        voice_script = None
        if include_voice:
            emit("🎙️  [Voice Agent] Writing broadcast script...")
            brief = (
                f"Market Intelligence on '{topic}': "
                + " | ".join(trends.get("trends", [])) + ". "
                + "Opportunities: " + "; ".join(strategy.get("opportunities", [])) + ". "
                + "Key Risks: " + "; ".join(risks.get("risks", []))
            )
            voice_script = voice_agent(brief, emit=emit)

        # Build structured report dict for the frontend
        report = {
            "topic": topic,
            "articles": articles,
            "trends": trends,
            "strategy": strategy,
            "risks": risks,
            "voice_script": voice_script,
        }

        emit("✅ Pipeline complete.")
        q.put(_sse("done", json.dumps(report)))

    except Exception as exc:
        q.put(_sse("error", f"Pipeline error: {exc}"))
    finally:
        # Sentinel: tell the SSE generator to close
        q.put(None)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def start_run():
    data = request.get_json(force=True)
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400

    include_voice = bool(data.get("include_voice", True))
    run_id = str(uuid.uuid4())
    _runs[run_id] = queue.Queue()

    t = threading.Thread(target=_run_pipeline, args=(run_id, topic, include_voice), daemon=True)
    t.start()

    return jsonify({"run_id": run_id})


@app.route("/stream/<run_id>")
def stream(run_id: str):
    if run_id not in _runs:
        return Response("Unknown run_id", status=404)

    q = _runs[run_id]

    def generate():
        while True:
            msg = q.get()
            if msg is None:
                # Clean up and close stream
                _runs.pop(run_id, None)
                break
            yield msg

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=True, threaded=True, host="0.0.0.0", port=port)
