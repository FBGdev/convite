"""Acesso privado à Data API do Supabase para as respostas do convite."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class StoreError(Exception):
    pass


class DuplicatePhone(StoreError):
    pass


class SupabaseStore:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SECRET_KEY", "")
        if not url.startswith("https://") or not key:
            raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SECRET_KEY no servidor.")
        self.endpoint = f"{url}/rest/v1/rsvps"
        self.key = key

    def _request(self, method="GET", params=None, payload=None):
        url = self.endpoint
        if params:
            url += "?" + urlencode(params)
        headers = {
            "apikey": self.key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=12) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            try:
                error = json.loads(exc.read())
            except (ValueError, OSError):
                error = {}
            if exc.code == 409 and error.get("code") == "23505":
                raise DuplicatePhone from exc
            error_code = error.get("code") or "sem código"
            error_message = error.get("message") or "sem mensagem"
            raise StoreError(
                f"Supabase respondeu com HTTP {exc.code} ({error_code}): {error_message[:300]}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise StoreError("Não foi possível acessar o Supabase.") from exc

    def by_phone(self, phone):
        rows = self._request(params={"select": "id", "phone": f"eq.{phone}", "limit": "1"})
        return rows[0] if rows else None

    def create(self, full_name, phone, attending, companion_names, now):
        self._request("POST", payload={
            "full_name": full_name,
            "phone": phone,
            "attending": attending,
            "companion_names": companion_names,
            "companions": len(companion_names),
            "children": 0,
            "created_at": now,
            "updated_at": now,
        })

    def all(self):
        rows = []
        offset = 0
        while True:
            batch = self._request(params={
                "select": "id,full_name,phone,attending,companion_names,wife_name,children_names,companions,children,updated_at",
                "order": "updated_at.desc,id.desc",
                "limit": "500",
                "offset": str(offset),
            })
            rows.extend(batch)
            if len(batch) < 500:
                return rows
            offset += 500

    def delete(self, record_id):
        self._request("DELETE", params={"id": f"eq.{record_id}"})
