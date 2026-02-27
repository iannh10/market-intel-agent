# Multi-Agent Market Intelligence System

A hackathon prototype that simulates a team of AI analysts collaborating to generate market intelligence from real-time news.

## Architecture

```
topic → [Data Agent] → [Trend Agent] → [Strategy Agent] → [Risk Agent] → Final Report
                                                                   ↓
                                                           [Voice Agent] (optional)
```

| Agent | Role | APIs Used |
|---|---|---|
| **Data Agent** | Fetch & summarise real-time news | Tavily + Reka |
| **Trend Agent** | Detect 3 major trends + sentiment shifts | Reka |
| **Strategy Agent** | Generate business opportunities & recommendations | Reka |
| **Risk Agent** | Identify risks, weak signals, uncertainties | Reka |
| **Voice Agent** | Convert report to 60-sec broadcast script | Reka (+ Modulate placeholder) |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add API Keys

Set environment variables (recommended):

```bash
export TAVILY_API_KEY="tvly-your-key-here"
export REKA_API_KEY="your-reka-key-here"
export MODULATE_API_KEY="your-modulate-key"   # optional — voice output
```

Or edit the `CONFIG` block at the top of `market_intel.py` directly.

#### Where to get keys
| API | Sponsor | Link |
|---|---|---|
| Tavily | Tavily | https://app.tavily.com |
| Reka | Reka | https://platform.reka.ai |
| Modulate | Modulate | https://modulate.ai (TTS voice — optional) |

### 3. Run

```bash
python market_intel.py
```

Change the topic on the last line of `market_intel.py`:

```python
topic = "AI hardware market"   # ← edit here
```

## Sample Output

```
╔══════════════════════════════════════════════════════════╗
║                MARKET INTELLIGENCE REPORT                ║
║                  Topic: AI hardware market               ║
║                      2025-06-15 14:23                    ║
╚══════════════════════════════════════════════════════════╝

📰 LATEST NEWS
──────────────────────────────────────────────────────────
  • NVIDIA announces next-gen Blackwell GB300 chips
    Source : ...
    Summary: ...
...
```

## Customisation

| Parameter | Location | Default |
|---|---|---|
| Number of articles | `MAX_ARTICLES` | `5` |
| AI model | `REKA_MODEL` | `reka-core-20240501` |
| Topic | `__main__` block | `"AI hardware market"` |
| Voice output | `include_voice=True` | `True` |

## Notes

- No agent frameworks used (no LangChain, no AutoGen).
- All inter-agent communication is plain Python dicts/lists.
- Modulate TTS is stubbed — see `voice_agent()` for integration instructions.
