import importlib
import json
import os
import unittest
from unittest.mock import patch


class FakeStore:
    def __init__(self, duplicate_error):
        self.records = []
        self.duplicate_error = duplicate_error

    def by_phone(self, phone):
        return next((row for row in self.records if row["phone"] == phone), None)

    def create(self, full_name, phone, attending, wife_name, children_names, now):
        if self.by_phone(phone):
            raise self.duplicate_error()
        self.records.append({"id": len(self.records) + 1, "full_name": full_name, "phone": phone,
                             "attending": attending, "wife_name": wife_name,
                             "children_names": children_names,
                             "companions": 1 if wife_name else 0,
                             "children": len(children_names),
                             "updated_at": now})

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

    def test_confirmation_duplicate_without_gift_prompt(self):
        first = self.submit()
        self.assertEqual(first.status_code, 200)
        self.assertIn("Presença <em>confirmada!</em>".encode(), first.data)
        self.assertIn("Traga sua bebida alcoólica de preferência.".encode(), first.data)
        self.assertNotIn(self.module.EVENT["pix_key"].encode(), first.data)
        self.assertNotIn(b'id="copy-pix"', first.data)
        self.assertNotIn("CÓDIGO DE EDIÇÃO".encode(), first.data)
        self.assertEqual(self.submit(phone="+55 11 99999-1234").status_code, 409)
        self.assertEqual(self.submit(attending="no", edit_code="WRONGCODE").status_code, 409)
        self.assertEqual(len(self.module.store.records), 1)
        self.assertTrue(self.module.store.records[0]["attending"])

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
        self.assertEqual(self.module.store.records[0]["companions"], 0)
        self.assertEqual(self.module.store.records[0]["children"], 0)

    def test_invite_has_only_wife_and_children_fields(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('<dialog id="rsvp-dialog"', page)
        self.assertEqual(page.count('data-open-rsvp'), 1)
        self.assertNotIn('class="rsvp-prompt"', page)
        self.assertNotIn('<section class="rsvp"', page)
        self.assertNotIn('name="edit_code"', page)
        self.assertNotIn('name="companions"', page)
        self.assertNotIn('name="children"', page)
        self.assertNotIn('name="adult_names"', page)
        self.assertIn('name="bring_wife"', page)
        self.assertIn('name="wife_name"', page)
        self.assertEqual(page.count('name="child_names"'), 2)
        self.assertIn(self.module.EVENT["maps_url"], page)
        self.assertIn('title="Mapa do local da festa:', page)
        self.assertIn('Traçar rota', page)

    def test_invite_uses_typographic_opening_and_gift_suggestions(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('<span class="hero-age">30</span>', page)
        self.assertIn('22.10.2026 · 19H', page)
        self.assertIn('Uma noite para celebrar brindar e sambar', page)
        self.assertNotIn('birthday-art.svg', page)
        self.assertNotIn('VOCÊ ESTÁ CONVIDADO(A)', page)
        self.assertIn('Sugestões de <em>presente.</em>', page)
        self.assertIn('<strong>Roupas</strong>', page)
        self.assertIn('Parte superior: G · Parte inferior: 44', page)
        self.assertEqual(page.count('Traga sua bebida alcoólica de preferência.'), 2)
        self.assertIn('<strong>Perfumes</strong>', page)
        self.assertIn('<strong>Bolsas e Acessórios</strong>', page)
        self.assertIn('<summary><span>04</span><strong>Pix</strong>', page)
        self.assertIn('<details class="gift-option gift-pix">', page)

    def test_invite_icons_are_local_svg(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('icon-party-popper', page)
        self.assertNotIn('🎉', page)
        for icon in ("party-popper", "calendar-days", "map-pin", "arrow-up-right", "x"):
            response = self.client.get(f"/static/icons/{icon}.svg")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"<svg", response.data)
            response.close()

    def test_family_names_are_saved_and_counted(self):
        response = self.submit(bring_wife="yes", wife_name="  Beatriz   Maria  ",
                               child_names=["Carlos", "Dora"])
        self.assertEqual(response.status_code, 200)
        row = self.module.store.records[0]
        self.assertEqual(row["wife_name"], "Beatriz Maria")
        self.assertEqual(row["children_names"], ["Carlos", "Dora"])
        self.assertEqual((row["companions"], row["children"]), (1, 2))
        self.login()
        dashboard = self.client.get("/admin").get_data(as_text=True)
        self.assertIn("Beatriz Maria", dashboard)
        self.assertIn("Carlos", dashboard)
        self.assertIn("<strong>4</strong>", dashboard)
        self.assertIn("Ana Maria", self.client.get("/admin?q=Dora").get_data(as_text=True))
        csv_text = self.client.get("/admin/exportar.csv").get_data(as_text=True)
        self.assertIn("Esposa;Filhos;Total de pessoas", csv_text)
        self.assertIn("Beatriz Maria", csv_text)
        self.assertIn("Carlos, Dora;4", csv_text)

    def test_family_validation_and_error_preserves_names(self):
        self.assertEqual(self.submit(bring_wife="yes", wife_name="").status_code, 400)
        self.assertEqual(self.submit(wife_name="Beatriz").status_code, 400)
        self.assertEqual(self.submit(child_names=["Carlos", "Dora", "Elisa"]).status_code, 400)
        self.assertEqual(self.submit(attending="no", bring_wife="yes", wife_name="Beatriz").status_code, 400)
        self.assertEqual(self.submit(attending="no", child_names=["Carlos"]).status_code, 400)
        invalid = self.submit(bring_wife="yes", wife_name="Beatriz", child_names=["C"])
        self.assertEqual(invalid.status_code, 400)
        self.assertIn(b'value="Beatriz"', invalid.data)
        self.assertIn(b'value="C"', invalid.data)
        self.assertEqual(self.module.store.records, [])

    def test_wife_and_children_are_optional_for_an_individual_or_decline(self):
        self.assertEqual(self.submit(child_names=["Carlos", ""]).status_code, 200)
        self.assertEqual(self.module.store.records[0]["children_names"], ["Carlos"])
        decline = self.submit(full_name="Bruno Lima", phone="(21) 3333-2222", attending="no")
        self.assertEqual(decline.status_code, 200)
        self.assertNotIn("Traga sua bebida alcoólica de preferência.".encode(), decline.data)
        self.assertEqual(self.module.store.records[1]["children_names"], [])
        self.login()
        dashboard = self.client.get("/admin").get_data(as_text=True)
        self.assertIn("<strong>2</strong>", dashboard)

    def test_existing_rows_without_family_names_remain_visible(self):
        self.module.store.records.append({
            "id": 1, "full_name": "Pessoa Antiga", "phone": "11999991234",
            "attending": True, "companions": 1, "children": 1,
            "updated_at": "2026-09-22T00:00:00+00:00",
        })
        self.login()
        dashboard = self.client.get("/admin").get_data(as_text=True)
        self.assertIn("Pessoa Antiga", dashboard)
        self.assertIn("<strong>3</strong>", dashboard)
        csv_text = self.client.get("/admin/exportar.csv").get_data(as_text=True)
        self.assertIn("Pessoa Antiga", csv_text)
        self.assertIn("Sim;;;3;", csv_text)


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

    def test_new_rsvp_does_not_send_edit_code(self):
        from supabase_store import SupabaseStore

        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "sb_secret_test"}):
            store = SupabaseStore()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b""

        with patch("supabase_store.urlopen", return_value=FakeResponse()) as mocked:
            store.create("Ana Maria", "11999991234", True, "Beatriz", ["Carlos"], "2026-09-22T00:00:00+00:00")
        payload = json.loads(mocked.call_args.args[0].data)
        self.assertNotIn("edit_code_hash", payload)
        self.assertEqual(payload["wife_name"], "Beatriz")
        self.assertEqual(payload["children_names"], ["Carlos"])
        self.assertEqual((payload["companions"], payload["children"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
