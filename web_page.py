from urllib import request
from urllib.error import HTTPError, URLError


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebPage:
    """
    WebPage: downloaded html page which should being processed
    """

    @staticmethod
    def download(url):
        try:
            opener = request.build_opener(NoRedirect)
            opener.addheaders = [("User-agent", "Mozilla/5.0"), ("Cookie", "lang=1")]
            request.install_opener(opener)
            text = request.urlopen(url)
            content_type = text.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type.lower():
                charset = content_type.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"

            text_bytes = text.read()
            return text_bytes.decode(charset)
        except (HTTPError, URLError, UnicodeDecodeError, ValueError, OSError) as e:
            print(f"Something wrong with page {url}: {e}")
            return None
