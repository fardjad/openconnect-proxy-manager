"""VPN manager: state machine wrapping openconnect process."""
import subprocess
import signal
import threading
import time
from enum import Enum


class VpnState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    WAITING_MFA = "waiting_mfa"
    CONNECTED = "connected"
    ERROR = "error"


class VpnManager:
    def __init__(self, config, heartbeat):
        self.config = config
        self.heartbeat = heartbeat
        self.state = VpnState.DISCONNECTED
        self.state_msg = ""
        self.output: list[str] = []
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        heartbeat.on_dead(self._on_heartbeat_dead)

    # ── Public API ───────────────────────────────────────────────────────

    def connect(self, user: str | None = None, password: str | None = None):
        u = user or self.config.user
        p = password or self.config.password
        if not u or not p:
            self.state = VpnState.ERROR
            self.state_msg = "Username and password required"
            return
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return
            self.state = VpnState.CONNECTING
            self.state_msg = "Starting VPN connection\u2026"
            self._proc = subprocess.Popen(
                ["openconnect", "-u", u, "--passwd-on-stdin",
                 "--script-tun", "--script=ocproxy -g -D 1081"]
                + self.config.options.split() + [self.config.url],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            assert self._proc.stdin is not None
            self._proc.stdin.write((p + "\n").encode())
            self._proc.stdin.flush()
            threading.Thread(target=self._read_output,
                             args=(self._proc.stdout,), daemon=True).start()

    def submit_mfa(self, code: str):
        code = code.strip()
        if not code:
            return
        with self._lock:
            if not self._proc or self._proc.poll() is not None:
                return
            assert self._proc.stdin is not None
            self._proc.stdin.write((code + "\n").encode())
            self._proc.stdin.flush()
            self.state = VpnState.CONNECTING
            self.state_msg = "MFA code sent. Waiting for connection\u2026"
            threading.Thread(target=self._check_connected, daemon=True).start()

    def disconnect(self):
        with self._lock:
            self._kill_proc()
            self.heartbeat.stop()
            self.state = VpnState.DISCONNECTED
            self.state_msg = ""

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "msg": self.state_msg,
            "output": self.output[-20:],
        }

    # ── Internals ────────────────────────────────────────────────────────

    def _kill_proc(self):
        if not self._proc:
            return
        try:
            self._proc.send_signal(signal.SIGINT)
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        except Exception:
            pass
        self._proc = None

    def _read_output(self, pipe):
        for line in iter(pipe.readline, b""):
            text = line.decode(errors="replace").strip()
            self.output.append(text)
            if len(self.output) > 50:
                self.output = self.output[-50:]
            if "Answer:" in text or "credential:" in text or "enter" in text.lower():
                self.state = VpnState.WAITING_MFA
                self.state_msg = "2FA code required"
            if "Connected" in text or "Established" in text or "DTLS" in text:
                self._on_connected()

    def _on_connected(self):
        self.state = VpnState.CONNECTED
        self.state_msg = "VPN connected"
        self.heartbeat.start()

    def _check_connected(self):
        time.sleep(5)
        if self._proc and self._proc.poll() is None:
            self._on_connected()
        elif self._proc:
            self.state = VpnState.ERROR
            self.state_msg = f"openconnect exited with code {self._proc.returncode}"
            self.heartbeat.stop()

    def _on_heartbeat_dead(self):
        self.disconnect()
        self.state = VpnState.ERROR
        self.state_msg = "VPN disconnected: heartbeat lost"