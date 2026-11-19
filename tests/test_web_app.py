"""
Тесты webhook-режима: авторизация, /health, защита /set-webhook.
"""

import json

import pytest

from web_app import create_app


class StubBot:
    """Заглушка бота с методами webhook API."""

    def __init__(self):
        self.updates = []
        self.webhook_url = None
        self.secret = None

    def process_new_updates(self, updates):
        self.updates.extend(updates)

    def remove_webhook(self):
        self.webhook_url = None

    def set_webhook(self, url, secret_token=None, allowed_updates=None):
        self.webhook_url = url
        self.secret = secret_token
        return True


@pytest.fixture
def app_client():
    bot = StubBot()
    app = create_app(bot)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client, bot


def _post_update(client, headers=None):
    payload = {"update_id": 1, "message": {
        "message_id": 1, "date": 0,
        "chat": {"id": 1, "type": "private"},
        "from": {"id": 1, "is_bot": False, "first_name": "T"},
        "text": "/start",
    }}
    return client.post("/webhook", data=json.dumps(payload),
                       headers=headers or {"content-type": "application/json"})


def test_health_ok(app_client):
    client, _ = app_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_index_ok(app_client):
    client, _ = app_client
    assert client.get("/").status_code == 200


def test_webhook_accepts_json_update(app_client):
    client, bot = app_client
    assert _post_update(client).status_code == 200
    assert len(bot.updates) == 1


def test_webhook_rejects_wrong_content_type(app_client):
    client, _ = app_client
    response = client.post("/webhook", data="{}", headers={"content-type": "text/plain"})
    assert response.status_code == 400


def test_webhook_rejects_bad_secret(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "WEBHOOK_SECRET", "s3cret")
    client, bot = app_client
    bad = _post_update(client, {"content-type": "application/json",
                                "X-Telegram-Bot-Api-Secret-Token": "wrong"})
    assert bad.status_code == 403
    assert bot.updates == []


def test_webhook_accepts_good_secret(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "WEBHOOK_SECRET", "s3cret")
    client, bot = app_client
    ok = _post_update(client, {"content-type": "application/json",
                               "X-Telegram-Bot-Api-Secret-Token": "s3cret"})
    assert ok.status_code == 200
    assert len(bot.updates) == 1


def test_set_webhook_forbidden_without_admin_token(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "ADMIN_TOKEN", "")
    monkeypatch.setattr(web_app, "WEBHOOK_URL", "https://example.com")
    client, bot = app_client
    assert client.post("/set-webhook").status_code == 403
    assert bot.webhook_url is None


def test_set_webhook_requires_token(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "ADMIN_TOKEN", "admin-pass")
    monkeypatch.setattr(web_app, "WEBHOOK_URL", "https://example.com/")
    client, bot = app_client

    assert client.post("/set-webhook").status_code == 403
    response = client.post("/set-webhook", headers={"X-Admin-Token": "admin-pass"})
    assert response.status_code == 200
    assert bot.webhook_url == "https://example.com/webhook"


def test_set_webhook_without_url(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "ADMIN_TOKEN", "admin-pass")
    monkeypatch.setattr(web_app, "WEBHOOK_URL", "")
    client, _ = app_client
    assert client.post("/set-webhook", headers={"X-Admin-Token": "admin-pass"}).status_code == 400


def test_delete_webhook_requires_admin(app_client, monkeypatch):
    import web_app

    monkeypatch.setattr(web_app, "ADMIN_TOKEN", "admin-pass")
    client, bot = app_client
    assert client.post("/delete-webhook").status_code == 403
    assert client.post("/delete-webhook", headers={"X-Admin-Token": "admin-pass"}).status_code == 200
