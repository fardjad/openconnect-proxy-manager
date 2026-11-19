import os
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest
from unittest.mock import Mock, patch

import heartbeat
from heartbeat import Heartbeat


class HeartbeatTests(unittest.TestCase):
    def make_heartbeat(self, url="https://heartbeat.example", interval=10):
        return Heartbeat(Mock(heartbeat_url=url, heartbeat_interval=interval))

    def test_start_without_url_does_not_create_thread(self):
        heart = self.make_heartbeat(url="")
        with patch.object(heartbeat.threading, "Thread") as thread:
            heart.start()

        thread.assert_not_called()
        self.assertFalse(heart._running)

    def test_start_is_idempotent(self):
        heart = self.make_heartbeat()
        with patch.object(heartbeat.threading, "Thread") as thread:
            heart.start()
            heart.start()

        thread.assert_called_once_with(target=heart._loop, daemon=True)
        thread.return_value.start.assert_called_once_with()

    def test_liveness_requires_file_younger_than_twice_interval(self):
        heart = self.make_heartbeat(interval=10)
        with tempfile.NamedTemporaryFile() as file:
            with patch.object(heartbeat, "HEARTBEAT_FILE", file.name):
                with patch.object(heartbeat.time, "time", return_value=120):
                    with patch.object(heartbeat.os.path, "getmtime", return_value=101):
                        self.assertTrue(heart.is_alive())
                    with patch.object(heartbeat.os.path, "getmtime", return_value=100):
                        self.assertFalse(heart.is_alive())

    def test_http_redirect_is_reachable_without_following_it(self):
        requests = []

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(302)
                self.send_header("Location", self.path)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        heart = self.make_heartbeat(url=f"http://127.0.0.1:{server.server_port}/")
        heart._running = True
        heart.consecutive_failures = 2
        callback = Mock()
        heart.on_dead(callback)

        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"no_proxy": "*", "NO_PROXY": "*"}), \
             patch.object(heartbeat, "HEARTBEAT_FILE", os.path.join(directory, "heartbeat")), \
             patch.object(heartbeat.sockshandler, "SocksiPyHandler", return_value=urllib.request.BaseHandler()), \
             patch.object(heartbeat.time, "sleep", side_effect=lambda _: setattr(heart, "_running", False)):
            heart._loop()
            self.assertTrue(heart.is_alive())

        self.assertEqual(requests, ["/"])
        self.assertEqual(heart.consecutive_failures, 0)
        callback.assert_not_called()

    def test_failure_threshold_calls_dead_callback(self):
        heart = self.make_heartbeat()
        callback = Mock()
        heart.on_dead(callback)
        heart._running = True

        def stop_after_threshold(_interval):
            if heart.consecutive_failures == heartbeat.FAILURE_THRESHOLD:
                heart._running = False

        opener = Mock()
        opener.open.side_effect = OSError("offline")
        with patch.object(heartbeat.sockshandler, "SocksiPyHandler"), \
             patch.object(heartbeat.urllib.request, "build_opener", return_value=opener), \
             patch.object(heartbeat.time, "sleep", side_effect=stop_after_threshold):
            heart._loop()

        self.assertEqual(heart.consecutive_failures, heartbeat.FAILURE_THRESHOLD)
        callback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
