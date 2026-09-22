import importlib
import os
import tempfile
import unittest
from pathlib import Path


class InviteFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(cls.temp.name) / "responses.sqlite3")
        os.environ["ADMIN_PASSWORD"] = "test-admin-password"
        os.environ["SECRET_KEY"] = "test-secret-key-with-enough-characters"
        cls.module = importlib.import_module("app")
        cls.module.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.client = self.module.app.test_client()
        with self.module.db_connection() as db:
            db.execute("DELETE FROM rsvps")

    def csrf(self):
        with self.client.session_transaction() as state:
            return state["csrf_token"]

    def submit(self, **changes):
        self.client.get("/")
        data = {
            "csrf_token": self.csrf(),
            "full_name": "Ana Maria",
            "phone": "(11) 99999-1234",
            "attending": "yes",
            "companions": "2",
        }
        data.update(changes)
        return self.client.post("/confirmar", data=data)

    def login(self):
        self.client.get("/admin/entrar")
        return self.client.post("/admin/entrar", data={"csrf_token": self.csrf(), "password": "test-admin-password"})

    def test_confirmation_duplicate_and_verified_update(self):
        first = self.submit()
        self.assertEqual(first.status_code, 200)
        self.assertIn("Presença <em>confirmada!</em>".encode(), first.data)
        with self.module.db_connection() as db:
            row = db.execute("SELECT * FROM rsvps").fetchone()
            self.assertEqual(row["companions"], 2)
            code_hash = row["edit_code_hash"]
        self.assertEqual(self.submit(phone="+55 11 99999-1234").status_code, 409)
        self.assertEqual(self.submit(edit_code="WRONGCODE").status_code, 403)
        # O código exibido tem 12 caracteres hexadecimais. Nesta prova, recuperamos
        # o valor da página de sucesso de uma nova resposta para validar a atualização.
        import re
        self.submit(phone="11988881234")
        with self.module.db_connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rsvps").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT edit_code_hash FROM rsvps WHERE phone = ?", ("11999991234",)).fetchone()[0], code_hash)
        second_client = self.module.app.test_client()
        page = second_client.get("/")
        token = re.search(rb'name="csrf_token" value="([^"]+)', page.data).group(1).decode()
        result = second_client.post("/confirmar", data={"csrf_token": token, "full_name": "Bia Costa", "phone": "11977771234", "attending": "yes", "companions": "0"})
        code = re.search(rb'<strong>([A-F0-9]{12})</strong>', result.data).group(1).decode()
        update = second_client.post("/confirmar", data={"csrf_token": token, "full_name": "Bia Costa", "phone": "11977771234", "attending": "no", "companions": "4", "edit_code": code})
        self.assertEqual(update.status_code, 200)
        with self.module.db_connection() as db:
            row = db.execute("SELECT attending, companions FROM rsvps WHERE phone = ?", ("11977771234",)).fetchone()
            self.assertEqual((row["attending"], row["companions"]), (0, 0))

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
        with self.module.db_connection() as db:
            rsvp_id = db.execute("SELECT id FROM rsvps").fetchone()[0]
        self.assertEqual(self.client.post(f"/admin/excluir/{rsvp_id}", data={"csrf_token": self.csrf()}).status_code, 302)
        with self.module.db_connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rsvps").fetchone()[0], 0)

    def test_csrf_and_validation(self):
        self.assertEqual(self.client.post("/confirmar", data={"full_name": "Ana"}).status_code, 400)
        self.assertEqual(self.submit(phone="123").status_code, 400)
        self.assertEqual(self.submit(attending="maybe").status_code, 400)
        self.assertEqual(self.submit(companions="99").status_code, 400)


if __name__ == "__main__":
    unittest.main()
