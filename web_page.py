from urllib import request
from urllib.error import HTTPError, URLError


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


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
    def download(url):
        try:
            opener = request.build_opener(NoRedirect)
            opener.addheaders = list(WebPage._HEADERS)
            request.install_opener(opener)
            text = request.urlopen(url, timeout=30)
            content_type = text.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type.lower():
                charset = content_type.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"

            text_bytes = text.read()
            return text_bytes.decode(charset)
        except (HTTPError, URLError, UnicodeDecodeError, ValueError, OSError) as e:
            print(f"Something wrong with page {url}: {e}")
            return None
