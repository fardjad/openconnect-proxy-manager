"""Heartbeat: pings a URL through the VPN proxy, tracks connection health."""
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request

import socks
import sockshandler

HEARTBEAT_FILE = os.path.join(tempfile.gettempdir(), "vpn_heartbeat")
FAILURE_THRESHOLD = 3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Heartbeat:
    def __init__(self, config):
        self.url = config.heartbeat_url
        self.interval = config.heartbeat_interval
        self.consecutive_failures = 0
        self._running = False
        self._on_dead = None

    def start(self):
        if not self.url or self._running:
            return
        self._running = True
        self.consecutive_failures = 0
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        self.consecutive_failures = 0

    def is_alive(self) -> bool:
        try:
            age = time.time() - os.path.getmtime(HEARTBEAT_FILE)
            return age < self.interval * 2
        except OSError:
            return False

    def on_dead(self, callback):
        self._on_dead = callback

    def _loop(self):
        handler = sockshandler.SocksiPyHandler(
            socks.SOCKS5, "127.0.0.1", 1081
        )
        opener = urllib.request.build_opener(handler, NoRedirect())
        while self._running:
            try:
                try:
                    response = opener.open(self.url, timeout=10)
                except urllib.error.HTTPError as response:
                    # Any HTTP response proves the target was reached through the VPN.
                    response.close()
                else:
                    response.close()
                with open(HEARTBEAT_FILE, "w") as f:
                    f.write(str(time.time()))
                self.consecutive_failures = 0
            except Exception:
                self.consecutive_failures += 1
                if self.consecutive_failures >= FAILURE_THRESHOLD and self._on_dead:
                    self._on_dead()
            time.sleep(self.interval)