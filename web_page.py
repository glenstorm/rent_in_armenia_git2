import time
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit


class WebPage:
    """
    WebPage: downloaded html page which should being processed
    """

    _HEADERS = [
        (
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
        ),
        (
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8",
        ),
        ("Accept-Language", "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"),
        ("Accept-Encoding", "identity"),
        ("Connection", "keep-alive"),
        ("Upgrade-Insecure-Requests", "1"),
        ("Referer", "https://www.list.am/ru/"),
        ("Cookie", "lang=1"),
    ]

    @staticmethod
    def _normalize_path(url):
        path = urlsplit(url).path.rstrip("/")
        if path.startswith("/ru/"):
            path = path[3:]
        elif path == "/ru":
            path = "/"
        return path

    @staticmethod
    def _is_end_of_results(requested_url, final_url):
        """Past the last listing page, list.am redirects away from /category/56/{page}."""
        return WebPage._normalize_path(requested_url) != WebPage._normalize_path(
            final_url
        )

    @staticmethod
    def download(url, max_retries=6, retry_delay=5.0):
        opener = request.build_opener()
        opener.addheaders = list(WebPage._HEADERS)
        request.install_opener(opener)

        for attempt in range(max_retries):
            try:
                response = request.urlopen(url, timeout=30)
                final_url = response.geturl()
                if WebPage._is_end_of_results(url, final_url):
                    return None

                content_type = response.headers.get("Content-Type", "")
                charset = "utf-8"
                if "charset=" in content_type.lower():
                    charset = (
                        content_type.split("charset=", 1)[1].split(";")[0].strip()
                        or "utf-8"
                    )

                return response.read().decode(charset)
            except HTTPError as e:
                # Rate limit / temporary block — wait and retry
                if e.code in (403, 429) and attempt + 1 < max_retries:
                    retry_after = e.headers.get("Retry-After")
                    try:
                        wait = float(retry_after) if retry_after else retry_delay * (
                            2**attempt
                        )
                    except ValueError:
                        wait = retry_delay * (2**attempt)
                    wait = min(wait, 120.0)
                    print(
                        f"HTTP {e.code} for {url}; retrying in {wait:.0f}s "
                        f"({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait)
                    continue

                # Redirects that urllib did not follow (should be rare with default opener)
                if e.code in (301, 302, 303, 307, 308):
                    return None

                print(f"Something wrong with page {url}: {e}")
                return None
            except (URLError, UnicodeDecodeError, ValueError, OSError) as e:
                if attempt + 1 < max_retries:
                    wait = retry_delay * (2**attempt)
                    print(
                        f"Network error for {url}: {e}; retrying in {wait:.0f}s "
                        f"({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait)
                    continue
                print(f"Something wrong with page {url}: {e}")
                return None

        print(f"Something wrong with page {url}: retries exhausted")
        return None
