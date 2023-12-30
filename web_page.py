from urllib import request
import urllib.error

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
			opener.addheaders = [('User-agent', 'Mozilla/5.0'), ("Cookie", "lang=1")]
			request.install_opener(opener)
			text = request.urlopen(url)
			charset = text.headers.get('Content-Type').split('charset=',1)[1]
			if not charset:
				charset = 'utf8'

			text_bytes = text.read()
			# converting bytearray to string datatype
			text_str = text_bytes.decode(charset)
			return text_str

		except Exception as e:
			pass
			# print("Something wrong with page {0}: {1}".format(url, e) )
			# raise SystemExit
