"""VPN proxy web UI — FastAPI app composing config, heartbeat, and VPN manager."""
import os
import shutil
import sys
import threading
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mako.template import Template
from pydantic import BaseModel

from config import Config
from heartbeat import Heartbeat
from vpn import VpnManager

# ── Prerequisites ───────────────────────────────────────────────────────────

def check_prerequisites():
    errors = []

    # OS dependencies
    for binary in ("openconnect", "ocproxy"):
        if not shutil.which(binary):
            errors.append(f"Missing binary: {binary}")

    if errors:
        sys.exit("Prerequisites failed:\n  " + "\n  ".join(errors))

check_prerequisites()

# ── Setup ───────────────────────────────────────────────────────────────────

config = Config.from_env()
heartbeat = Heartbeat(config)
vpn = VpnManager(config, heartbeat)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
template = Template(filename=os.path.join(TEMPLATE_DIR, "index.html"))

# ── Models ──────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    user: str | None = None
    password: str | None = None

class MfaRequest(BaseModel):
    code: str

# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return template.render(
        state=vpn.state.value,
        state_msg=vpn.state_msg,
        output=vpn.output,
        show_creds=not config.has_creds,
    )


@app.get("/api/status")
async def api_status():
    s = vpn.state.value
    color = {
        "connected": "green", "waiting_mfa": "orange", "connecting": "orange",
        "disconnected": "gray", "error": "red",
    }.get(s, "gray")
    return {
        **vpn.get_status(),
        "color": color,
        "heartbeat_alive": heartbeat.is_alive(),
        "heartbeat_failures": heartbeat.consecutive_failures,
    }


@app.post("/api/connect")
async def api_connect(body: ConnectRequest):
    vpn.connect(user=body.user, password=body.password)
    return {"state": vpn.state.value, "msg": vpn.state_msg}


@app.post("/api/mfa")
async def api_mfa(body: MfaRequest):
    if not body.code.strip():
        return JSONResponse({"error": "no code provided"}, 400)
    vpn.submit_mfa(body.code)
    return {"state": vpn.state.value, "msg": vpn.state_msg}


@app.post("/api/disconnect")
async def api_disconnect():
    vpn.disconnect()
    return {"state": vpn.state.value, "msg": vpn.state_msg}


# ── Startup ─────────────────────────────────────────────────────────────────

if config.auto_connect:
    def _auto_connect():
        time.sleep(2)
        vpn.connect()
    threading.Thread(target=_auto_connect, daemon=True).start()
