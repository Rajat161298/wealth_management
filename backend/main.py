# main.py
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from utils import get_nse100_tickers, get_stock_data_summary, get_yfinance_news_summary
import uvicorn
from dotenv import load_dotenv
load_dotenv()

# Use Groq-based reasoner module (template in llm_groq.py)
try:
    from llm_groq import call_groq_reasoner
    GROQ_AVAILABLE = True
except Exception:
    call_groq_reasoner = None
    GROQ_AVAILABLE = False

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI(title="Wealth Signals Prototype - Groq")

# Simple in-memory cache to avoid repeated LLM calls during dev/testing
SIGNAL_CACHE = {}  # ticker -> (signal_dict, timestamp)
CACHE_TTL = int(os.getenv("SIGNAL_CACHE_TTL", 3600))  # seconds

class Signal(BaseModel):
    ticker: str
    action: str
    reason: str
    source: str
    confidence: Optional[float] = None

@app.get("/health")
async def health():
    return {"status": "ok", "groq_available": GROQ_AVAILABLE}

def parse_json_from_text(text: str):
    import json, re
    if not text:
        return None
    m = re.search(r"\{[\\s\\S]*\\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def call_groq_sync(prompt: str):
    # wrapper to call the Groq reasoner which may be sync or async depending on lib
    if not GROQ_AVAILABLE:
        raise RuntimeError("Groq not available")
    try:
        return call_groq_reasoner(prompt)
    except TypeError:
        # maybe it's async
        import asyncio
        return asyncio.get_event_loop().run_until_complete(call_groq_reasoner(prompt))

def ask_groq(prompt: str, retry: int = 1):
    \"\"\"Ask the Groq reasoner to return JSON matching schema. Retries once with stricter instruction.\"\"\"
    if not GROQ_AVAILABLE:
        return None
    try:
        raw = call_groq_sync(prompt)
        parsed = parse_json_from_text(raw)
        if parsed is not None:
            return parsed
        if retry > 0:
            strict_prompt = prompt + \"\\n\\nIMPORTANT: Respond ONLY with a single JSON object and no additional commentary. Follow this schema exactly: {\\\"action\\\": \\\"BUY|SELL|WATCH\\\", \\\"reason\\\": \\\"<1-2 sentences>\\\", \\\"source\\\": \\\"Technical|Fundamental|News|Mixed\\\", \\\"confidence\\\": <0-1 float> }\"
            raw2 = call_groq_sync(strict_prompt)
            parsed2 = parse_json_from_text(raw2)
            return parsed2
    except Exception as e:
        print(\"Groq call failed:\", e)
        return None

def call_llm_for_signal(ticker: str, stock_summary: dict, news_text: str) -> dict:
    # Check cache
    cached = SIGNAL_CACHE.get(ticker)
    if cached and (time.time() - cached[1]) < CACHE_TTL:
        return cached[0]

    prompt = f\"\"\"\nYou are an expert equities analyst and quantitative researcher (quant + fundamental + news). For the Indian stock {ticker} (NSE), analyze the provided structured metrics and recent news. Decide exactly ONE of the following actions: BUY, SELL, WATCH.\n\nOutput requirement (IMPORTANT): Respond ONLY with a single JSON object matching this schema:\n{{\n  \"action\": \"BUY|SELL|WATCH\",\n  \"reason\": \"A 1-2 sentence concise explanation (mention the dominant driver among Technical/Fundamental/News).\",\n  \"source\": \"Technical|Fundamental|News|Mixed\",\n  \"confidence\": 0.0\n}}\n\nUse the Metrics JSON and Recent News Text below. Keep the reason very concise and factual. If you are uncertain or the signals contradict strongly, choose WATCH and set confidence <= 0.5.\n\nMetrics JSON:\n{stock_summary}\n\nRecent News Text:\n{news_text}\n\nExample valid output:\n{\"action\":\"BUY\",\"reason\":\"RSI below 30 and price at lower 10% of 52-week range — technical oversold; fundamentals neutral.\",\"source\":\"Technical\",\"confidence\":0.72}\n\nNow provide the JSON only.\n\"\"\"

    groq_result = ask_groq(prompt)
    if groq_result:
        action = str(groq_result.get(\"action\", \"WATCH\")).upper()
        if action not in (\"BUY\", \"SELL\", \"WATCH\"):
            action = \"WATCH\"
        reason = groq_result.get(\"reason\", \"No concise reason provided.\")\n        source = groq_result.get(\"source\", \"Mixed\")
        try:
            confidence = float(groq_result.get(\"confidence\", 0.0))
            confidence = max(0.0, min(1.0, confidence))
        except Exception:
            confidence = 0.0
        signal = {\"action\": action, \"reason\": reason, \"source\": source, \"confidence\": confidence}
        SIGNAL_CACHE[ticker] = (signal, time.time())
        return signal

    # fallback heuristic
    act = \"WATCH\"
    reason = \"Heuristic fallback: insufficient LLM response.\"
    source = \"heuristic\"
    rsi = stock_summary.get('RSI', None)
    try:
        if rsi is not None:
            rsi = float(rsi)
            if rsi < 30:
                act = \"BUY\"
                reason = \"Heuristic: RSI indicates oversold.\"
            elif rsi > 70:
                act = \"SELL\"
                reason = \"Heuristic: RSI indicates overbought.\"
    except Exception:
        pass
    signal = {\"action\": act, \"reason\": reason, \"source\": source, \"confidence\": 0.3}
    SIGNAL_CACHE[ticker] = (signal, time.time())
    return signal

def make_signal_response(sig):
    return {\"ticker\": sig.get('ticker'), \"action\": sig.get('action'), \"reason\": sig.get('reason'), \"source\": sig.get('source'), \"confidence\": sig.get('confidence', 0.0)}

@app.get(\"/signals\", response_model=List[Signal])
async def get_signals(limit: int = 8):
    tickers = [
    'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BHARTIARTL.NS',
    'HCLTECH.NS', 'HDFCBANK.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'INDUSINDBK.NS',
    'INFY.NS', 'ITC.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LT.NS',
    'M&M.NS', 'MARUTI.NS', 'NESTLEIND.NS', 'NTPC.NS', 'POWERGRID.NS',
    'RELIANCE.NS', 'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATAMOTORS.NS',
    'TATASTEEL.NS', 'TECHM.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'WIPRO.NS']
    tickers = tickers[:limit]
    results = []
    for t in tickers:
        stock_summary, status = get_stock_data_summary(t)
        if not stock_summary:
            continue
        news_text = get_yfinance_news_summary(t)
        sig = call_llm_for_signal(t.replace(\".NS\", \"\"), stock_summary, news_text)
        results.append({\"ticker\": t.replace(\".NS\", \"\"), \"action\": sig.get('action', 'WATCH'), \"reason\": sig.get('reason', ''), \"source\": sig.get('source', ''), \"confidence\": sig.get('confidence', 0.0)})
    return results

if __name__ == \"__main__\":
    uvicorn.run(\"main:app\", host=\"0.0.0.0\", port=int(os.getenv(\"PORT\", 8000)), reload=True)