"""Linux integration checks: python -m unittest discover -s tests (nginx + openssl)."""

import base64
import contextlib
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import shutil
import threading
import unittest

from runtime_auth import authenticated_ingress, COMFY_BACKEND, COMFY_INGRESS, GRADIO_BACKEND, GRADIO_INGRESS


class Backend(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() == "websocket":
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self.headers.get("Authorization", "no credential").encode())

    do_POST = do_GET

    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which("nginx") and shutil.which("openssl"), "requires nginx and openssl")
class IngressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = contextlib.ExitStack()
        cls.addClassCleanup(cls.stack.close)
        for port in (GRADIO_BACKEND, COMFY_BACKEND):
            server = cls.stack.enter_context(ThreadingHTTPServer(("127.0.0.1", port), Backend))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            cls.stack.callback(server.shutdown)
        password = secrets.token_urlsafe(32)
        cls.basic = "Basic " + base64.b64encode(f"easycolab:{password}".encode()).decode()
        cls.stack.enter_context(authenticated_ingress(password))

    def request(self, port, path, headers=None, method="GET"):
        with contextlib.closing(HTTPConnection("127.0.0.1", port, timeout=3)) as conn:
            conn.request(method, path, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read()

    def test_management_and_gradio(self):
        paths = ["/", "/config", "/gradio_api/queue/join", "/minimax_api/config_api_key",
                 "/minimax_api/disconnect", "/minimax_api/generate", "/minimax_api/comfyui/start"]
        for path in paths:
            for auth in ("", "Bearer inference-key", "Basic invalid"):
                with self.subTest(path=path, auth=auth):
                    self.assertEqual(self.request(GRADIO_INGRESS, path, {"Authorization": auth}, "POST")[0], 401)
            self.assertEqual(self.request(GRADIO_INGRESS, path, {"Authorization": self.basic}, "POST"),
                             (200, b"no credential"))

    def test_streaming_upgrade_and_origin(self):
        headers = {"Connection": "Upgrade", "Upgrade": "websocket"}
        self.assertEqual(self.request(COMFY_INGRESS, "/ws", headers)[0], 401)
        headers["Authorization"] = self.basic
        self.assertEqual(self.request(COMFY_INGRESS, "/ws", headers)[0], 101)
        headers["Origin"] = "https://untrusted.example"
        self.assertEqual(self.request(COMFY_INGRESS, "/ws", headers)[0], 403)
        headers.update(Origin="https://studio.example", Host="studio.example")
        self.assertEqual(self.request(COMFY_INGRESS, "/ws", headers)[0], 101)
        self.assertEqual(self.request(COMFY_INGRESS, "/prompt", method="POST")[0], 401)

    def test_only_inference_paths_pass_credentials_to_the_gateway(self):
        bearer = "Bearer inference-key"
        self.assertEqual(self.request(GRADIO_INGRESS, "/v1/models", {"Authorization": bearer}),
                         (200, bearer.encode()))
        for path in ("/v1/models/../minimax_api/status", "/v1/models%2f..%2fminimax_api/status",
                     "/v1/unknown", "/v1/models/"):
            self.assertEqual(self.request(GRADIO_INGRESS, path, {"Authorization": bearer})[0], 401)
