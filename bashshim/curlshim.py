import json
from urllib.parse import urlparse
try:  # optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

import bashshim.turnstile_test as turnstile_test


def run(shell, args):
    """Standalone curl command logic, decoupled from BashShim.

    shell: BashShim instance providing _log, allow_networking, home.
    args: list of command arguments.
    Returns (exit_code, output_str)
    """
    if not args:
        return 1, "curl: no URL specified\n"

    shell._log(f"curlshim: invoked curl with args: {args}")

    url = next((arg for arg in args if not arg.startswith("-")), None)
    if not url:
        return 1, "curl: no URL specified\n"

    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname
    path = parsed.path or "/"
    full_url = f"{scheme}://{host}{path}"

    if path in ["/403", "/404", "/500"]:
        shell._log(f"curlshim: rejecting access to {path} on purpose. meta errorception.")
        return 0, "HTTP/1.1 404 Not Found\nContent-Type: text/plain\n\n404 Not Found\n"

    shell._log(f"curlshim: target host = {host}, path = {path}, scheme = {scheme}")

    # Load JSON override rules (user can place this file anywhere & point via attribute)
    overrides_path = getattr(shell.home, "curl_override_path", "curl_overrides.json")
    try:
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    except Exception as e:  # pragma: no cover - missing file common
        shell._log(f"curlshim: override file load failed: {e}")
        overrides = {}

    host_rules = overrides.get(host)
    if host_rules:
        shell._log(f"curlshim: found override rules for {host}")

        # Handle auto-redirect from http to https
        if scheme == "http" and host_rules.get("upgrade_http", False):
            shell._log("curlshim: auto-upgrading http -> https per override rules")
            return 0, f"HTTP/1.1 301 Moved Permanently\nLocation: https://{host}{path}\n\n"

        route = host_rules.get(path)
        if not route:
            shell._log(f"curlshim: no rule for path '{path}', falling back to {host}/404")
            route = host_rules.get("/404")
            if not route:
                shell._log("curlshim: no /404 defined, using default not found output")
                return 0, "HTTP/1.1 404 Not Found\nContent-Type: text/plain\n\n404 Not Found\n"

        status = route.get("status", 200)
        headers = route.get("headers", {"Content-Type": "text/plain"})
        body = route.get("body", "")
        redirect_to = route.get("redirect_to")

        # Handle 403 or 500 with no body
        if status == 403 and not body:
            error_route = host_rules.get("/403")
            if error_route:
                shell._log("curlshim: using custom /403 error route")
                body = error_route.get("body", "")
                status = error_route.get("status", 200)
        elif status == 500 and not body:
            error_route = host_rules.get("/500")
            if error_route:
                shell._log("curlshim: using custom /500 error route")
                body = error_route.get("body", "")
                status = error_route.get("status", 200)

        # Construct response
        header_lines = [f"HTTP/1.1 {status}"]
        for key, val in headers.items():
            header_lines.append(f"{key}: {val}")
        if redirect_to:
            header_lines.append(f"Location: {redirect_to}")
        header_blob = "\n".join(header_lines)
        shell._log(f"curlshim: override matched. returning fake HTTP {status}")
        return 0, f"{header_blob}\n\n{body}\n"

    elif shell.allow_networking:
        shell._log(f"curlshim: no override for {host}. attempting real request...")
        if requests is None:
            shell._log("curlshim: requests library not available")
            return 6, f"curl: (6) Could not resolve host: {host}\n"
        if turnstile_test.is_behind_turnstile(full_url):
            shell._log(f"curlshim: BLOCKED by Cloudflare Turnstile: {full_url}")
            return 6, f"curl: (6) Could not resolve host: {host}\n"
        try:
            headers = {"User-Agent": "curl/7.88.1-bashshim"}
            response = requests.get(full_url, headers=headers, timeout=10)  # type: ignore
            shell._log(f"curlshim: real response received: HTTP {response.status_code}")
            header_blob = [f"HTTP/1.1 {response.status_code}"]
            for k, v in response.headers.items():
                header_blob.append(f"{k}: {v}")
            return 0, "\n".join(header_blob) + "\n\n" + response.text
        except Exception as e:  # pragma: no cover - network errors
            shell._log(f"curlshim: real request failed: {e}")
            return 7, f"curl: (7) Failed to connect to {host} after 10000 ms: Couldn't connect to server\n"
    else:
        shell._log(f"curlshim: networking disabled, and no override found for {host}")
        return 6, f"curl: (6) Could not resolve host: {host}\n"
