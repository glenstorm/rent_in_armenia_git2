from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apartment import area_is_plausible
from house import house_price_is_plausible, house_rooms_are_plausible
from house_parser import HousePageParser
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


class HouseValidationTests(TestCase):
    def test_price_and_rooms(self):
        self.assertTrue(house_rooms_are_plausible(4))
        self.assertFalse(house_rooms_are_plausible(0))
        self.assertTrue(house_price_is_plausible(50_000_000))
        self.assertFalse(house_price_is_plausible(100 * 400))  # ~$100

    def test_parser_reads_rooms_and_square_from_title(self):
        html = """
        <div id="contentr"><div class="dl"><div class="gl">
          <a href="/ru/item/111">
            <div class="p">$120,000 </div>
            <div class="l">Двухэтажный каменный дом на ул. Калинина в Дилижане, 222 кв.м., на участке 344 кв.м., 2 ванные</div>
            <div class="at">Дилижан, 4 ком.</div>
          </a>
          <a href="/ru/item/222">
            <div class="p">$100 </div>
            <div class="l">Дом в Дилижане, 80 кв.м., на участке 200 кв.м.</div>
            <div class="at">Дилижан, 8 ком.</div>
          </a>
          <a href="/ru/item/333">
            <div class="p">$200,000 </div>
            <div class="l">Дом в Дилижане, 2,000 кв.м., на участке 2030 кв.м.</div>
            <div class="at">Дилижан, 5 ком.</div>
          </a>
        </div></div></div>
        """
        batch = HousePageParser.transform(html, 58, {1: 400.0, 2: 430.0})
        self.assertEqual(len(batch.houses), 2)
        by_link = {h.link: h for h in batch.houses}
        first = by_link["https://www.list.am/ru/item/111"]
        self.assertEqual(first.room_num, 4)
        self.assertEqual(first.square, 222)
        self.assertAlmostEqual(first.price_per_square, 48_000_000 / 222)
        big = by_link["https://www.list.am/ru/item/333"]
        self.assertEqual(big.square, 2000)

    def test_parser_filters_by_place_alias(self):
        html = """
        <div id="contentr"><div class="dl"><div class="gl">
          <a href="/ru/item/1">
            <div class="p">$80,000 </div>
            <div class="l">Дом в Агарцине, 90 кв.м., на участке 400 кв.м.</div>
            <div class="at">Агарцин, 3 ком.</div>
          </a>
          <a href="/ru/item/2">
            <div class="p">$90,000 </div>
            <div class="l">Дом в Дилижане, 100 кв.м., на участке 300 кв.м.</div>
            <div class="at">Дилижан, 4 ком.</div>
          </a>
        </div></div></div>
        """
        batch = HousePageParser.transform(
            html,
            1001,
            {1: 400.0, 2: 430.0},
            place_aliases=("Агарцин", "Haghartsin"),
        )
        self.assertEqual(len(batch.houses), 1)
        self.assertEqual(batch.houses[0].room_num, 3)
        self.assertEqual(batch.houses[0].square, 90)

    def test_parser_reads_redesigned_cards(self):
        html = """
        <div id="contentr"><div class="dl"><div class="gl">
          <div class="category-data-list-grid-card">
            <a href="/ru/item/555?ld_src=2" class="h">
              <div class="p"><span class="category-data-list-card__amount">
                <span class="category-data-list-card__currency">$</span>90,000
              </span></div>
              <div class="l">Дом в Дилижане, 98 кв.м., на участке 727 кв.м.</div>
              <div class="at">4 ком.</div>
              <div class="category-data-list-card__grid-bottom">
                <div class="at category-data-list-card__location">Дилижан</div>
              </div>
            </a>
          </div>
          <div class="category-data-list-grid-card">
            <a href="/ru/item/556?ld_src=2" class="h">
              <div class="p"><span class="category-data-list-card__amount">
                <span class="category-data-list-card__currency">$</span>80,000
              </span></div>
              <div class="l">Дом в Агарцине, 90 кв.м., на участке 400 кв.м.</div>
              <div class="at">3 ком.</div>
              <div class="category-data-list-card__grid-bottom">
                <div class="at category-data-list-card__location">Агарцин</div>
              </div>
            </a>
          </div>
        </div></div></div>
        """
        dilijan = HousePageParser.transform(html, 58, {1: 400.0, 2: 430.0})
        self.assertEqual(len(dilijan.houses), 2)
        self.assertEqual(dilijan.houses[0].room_num, 4)
        self.assertEqual(dilijan.houses[0].square, 98)
        self.assertEqual(dilijan.houses[0].link, "https://www.list.am/ru/item/555")

        hag = HousePageParser.transform(
            html,
            1001,
            {1: 400.0, 2: 430.0},
            place_aliases=("Агарцин", "Haghartsin"),
        )
        self.assertEqual(len(hag.houses), 1)
        self.assertEqual(hag.houses[0].link, "https://www.list.am/ru/item/556")


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
