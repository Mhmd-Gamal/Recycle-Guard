from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
import time
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from typing import Literal

from .core import Core, ROOT
from .models import Action, AdviceRequest, Observation, StrictModel
from .policy import advise


@dataclass
class Session:
    core: Core
    advice: object = None
    excluded: list = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)


sessions = {}
registry_lock = RLock()


@asynccontextmanager
async def lifespan(app):
    yield
    with registry_lock:
        for s in sessions.values(): s.core.close()
        sessions.clear()


app = FastAPI(title="RecycleGuard research prototype", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def local_only(request: Request, call_next):
    # Bind on loopback. Reject cross-origin browser writes, even on loopback.
    origin = request.headers.get("origin")
    if request.method != "GET" and origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail": "Cross-origin writes are disabled"}, status_code=403)
    if int(request.headers.get("content-length", "0")) > 2_000_000:
        return JSONResponse({"detail": "Payload too large"}, status_code=413)
    return await call_next(request)


class NewSession(StrictModel):
    seed: int = Field(default=42, ge=-2147483648, le=2147483647)
    scenario: Literal["reliable", "delayed", "dropout"] = "reliable"


class Decide(StrictModel):
    decision: Literal["accept", "reject", "modify", "manual"]
    action: Action | None = None
    note: str = Field(default="", max_length=500)


class Mode(StrictModel):
    mode: Literal["scripted", "offline_raw", "offline_checked", "llm_raw", "llm_checked"] = "offline_checked"
    alternative: bool = False


def get(sid):
    with registry_lock:
        session = sessions.get(sid)
        if not session: raise HTTPException(404, "Session not found; create a new incident")
        session.last_used = time.monotonic()
        return session


def state(s):
    return {"observation": s.core.call("observe"), "advice": s.advice.model_dump() if s.advice else None}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "simulation": "shared C# core", "offline_is_llm": False}


@app.post("/v1/advice")
def advice(request: AdviceRequest):
    try: return advise(request)
    except ValueError as e: raise HTTPException(422, str(e)) from e
    except Exception as e: raise HTTPException(503, "Model provider unavailable or returned malformed output; use offline mode or check provider configuration.") from e


@app.post("/v1/sessions")
def create(request: NewSession):
    with registry_lock:
        for sid, s in list(sessions.items()):
            if time.monotonic() - s.last_used > 3600:
                s.core.close()
                del sessions[sid]
        if len(sessions) >= 16: raise HTTPException(429, "Close an existing session first")
        sid = str(uuid4())
        s = Session(Core())
        s.core.call("reset", seed=request.seed, scenario=request.scenario)
        sessions[sid] = s
        return {"id": sid, **state(s)}


@app.delete("/v1/sessions/{sid}")
def close(sid: str):
    with registry_lock:
        s = sessions.pop(sid, None)
        if s: s.core.close()
    return {"closed": True}


@app.get("/v1/sessions/{sid}")
def read(sid: str):
    s = get(sid)
    with s.core.lock: return state(s)


@app.post("/v1/sessions/{sid}/advice")
def session_advice(sid: str, request: Mode):
    s = get(sid)
    with s.core.lock:
        if request.alternative and s.advice:
            s.excluded.append(s.advice.recommendation)
            s.core.call("record", decision="alternative", note=json.dumps(s.advice.model_dump()))
        s.advice = advice(AdviceRequest(observation=Observation.model_validate(s.core.call("observe")), mode=request.mode, exclude=s.excluded))
        s.core.call("record", decision="advice", note=s.advice.model_dump_json())
        return state(s)


@app.post("/v1/sessions/{sid}/decision")
def decide(sid: str, request: Decide):
    s = get(sid)
    with s.core.lock:
        if request.decision in ("accept", "reject", "modify") and s.advice is None:
            raise HTTPException(409, "No recommendation available")
        if request.decision == "reject":
            s.core.call("record", decision="reject", note=request.note)
            s.excluded.append(s.advice.recommendation)
            s.advice = None
            return state(s)
        action = s.advice.recommendation if request.decision == "accept" else request.action
        if action is None: raise HTTPException(422, "Manual/modified decisions require an action")
        result = s.core.call("step", action=action.model_dump(), decision=request.decision, note=request.note)
        s.advice = None
        if result["advanced"]: s.excluded.clear()
        return {**state(s), "result": result}


@app.get("/v1/sessions/{sid}/replay")
def export(sid: str):
    return get(sid).core.call("log")


@app.post("/v1/replay/verify")
def replay(log: dict):
    if len(json.dumps(log)) > 2_000_000 or len(log.get("events", [])) > 2000: raise HTTPException(413, "Replay too large")
    try:
        with Core() as core: final = core.call("replay", log=log)
        return {"verified": True, "final": final}
    except (ValueError, TypeError) as e: raise HTTPException(422, str(e)) from e


app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.get("/")
def index(): return FileResponse(ROOT / "web" / "index.html")
