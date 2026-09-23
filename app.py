"""Convite de aniversário com confirmação de presença e painel privado."""

import csv
import hmac
import io
import os
import re
import secrets
import time
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import quote
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for

from config import EVENT
from supabase_store import DuplicatePhone, StoreError, SupabaseStore


APP_SECRET = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
store = SupabaseStore()

app = Flask(__name__)
app.secret_key = APP_SECRET
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    MAX_CONTENT_LENGTH=16 * 1024,
)

_login_attempts = {}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def require_csrf():
    submitted = request.form.get("csrf_token", "")
    if not submitted or not hmac.compare_digest(submitted, session.get("csrf_token", "")):
        abort(400, "Formulário expirado. Atualize a página e tente novamente.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def normalize_phone(value):
    digits = re.sub(r"\D", "", value)
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) not in (10, 11) or digits[0] == "0" or digits[1] == "0":
        return None
    return digits


def format_phone(value):
    digits = normalize_phone(value)
    if not digits:
        return value
    return f"({digits[:2]}) {digits[2:-4]}-{digits[-4:]}"


def display_date(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M")


app.jinja_env.filters["br_date"] = display_date
app.jinja_env.filters["br_phone"] = format_phone


def companion_names(row):
    names = row.get("companion_names") or []
    if names:
        return names
    return [name for name in [row.get("wife_name"), *(row.get("children_names") or [])] if name]


app.jinja_env.filters["companion_names"] = companion_names


@app.context_processor
def event_context():
    date = datetime.strptime(EVENT["date"], "%Y-%m-%d")
    return {
        "event": EVENT,
        "event_day": date.strftime("%d"),
        "event_short_date": date.strftime("%d.%m.%Y"),
        "event_short_time": EVENT["time"].replace(":00", "H"),
        "event_month": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"][date.month - 1],
        "event_weekday": ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"][date.weekday()],
        "public_site_url": os.environ.get("PUBLIC_SITE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/"),
        "maps_url": EVENT.get("maps_url") or "https://www.google.com/maps/search/?api=1&query=" + quote(EVENT["address"]),
        "directions_url": "https://www.google.com/maps/dir/?api=1&destination=" + quote(f"{EVENT['map_latitude']},{EVENT['map_longitude']}"),
        "map_embed_url": f"https://maps.google.com/maps?q={EVENT['map_latitude']},{EVENT['map_longitude']}&z=17&output=embed",
    }


@app.route("/")
def invite():
    return render_template("invite.html")


@app.post("/confirmar")
def confirm():
    require_csrf()
    name = " ".join(request.form.get("full_name", "").split())
    phone_input = request.form.get("phone", "").strip()
    phone = normalize_phone(phone_input)
    answer = request.form.get("attending")
    submitted_companions = request.form.getlist("companion_names")
    names = [" ".join(person.split()) for person in submitted_companions]
    old_family_fields = any(field in request.form for field in ("bring_wife", "wife_name", "child_names"))
    form = {"full_name": name, "phone": phone_input, "attending": answer,
            "companion_names": names}

    error = None
    if old_family_fields:
        error = "O formulário mudou. Atualize a página e informe seus acompanhantes novamente."
    elif len(name) < 3 or len(name) > 120:
        error = "Informe seu nome completo (3 a 120 caracteres)."
    elif not phone:
        error = "Informe um telefone com DDD válido."
    elif answer not in ("yes", "no"):
        error = "Selecione se você vai comparecer."
    elif answer == "no" and any(names):
        error = "Informe acompanhantes somente se você for à festa."
    elif len(submitted_companions) > 6:
        error = "Você pode adicionar até seis acompanhantes."
    elif any(person and not 2 <= len(person) <= 120 for person in names):
        error = "Informe o nome de cada acompanhante com 2 a 120 caracteres."

    if error:
        return render_template("invite.html", error=error, form=form), 400

    now = datetime.now(timezone.utc).isoformat()
    try:
        existing = store.by_phone(phone)
        if existing:
            return render_template("invite.html", error="Este telefone já respondeu. Se precisar corrigir sua resposta, fale com a aniversariante.", form=form), 409
        store.create(name, phone, answer == "yes", [person for person in names if person], now)
    except DuplicatePhone:
        return render_template("invite.html", error="Este telefone já respondeu. Se precisar corrigir sua resposta, fale com a aniversariante.", form=form), 409
    except StoreError:
        app.logger.exception("Erro ao salvar confirmação no Supabase")
        return render_template("invite.html", error="Não foi possível registrar sua resposta agora. Tente novamente em instantes.", form=form), 503

    return render_template("success.html", attending=answer == "yes")


@app.route("/admin/entrar", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("admin_dashboard"))
    error = None
    if request.method == "POST":
        require_csrf()
        key = request.remote_addr or "unknown"
        attempts = [timestamp for timestamp in _login_attempts.get(key, []) if time.monotonic() - timestamp < 900]
        if len(attempts) >= 8:
            error = "Muitas tentativas. Aguarde 15 minutos para tentar novamente."
        elif not ADMIN_PASSWORD:
            error = "A senha do painel ainda não foi configurada no servidor."
        elif hmac.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            _login_attempts.pop(key, None)
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            attempts.append(time.monotonic())
            _login_attempts[key] = attempts
            error = "Senha incorreta. Tente novamente."
    return render_template("admin_login.html", error=error), 400 if error else 200


@app.post("/admin/sair")
@admin_required
def admin_logout():
    require_csrf()
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    query = request.args.get("q", "").strip()[:120]
    status = request.args.get("status", "all")
    if status not in ("all", "yes", "no"):
        status = "all"
    try:
        all_rows = store.all()
    except StoreError:
        app.logger.exception("Erro ao consultar confirmações no Supabase")
        abort(503, "O painel está indisponível no momento. Tente novamente em instantes.")
    totals = {
        "responses": len(all_rows),
        "attending": sum(1 + row.get("companions", 0) + row.get("children", 0)
                         for row in all_rows if row["attending"]),
        "declining": sum(not row["attending"] for row in all_rows),
    }
    query_digits = re.sub(r"\D", "", query)
    rows = [row for row in all_rows if
            (not query or query.casefold() in row["full_name"].casefold() or
             any(query.casefold() in person.casefold() for person in companion_names(row)) or
             (query_digits and query_digits in row["phone"])) and
            (status == "all" or bool(row["attending"]) == (status == "yes"))]
    return render_template("admin.html", totals=totals, rows=rows, query=query, status=status)


@app.post("/admin/excluir/<int:rsvp_id>")
@admin_required
def admin_delete(rsvp_id):
    require_csrf()
    try:
        store.delete(rsvp_id)
    except StoreError:
        app.logger.exception("Erro ao excluir confirmação no Supabase")
        abort(503, "Não foi possível excluir a resposta agora.")
    flash("Resposta excluída.")
    return redirect(url_for("admin_dashboard"))


def csv_safe(value):
    text = str(value)
    return "'" + text if text and text[0] in "=+-@\t\r\n" else text


@app.get("/admin/exportar.csv")
@admin_required
def admin_export():
    try:
        rows = sorted(store.all(), key=lambda row: row["full_name"].casefold())
    except StoreError:
        app.logger.exception("Erro ao exportar confirmações do Supabase")
        abort(503, "Não foi possível exportar a lista agora.")
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Nome", "Telefone", "Resposta", "Acompanhantes", "Total de pessoas", "Data da confirmação"])
    for row in rows:
        writer.writerow([csv_safe(row["full_name"]), row["phone"],
                         "Sim" if row["attending"] else "Não",
                         csv_safe(", ".join(companion_names(row))),
                         1 + row.get("companions", 0) + row.get("children", 0) if row["attending"] else 0,
                         display_date(row["updated_at"])])
    response = Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = 'attachment; filename="confirmacoes.csv"'
    response.headers["Cache-Control"] = "no-store"
    return response


@app.after_request
def private_headers(response):
    if request.path.startswith("/admin") or request.path == "/confirmar":
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
