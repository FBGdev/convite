"""Dados da festa. Altere este arquivo antes de compartilhar o convite."""

import os

EVENT = {
    "name": "Isabelle",
    "date": "2026-10-22",
    "time": "19:00",
    "venue": "Recanto dos Azevedos",
    "address": "Rua Padre Luís Riou, 625 · Campo Grande, Rio de Janeiro - RJ, 23013-320",
    "maps_url": "https://maps.app.goo.gl/DT68Jutc8zTHyJsK9",
    "map_latitude": -22.9023485,
    "map_longitude": -43.5365077,
    "message": "Uma noite para brindar a vida, reunir quem eu amo e criar novas memórias. Sua presença vai deixar essa festa ainda mais especial!",
    "pix_key": os.environ.get("PIX_KEY", "").strip() or "21964078715",
}
