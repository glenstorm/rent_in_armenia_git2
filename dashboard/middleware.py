"""Redirect unverified visitors to the CAPTCHA gate."""

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from dashboard.bot_gate import gate_enabled, is_verified


class BotGateMiddleware:
    """Require a solved CAPTCHA session before serving public pages."""

    EXEMPT_PREFIXES = ("/admin/", "/static/", "/verify")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._requires_gate(request) and not is_verified(request):
            next_url = request.get_full_path()
            verify_url = reverse("bot_verify")
            if next_url and not next_url.startswith("/verify"):
                verify_url = f"{verify_url}?{urlencode({'next': next_url})}"
            return redirect(verify_url)
        return self.get_response(request)

    def _requires_gate(self, request) -> bool:
        if not gate_enabled():
            return False
        path = request.path
        return not any(
            path == prefix or path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES
        )
