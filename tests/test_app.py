import importlib
import os
import re
import unittest
from unittest.mock import patch


class FakeStore:
    def __init__(self, duplicate_error):
        self.records = []
        self.duplicate_error = duplicate_error

    def by_phone(self, phone):
        return next((row for row in self.records if row["phone"] == phone), None)

    def create(self, full_name, phone, attending, code_hash, now):
        if self.by_phone(phone):
            raise self.duplicate_error()
        self.records.append({"id": len(self.records) + 1, "full_name": full_name, "phone": phone,
                             "attending": attending,
                             "edit_code_hash": code_hash, "updated_at": now})

    def update(self, record_id, full_name, attending, now):
        row = next(row for row in self.records if row["id"] == record_id)
        row.update(full_name=full_name, attending=attending, updated_at=now)

    def all(self):
        return list(self.records)

    def delete(self, record_id):
        self.records = [row for row in self.records if row["id"] != record_id]


class InviteFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SUPABASE_URL"] = "https://example.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "sb_secret_test"
        os.environ["ADMIN_PASSWORD"] = "test-admin-password"
        os.environ["SECRET_KEY"] = "test-secret-key-with-enough-characters"
        cls.module = importlib.import_module("app")
        cls.module.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.module.app.test_client()
        self.module.store = FakeStore(self.module.DuplicatePhone)

    def csrf(self):
        with self.client.session_transaction() as state:
            return state["csrf_token"]

    def submit(self, **changes):
        self.client.get("/")
        data = {"csrf_token": self.csrf(), "full_name": "Ana Maria", "phone": "(11) 99999-1234",
                "attending": "yes"}
        data.update(changes)
        return self.client.post("/confirmar", data=data)

    def login(self):
        self.client.get("/admin/entrar")
        return self.client.post("/admin/entrar", data={"csrf_token": self.csrf(), "password": "test-admin-password"})

    def test_confirmation_duplicate_and_verified_update(self):
        first = self.submit()
        self.assertEqual(first.status_code, 200)
        self.assertIn("Presença <em>confirmada!</em>".encode(), first.data)
        code = re.search(rb'<strong>([A-F0-9]{12})</strong>', first.data).group(1).decode()
        self.assertEqual(self.submit(phone="+55 11 99999-1234").status_code, 409)
        self.assertEqual(self.submit(edit_code="WRONGCODE").status_code, 403)
        updated = self.submit(attending="no", edit_code=code)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(len(self.module.store.records), 1)
        self.assertFalse(self.module.store.records[0]["attending"])

    def test_private_dashboard_csv_and_delete(self):
        self.submit()
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.assertEqual(self.client.get("/admin/exportar.csv").status_code, 302)
        self.assertEqual(self.login().status_code, 302)
        dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Ana Maria", dashboard.data)
        csv_response = self.client.get("/admin/exportar.csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("Ana Maria", csv_response.get_data(as_text=True))
        self.assertNotIn("Acompanhantes", csv_response.get_data(as_text=True))
        record_id = self.module.store.records[0]["id"]
        self.assertEqual(self.client.post(f"/admin/excluir/{record_id}", data={"csrf_token": self.csrf()}).status_code, 302)
        self.assertEqual(self.module.store.records, [])

    def test_dashboard_search_by_phone_and_status(self):
        self.submit(full_name="Ana Maria", phone="(11) 99999-1234")
        self.submit(full_name="Bruno Lima", phone="(21) 3333-2222", attending="no")
        self.login()
        page = self.client.get("/admin?q=21&status=no").get_data(as_text=True)
        self.assertIn("Bruno Lima", page)
        self.assertNotIn("Ana Maria", page)
        self.assertIn("(21) 3333-2222", page)
        self.assertIn("tel:+552133332222", page)
        confirmed = self.client.get("/admin?status=yes").get_data(as_text=True)
        self.assertIn("Ana Maria", confirmed)
        self.assertNotIn("Bruno Lima", confirmed)

    def test_brazilian_phone_validation_and_format(self):
        self.assertEqual(self.module.normalize_phone("(11) 99999-1234"), "11999991234")
        self.assertEqual(self.module.normalize_phone("(21) 3333-2222"), "2133332222")
        self.assertEqual(self.module.format_phone("11999991234"), "(11) 99999-1234")
        self.assertIsNone(self.module.normalize_phone("(00) 99999-1234"))
        self.assertEqual(self.submit(phone="(00) 99999-1234").status_code, 400)

    def test_csrf_and_validation(self):
        self.assertEqual(self.client.post("/confirmar", data={"full_name": "Ana"}).status_code, 400)
        invalid = self.submit(phone="123")
        self.assertEqual(invalid.status_code, 400)
        self.assertIn(b'data-open-on-load="true"', invalid.data)
        self.assertIn(b'value="123"', invalid.data)
        self.assertEqual(self.submit(attending="maybe").status_code, 400)
        self.assertEqual(self.submit(companions="99", children="99").status_code, 200)
        self.assertNotIn("companions", self.module.store.records[0])

    def test_invite_has_no_companion_fields(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('<dialog id="rsvp-dialog"', page)
        self.assertEqual(page.count('data-open-rsvp'), 1)
        self.assertNotIn('class="rsvp-prompt"', page)
        self.assertNotIn('<section class="rsvp"', page)
        self.assertIn('id="edit-field" class="edit-field"', page)
        self.assertNotIn('name="companions"', page)
        self.assertNotIn('name="children"', page)
        self.assertNotIn('name="adult_names"', page)
        self.assertIn(self.module.EVENT["maps_url"], page)
        self.assertIn('title="Mapa do local da festa:', page)
        self.assertIn('Traçar rota', page)

    def test_invite_icons_are_local_svg(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('icon-party-popper', page)
        self.assertNotIn('🎉', page)
        for icon in ("party-popper", "calendar-days", "map-pin", "arrow-up-right", "x"):
            response = self.client.get(f"/static/icons/{icon}.svg")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"<svg", response.data)
            response.close()


class SupabaseRequestTest(unittest.TestCase):
    def test_secret_is_sent_in_apikey_header_only(self):
        from supabase_store import SupabaseStore

        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "sb_secret_test"}):
            store = SupabaseStore()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"[]"

        with patch("supabase_store.urlopen", return_value=FakeResponse()) as mocked:
            self.assertEqual(store.all(), [])
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Apikey"), "sb_secret_test")
        self.assertIsNone(request.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
