import signal
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import vpn


class FakeHeartbeat:
    def __init__(self):
        self.on_dead_callback = None
        self.start = Mock()
        self.stop = Mock()

    def on_dead(self, callback):
        self.on_dead_callback = callback


def make_manager(user="alice", password="secret"):
    config = SimpleNamespace(
        user=user,
        password=password,
        options="--protocol=anyconnect --servercert pin",
        url="https://vpn.example",
    )
    heartbeat = FakeHeartbeat()
    return vpn.VpnManager(config, heartbeat), heartbeat


class VpnManagerTests(unittest.TestCase):
    @patch("vpn.subprocess.Popen")
    def test_connect_without_credentials_sets_error(self, popen):
        manager, _ = make_manager(user="", password="")

        manager.connect()

        self.assertEqual(manager.state, vpn.VpnState.ERROR)
        self.assertEqual(manager.state_msg, "Username and password required")
        popen.assert_not_called()

    @patch("vpn.threading.Thread")
    @patch("vpn.subprocess.Popen")
    def test_connect_starts_process_with_command_and_password(self, popen, thread):
        process = Mock()
        process.poll.return_value = None
        process.stdin = BytesIO()
        process.stdout = BytesIO()
        popen.return_value = process
        manager, _ = make_manager()

        manager.connect()

        popen.assert_called_once_with(
            [
                "openconnect", "-u", "alice", "--passwd-on-stdin",
                "--script-tun", "--script=ocproxy -g -D 1081",
                "--protocol=anyconnect", "--servercert", "pin",
                "https://vpn.example",
            ],
            stdin=vpn.subprocess.PIPE,
            stdout=vpn.subprocess.PIPE,
            stderr=vpn.subprocess.STDOUT,
        )
        self.assertEqual(process.stdin.getvalue(), b"secret\n")
        thread.assert_called_once()

    def test_output_prompt_requests_mfa(self):
        manager, _ = make_manager()

        manager._read_output(BytesIO(b"Answer: \n"))

        self.assertEqual(manager.state, vpn.VpnState.WAITING_MFA)
        self.assertEqual(manager.state_msg, "2FA code required")

    def test_submit_mfa_writes_code_and_resumes_connecting(self):
        manager, _ = make_manager()
        process = Mock()
        process.poll.return_value = None
        process.stdin = BytesIO()
        manager._proc = process
        manager.state = vpn.VpnState.WAITING_MFA

        manager.submit_mfa("  123456  ")

        self.assertEqual(process.stdin.getvalue(), b"123456\n")
        self.assertEqual(manager.state, vpn.VpnState.CONNECTING)
        self.assertEqual(manager.state_msg, "MFA code sent. Waiting for connection\u2026")

    def test_connected_output_updates_state_and_starts_heartbeat(self):
        manager, heartbeat = make_manager()

        manager._read_output(BytesIO(b"Configured as 192.0.2.1, with SSL connected and DTLS disabled\n"))

        self.assertEqual(manager.state, vpn.VpnState.CONNECTED)
        self.assertEqual(manager.state_msg, "VPN connected")
        heartbeat.start.assert_called_once_with()

    def test_login_https_and_dtls_messages_do_not_start_heartbeat(self):
        manager, heartbeat = make_manager()
        manager.state = vpn.VpnState.CONNECTING

        manager._read_output(BytesIO(
            b"Connected to HTTPS on vpn.example\nDTLS disabled\nAnswer:\n"
        ))

        self.assertEqual(manager.state, vpn.VpnState.WAITING_MFA)
        heartbeat.start.assert_not_called()

    def test_process_exit_updates_state_and_stops_heartbeat(self):
        manager, heartbeat = make_manager()
        process = Mock()
        process.stdout = BytesIO(b"authentication failed\n")
        process.wait.return_value = 1
        manager._proc = process
        manager.state = vpn.VpnState.CONNECTING

        manager._read_output(process.stdout)

        self.assertEqual(manager.state, vpn.VpnState.ERROR)
        self.assertEqual(manager.state_msg, "openconnect exited with code 1")
        self.assertIsNone(manager._proc)
        heartbeat.stop.assert_called_once_with()

    def test_disconnect_stops_process_and_heartbeat(self):
        manager, heartbeat = make_manager()
        process = Mock()
        process.poll.return_value = None
        manager._proc = process

        manager.disconnect()

        process.send_signal.assert_called_once_with(signal.SIGINT)
        process.wait.assert_called_once_with(timeout=5)
        heartbeat.stop.assert_called_once_with()
        self.assertIsNone(manager._proc)
        self.assertEqual(manager.state, vpn.VpnState.DISCONNECTED)


if __name__ == "__main__":
    unittest.main()
