"""
Multi-Agent Market Intelligence System
Hackathon Prototype

Agents: Data Agent → Trend Agent → Strategy Agent → Risk Agent → Final Report

APIs Used:
  - Tavily  : Real-time news search
  - Reka    : Reasoning & summarization
  - Modulate: (placeholder) Voice script output

Insert your API keys in the CONFIG section below.
"""

import os
import json
import datetime
import requests
from typing import Optional, Callable
from reka.client import Reka
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG — insert your API keys here
# ─────────────────────────────────────────────
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY",   "tvly-YOUR_TAVILY_KEY")
REKA_API_KEY     = os.getenv("REKA_API_KEY",     "YOUR_REKA_KEY")
MODULATE_API_KEY = os.getenv("MODULATE_API_KEY", "YOUR_MODULATE_KEY")  # optional

TAVILY_ENDPOINT = "https://api.tavily.com/search"
REKA_MODEL      = "reka-core-20240501"   # use reka-flash for faster speeds
MAX_ARTICLES    = 5               # number of news articles to fetch

client = Reka(api_key=REKA_API_KEY)

Emitter = Optional[Callable[[str], None]]


# ─────────────────────────────────────────────
# HELPER — thin wrapper around Reka chat
# ─────────────────────────────────────────────
def _chat(system: str, user: str) -> str:
    """Send a single chat completion request to Reka and return the text."""
    response = client.chat.create(
        model=REKA_MODEL,
        messages=[
            {"role": "user",   "content": f"System Instruction: {system}\n\nUser Question: {user}"},
        ],
    )
    # The Reka SDK returns responses[0].message.content
    return response.responses[0].message.content.strip()


def _parse_json(raw: str) -> dict | list:
    """
    Robustly parse JSON from an LLM response that may be wrapped in
    markdown code fences (```json ... ``` or ``` ... ```).
    """
    text = raw.strip()
    # Strip opening fence: ```json or ```
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    # Strip closing fence
    if text.endswith("```"):
        text = text[:-3].strip()
    return json.loads(text)


# ─────────────────────────────────────────────
# AGENT 1 — Data Agent
#   Input : topic (str)
#   Output: list of dicts {headline, source, summary}
# ─────────────────────────────────────────────
def data_agent(topic: str, emit: Emitter = None) -> list[dict]:
    """
    Fetches recent news about the topic via Tavily,
    then uses Reka to produce a clean one-sentence summary per article.
    """
    def log(msg):
        print(msg)
        if emit:
            emit(msg)

    log(f"[Data Agent] 🔍 Searching news for: '{topic}' ...")

    # --- Step 1: Pull real-time news with Tavily Search API ---
    payload = {
        "api_key":        TAVILY_API_KEY,
        "query":          topic,
        "search_depth":   "advanced",
        "include_answer": False,
        "max_results":    MAX_ARTICLES,
        "topic":          "news",   # restrict to news results
    }
    resp = requests.post(TAVILY_ENDPOINT, json=payload, timeout=30)
    resp.raise_for_status()
    raw_results = resp.json().get("results", [])

    if not raw_results:
        log("[Data Agent] ⚠️  No results returned from Tavily.")
        return []

    # --- Step 2: Summarise each article with Reka ---
    articles = []
    for item in raw_results[:MAX_ARTICLES]:
        headline = item.get("title", "No title")
        source   = item.get("url",   "Unknown source")
        content  = item.get("content", item.get("snippet", ""))

        summary = _chat(
            system="You are a concise financial news analyst. Summarise the article in one sentence.",
            user=f"Article title: {headline}\n\nContent: {content[:1500]}",
        )

        articles.append({
            "headline": headline,
            "source":   source,
            "summary":  summary,
        })
        log(f"  ✔ {headline[:80]}")

    return articles


# ─────────────────────────────────────────────
# AGENT 2 — Trend Agent
#   Input : list of article dicts from Data Agent
#   Output: dict {trends: [...], sentiment_shifts: [...]}
# ─────────────────────────────────────────────
def trend_agent(articles: list[dict], emit: Emitter = None) -> dict:
    """
    Uses Reka to identify the 3 major trends and any sentiment shifts
    across the collected news summaries.
    """
    def log(msg):
        print(msg)
        if emit:
            emit(msg)

    log("[Trend Agent] 📈 Detecting trends and sentiment shifts ...")

    # Build a compact brief from the article summaries
    brief = "\n".join(
        f"- [{a['source']}] {a['headline']}: {a['summary']}"
        for a in articles
    )

    raw = _chat(
        system=(
            "You are a market research analyst specialising in trend detection. "
            "Return ONLY valid JSON with two keys: "
            "\"trends\" (list of 3 strings) and "
            "\"sentiment_shifts\" (list of strings describing sentiment changes). "
            "No markdown, no code fences."
        ),
        user=f"News summaries:\n{brief}\n\nIdentify 3 major market trends and any notable sentiment shifts.",
    )

    # --- Parse JSON robustly ---
    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        # Fallback: wrap raw text so pipeline keeps running
        result = {
            "trends": [raw],
            "sentiment_shifts": ["Unable to parse structured output."],
        }

    for i, t in enumerate(result.get("trends", []), 1):
        log(f"  Trend {i}: {t}")

    return result


# ─────────────────────────────────────────────
# AGENT 3 — Strategy Agent
#   Input : trend dict from Trend Agent
#   Output: dict {opportunities: [...], recommendations: [...]}
# ─────────────────────────────────────────────
def strategy_agent(trend_data: dict, emit: Emitter = None) -> dict:
    """
    Converts detected trends into business opportunities and
    actionable strategic recommendations using Reka.
    """
    def log(msg):
        print(msg)
        if emit:
            emit(msg)

    log("[Strategy Agent] 💡 Generating strategic opportunities ...")

    trend_text = "\n".join(f"- {t}" for t in trend_data.get("trends", []))
    sentiment_text = "\n".join(f"- {s}" for s in trend_data.get("sentiment_shifts", []))

    raw = _chat(
        system=(
            "You are a senior business strategist. "
            "Return ONLY valid JSON with two keys: "
            "\"opportunities\" (list of 3 business opportunity strings) and "
            "\"recommendations\" (list of 3 strategic recommendation strings). "
            "No markdown, no code fences."
        ),
        user=(
            f"Market Trends:\n{trend_text}\n\n"
            f"Sentiment Shifts:\n{sentiment_text}\n\n"
            "Generate concrete business opportunities and strategic recommendations."
        ),
    )

    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        result = {
            "opportunities":    [raw],
            "recommendations":  ["Unable to parse structured output."],
        }

    for i, o in enumerate(result.get("opportunities", []), 1):
        log(f"  Opportunity {i}: {o}")

    return result


# ─────────────────────────────────────────────
# AGENT 4 — Risk Agent
#   Input : trend dict + strategy dict
#   Output: dict {risks: [...], weak_signals: [...], uncertainties: [...]}
# ─────────────────────────────────────────────
def risk_agent(trend_data: dict, strategy_data: dict, emit: Emitter = None) -> dict:
    """
    Identifies market risks, weak signals, and areas of uncertainty
    by cross-referencing trends with proposed strategies.
    """
    def log(msg):
        print(msg)
        if emit:
            emit(msg)

    log("[Risk Agent] ⚠️  Identifying risks and weak signals ...")

    trend_text    = "\n".join(f"- {t}" for t in trend_data.get("trends", []))
    strategy_text = "\n".join(f"- {r}" for r in strategy_data.get("recommendations", []))

    raw = _chat(
        system=(
            "You are a risk analyst specialising in emerging market threats. "
            "Return ONLY valid JSON with three keys: "
            "\"risks\" (list of 3 market risk strings), "
            "\"weak_signals\" (list of 2 early warning signals), and "
            "\"uncertainties\" (list of 2 major uncertainty factors). "
            "No markdown, no code fences."
        ),
        user=(
            f"Market Trends:\n{trend_text}\n\n"
            f"Proposed Strategies:\n{strategy_text}\n\n"
            "Identify the key risks, weak signals, and uncertainties."
        ),
    )

    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        result = {
            "risks":         [raw],
            "weak_signals":  ["Unable to parse structured output."],
            "uncertainties": ["Unable to parse structured output."],
        }

    for i, r in enumerate(result.get("risks", []), 1):
        log(f"  Risk {i}: {r}")

    return result


# ─────────────────────────────────────────────
# OPTIONAL — Voice Script (Modulate placeholder)
# ─────────────────────────────────────────────
def voice_agent(report_text: str, emit: Emitter = None) -> str:
    """
    Converts the final report into a short broadcast-style voice script.
    Uses Reka to write the script; Modulate would handle TTS playback.
    """
    def log(msg):
        print(msg)
        if emit:
            emit(msg)

    log("[Voice Agent] 🎙️  Writing voice script ...")

    script = _chat(
        system=(
            "You are a professional radio broadcaster. "
            "Convert the market intelligence report into a concise 60-second verbal briefing. "
            "Use natural, spoken language."
        ),
        user=report_text,
    )

    # ── Modulate TTS placeholder ──────────────────────────
    # import modulate  (pip install modulate-sdk)
    # audio = modulate.tts.synthesize(
    #     api_key=MODULATE_API_KEY,
    #     voice_id="announcer_v1",
    #     text=script,
    # )
    # with open("report_audio.mp3", "wb") as f:
    #     f.write(audio)
    # print("  ✔ Audio saved to report_audio.mp3")
    # ─────────────────────────────────────────────────────

    return script


# ─────────────────────────────────────────────
# REPORT RENDERER (CLI only)
# ─────────────────────────────────────────────
def render_report(
    topic: str,
    articles:  list[dict],
    trends:    dict,
    strategy:  dict,
    risks:     dict,
    voice_script: Optional[str] = None,
) -> str:
    """Assembles all agent outputs into a formatted terminal report."""

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sep = "─" * 60

    lines = [
        "",
        "╔" + "═" * 58 + "╗",
        f"║{'MARKET INTELLIGENCE REPORT':^58}║",
        f"║{'Topic: ' + topic:^58}║",
        f"║{now:^58}║",
        "╚" + "═" * 58 + "╝",
        "",
        f"{'📰 LATEST NEWS':}",
        sep,
    ]

    for a in articles:
        lines += [
            f"  • {a['headline']}",
            f"    Source : {a['source']}",
            f"    Summary: {a['summary']}",
            "",
        ]

    lines += [f"{'📈 MARKET TRENDS':}", sep]
    for t in trends.get("trends", []):
        lines.append(f"  • {t}")
    lines.append("")
    lines.append("  Sentiment Shifts:")
    for s in trends.get("sentiment_shifts", []):
        lines.append(f"  ↳ {s}")
    lines.append("")

    lines += [f"{'💡 STRATEGIC OPPORTUNITIES':}", sep]
    for o in strategy.get("opportunities", []):
        lines.append(f"  ✦ {o}")
    lines.append("")
    lines.append("  Recommendations:")
    for r in strategy.get("recommendations", []):
        lines.append(f"  → {r}")
    lines.append("")

    lines += [f"{'⚠️  RISKS & SIGNALS':}", sep]
    lines.append("  Market Risks:")
    for r in risks.get("risks", []):
        lines.append(f"  ✗ {r}")
    lines.append("")
    lines.append("  Weak Signals:")
    for w in risks.get("weak_signals", []):
        lines.append(f"  ~ {w}")
    lines.append("")
    lines.append("  Uncertainties:")
    for u in risks.get("uncertainties", []):
        lines.append(f"  ? {u}")
    lines.append("")

    if voice_script:
        lines += [f"{'🎙️  VOICE BRIEFING':}", sep, voice_script, ""]

    lines += ["═" * 60, "  End of Report", "═" * 60, ""]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# PIPELINE ENTRY POINT (CLI)
# ─────────────────────────────────────────────
def run_pipeline(topic: str, include_voice: bool = True) -> str:
    """
    Orchestrates the full multi-agent pipeline:
      topic → Data Agent → Trend Agent → Strategy Agent → Risk Agent → Report
    """
    print(f"\n{'═'*60}")
    print(f"  🚀 Market Intelligence Pipeline Starting")
    print(f"  Topic: {topic}")
    print(f"{'═'*60}")

    # Agent 1 — fetch & structure news
    articles = data_agent(topic)
    if not articles:
        return "Pipeline aborted: no news articles retrieved."

    # Agent 2 — detect trends
    trends = trend_agent(articles)

    # Agent 3 — generate strategy
    strategy = strategy_agent(trends)

    # Agent 4 — assess risks
    risks = risk_agent(trends, strategy)

    # (Optional) Voice Agent
    voice_script = None
    if include_voice:
        # Build a brief text summary to feed into the voice agent
        brief = (
            f"Market Intelligence on '{topic}': "
            + " | ".join(trends.get("trends", [])) + ". "
            + "Opportunities: " + "; ".join(strategy.get("opportunities", [])) + ". "
            + "Key Risks: " + "; ".join(risks.get("risks", []))
        )
        voice_script = voice_agent(brief)

    # Render final report
    report = render_report(topic, articles, trends, strategy, risks, voice_script)
    print(report)
    return report


# ─────────────────────────────────────────────
# SAMPLE RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    topic = "AI hardware market"          # ← change topic here
    run_pipeline(topic, include_voice=True)
