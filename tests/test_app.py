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

    def create(self, full_name, phone, attending, companions, code_hash, now):
        if self.by_phone(phone):
            raise self.duplicate_error()
        self.records.append({"id": len(self.records) + 1, "full_name": full_name, "phone": phone,
                             "attending": attending, "companions": companions,
                             "edit_code_hash": code_hash, "updated_at": now})

    def update(self, record_id, full_name, attending, companions, now):
        row = next(row for row in self.records if row["id"] == record_id)
        row.update(full_name=full_name, attending=attending, companions=companions, updated_at=now)

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
                "attending": "yes", "companions": "2"}
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
        updated = self.submit(attending="no", companions="4", edit_code=code)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(len(self.module.store.records), 1)
        self.assertFalse(self.module.store.records[0]["attending"])
        self.assertEqual(self.module.store.records[0]["companions"], 0)

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
        record_id = self.module.store.records[0]["id"]
        self.assertEqual(self.client.post(f"/admin/excluir/{record_id}", data={"csrf_token": self.csrf()}).status_code, 302)
        self.assertEqual(self.module.store.records, [])

    def test_csrf_and_validation(self):
        self.assertEqual(self.client.post("/confirmar", data={"full_name": "Ana"}).status_code, 400)
        self.assertEqual(self.submit(phone="123").status_code, 400)
        self.assertEqual(self.submit(attending="maybe").status_code, 400)
        self.assertEqual(self.submit(companions="99").status_code, 400)


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
