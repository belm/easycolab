"""Loopback ingress for the Gradio and Cloudflare tunnels on a Colab VM."""

import contextlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request


GRADIO_INGRESS = 7860
GRADIO_BACKEND = 27860
COMFY_INGRESS = 8188
COMFY_BACKEND = 28188
INFERENCE_PATHS = (
    "/models", "/chat/completions", "/images/generations",
    "/messages/count_tokens", "/messages",
    "/v1/models", "/v1/chat/completions", "/v1/images/generations",
    "/v1/messages/count_tokens", "/v1/messages",
    "/v1/v1/messages/count_tokens", "/v1/v1/messages",
)


def nginx_config(directory):
    # Send a canonical path to the inference backend. Its API-key check remains
    # mandatory. Every other path, including upgrades and future routes, is admin.
    inference = "\n".join(
        f"location = {path} {{ auth_basic off; proxy_pass http://127.0.0.1:{GRADIO_BACKEND}{path}; }}"
        for path in INFERENCE_PATHS
    )
    def server(port, backend, extra=""):
        return f"""
        server {{
            listen 127.0.0.1:{port};
            auth_basic "EasyColab";
            auth_basic_user_file "{directory}/users";
            if ($http_sec_fetch_site = cross-site) {{ return 403; }}
            set $origin_check $http_origin;
            if ($http_origin = https://$http_host) {{ set $origin_check ""; }}
            if ($origin_check != "") {{ return 403; }}
            {extra}
            location / {{
                proxy_set_header Host $http_host;
                proxy_set_header X-Forwarded-Proto https;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection $connection_upgrade;
                proxy_set_header Authorization "";
                proxy_pass http://127.0.0.1:{backend};
            }}
        }}
        """
    return f"""
    daemon off;
    master_process off;
    pid "{directory}/nginx.pid";
    error_log stderr warn;
    events {{ worker_connections 1024; }}
    http {{
        access_log off;
        map $http_upgrade $connection_upgrade {{ default upgrade; '' ''; }}
        client_max_body_size 0;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 3600s;
        proxy_hide_header Access-Control-Allow-Origin;
        {server(GRADIO_INGRESS, GRADIO_BACKEND, inference)}
        {server(COMFY_INGRESS, COMFY_BACKEND)}
    }}
    """


@contextlib.contextmanager
def authenticated_ingress(password):
    if not re.fullmatch(r"[A-Za-z0-9_-]{24,256}", password):
        raise ValueError("Management password must contain at least 24 URL-safe ASCII characters")
    nginx = shutil.which("nginx")
    if not nginx:
        raise RuntimeError("Install nginx on the runtime before starting EasyColab")
    with tempfile.TemporaryDirectory(prefix="easycolab-auth-") as directory:
        digest = subprocess.run(
            ["openssl", "passwd", "-6", "-stdin"], input=password, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        Path(directory, "users").write_text(f"easycolab:{digest}\n", encoding="ascii")
        config = Path(directory, "nginx.conf")
        config.write_text(nginx_config(directory), encoding="utf-8")
        with subprocess.Popen([nginx, "-p", directory, "-c", str(config)]) as proxy:
            try:
                # A wrong password must be challenged by both listeners before
                # either tunnel is published. Fail if a previous proxy owns a port.
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for port in (GRADIO_INGRESS, COMFY_INGRESS):
                    for _ in range(100):
                        if proxy.poll() is not None:
                            raise RuntimeError("Authenticated ingress failed to bind")
                        try:
                            opener.open(f"http://127.0.0.1:{port}/").close()
                        except urllib.error.HTTPError as error:
                            if error.code == 401:
                                break
                            raise
                        except urllib.error.URLError:
                            time.sleep(0.05)
                            continue
                        raise RuntimeError("Ingress accepted anonymous traffic")
                    else:
                        raise RuntimeError("Authenticated ingress did not start")
                # nginx retries occupied ports for a while before exiting. Its
                # private pid file appears only after both sockets are bound.
                if not Path(directory, "nginx.pid").exists():
                    raise RuntimeError("Ingress ports are already occupied")
                yield
            finally:
                proxy.terminate()
