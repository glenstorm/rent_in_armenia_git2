from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apartment import area_is_plausible
from dashboard.bot_gate import SESSION_CODE_KEY, SESSION_ISSUED_KEY, SESSION_OK_KEY


class AreaValidationTests(TestCase):
    def test_rejects_tiny_and_huge_squares(self):
        self.assertFalse(area_is_plausible(3, 5))
        self.assertFalse(area_is_plausible(3, 3))
        self.assertFalse(area_is_plausible(4, 8))
        self.assertFalse(area_is_plausible(2, 640))
        self.assertFalse(area_is_plausible(1, 14))

    def test_accepts_normal_flats(self):
        self.assertTrue(area_is_plausible(1, 40))
        self.assertTrue(area_is_plausible(2, 55))
        self.assertTrue(area_is_plausible(3, 90))
        self.assertTrue(area_is_plausible(4, 120))
        self.assertTrue(area_is_plausible(5, 180))


@override_settings(BOT_GATE_ENABLED=True, BOT_GATE_MIN_SOLVE_SECONDS=0)
class BotGateTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_redirects_to_verify(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/verify/", response["Location"])

    def test_verify_page_renders(self):
        response = self.client.get(reverse("bot_verify"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm you are not a bot")

    def test_captcha_image_returns_svg(self):
        response = self.client.get(reverse("bot_captcha_image"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", response.content)

    def test_wrong_captcha_rejected(self):
        session = self.client.session
        session[SESSION_CODE_KEY] = "ABCDE"
        session[SESSION_ISSUED_KEY] = 0
        session.save()

        response = self.client.post(
            reverse("bot_verify"),
            {"captcha": "ZZZZZ", "company_url": "", "next": "/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect CAPTCHA")
        self.assertNotIn(SESSION_OK_KEY, self.client.session)

    def test_correct_captcha_unlocks_pages(self):
        session = self.client.session
        session[SESSION_CODE_KEY] = "ABCDE"
        session[SESSION_ISSUED_KEY] = 0
        session.save()

        response = self.client.post(
            reverse("bot_verify"),
            {"captcha": "abcde", "company_url": "", "next": "/"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertIn(SESSION_OK_KEY, self.client.session)

        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)

    def test_honeypot_rejected(self):
        session = self.client.session
        session[SESSION_CODE_KEY] = "ABCDE"
        session[SESSION_ISSUED_KEY] = 0
        session.save()

        response = self.client.post(
            reverse("bot_verify"),
            {"captcha": "ABCDE", "company_url": "http://spam.example", "next": "/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verification failed")
        self.assertNotIn(SESSION_OK_KEY, self.client.session)


@override_settings(BOT_GATE_ENABLED=False)
class BotGateDisabledTests(TestCase):
    def test_home_accessible_without_captcha(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
