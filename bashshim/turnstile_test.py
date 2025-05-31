import requests

def is_behind_turnstile(url):
    """
    Check if a URL is protected by Cloudflare Turnstile.
    Args:
        url (str): The URL to check.
    Returns:
        bool: True if the URL is behind Cloudflare Turnstile, False otherwise.
    """
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Request failed: {e}")
        return False

    # common status codes for challenge
    if resp.status_code in [403, 429, 503]:
        pass  # challenge likely
    elif "cf-mitigated" in resp.headers and "challenge" in resp.headers.get("cf-mitigated", ""):
        pass  # challenge confirmed via header
    else:
        return False

    # check for challenge markers
    challenge_keywords = [
        "cf-turnstile",                # iframe embed
        "data-sitekey",                # turnstile widget
        "challenges.cloudflare.com",  # js src or iframe src
        "Verification Required",       # title or body
        "challenge-form",              # cloudflare's injected form
    ]

    content = resp.text.lower()
    if any(keyword.lower() in content for keyword in challenge_keywords):
        return True

    return False
