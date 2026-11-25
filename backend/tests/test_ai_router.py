"""Provider routing: consent, explicit modes and no silent cloud fallback."""

from __future__ import annotations

import pytest

from app.ai import router as ai_router
from app.ai.base import AIError, AIResult, ProviderUnavailable
from app.settings_service import update_settings


class FakeLocal:
    async def generate(self, **kwargs) -> AIResult:
        return AIResult(text="local answer", provider="local", model="fake-qwen", latency_ms=1)


@pytest.fixture()
def local_only(monkeypatch):
    async def fake_ensure(db, *, vision=False):
        return None

    def fake_local(db):
        return FakeLocal()

    def boom(db):
        raise AssertionError("Gemini must not be contacted in local-only mode")

    monkeypatch.setattr(ai_router, "_ensure_local", fake_ensure)
    monkeypatch.setattr(ai_router, "_local_provider", fake_local)
    monkeypatch.setattr(ai_router, "_gemini_provider", boom)


@pytest.mark.asyncio
async def test_local_only_never_contacts_cloud(db, local_only):
    update_settings(
        db,
        {
            "ai_mode": "local_only",
            "cloud_consent": True,
            "gemini_api_key": "would-be-used",
        },
    )
    result = await ai_router.generate(db, task="test", system="s", prompt="p")
    assert result.provider == "local"
    assert result.text == "local answer"


@pytest.mark.asyncio
async def test_explicit_gemini_mode_does_not_fall_back_to_local(db, monkeypatch):
    update_settings(db, {"ai_mode": "gemini", "cloud_consent": True, "gemini_api_key": "k"})

    def boom(db):
        raise ProviderUnavailable("no network", provider="gemini")

    monkeypatch.setattr(ai_router, "_gemini_provider", boom)
    monkeypatch.setattr(
        ai_router,
        "_local_provider",
        lambda db: (_ for _ in ()).throw(AssertionError("local must not be used")),
    )
    with pytest.raises(AIError):
        await ai_router.generate(db, task="test", system="s", prompt="p")


@pytest.mark.asyncio
async def test_cloud_consent_is_required(db, monkeypatch):
    update_settings(db, {"ai_mode": "gemini", "cloud_consent": False, "gemini_api_key": "k"})
    monkeypatch.setattr(
        ai_router,
        "_local_provider",
        lambda db: (_ for _ in ()).throw(AssertionError("local must not be used")),
    )
    with pytest.raises(AIError) as excinfo:
        await ai_router.generate(db, task="test", system="s", prompt="p")
    assert "consent" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_auto_mode_falls_back_and_records_it(db, monkeypatch):
    update_settings(
        db,
        {
            "ai_mode": "auto",
            "preferred_provider": "gemini",
            "allow_auto_fallback": True,
            "cloud_consent": True,
            "gemini_api_key": "k",
        },
    )

    def gemini_down(db):
        raise ProviderUnavailable("quota exhausted", provider="gemini")

    async def fake_ensure(db, *, vision=False):
        return None

    monkeypatch.setattr(ai_router, "_gemini_provider", gemini_down)
    monkeypatch.setattr(ai_router, "_ensure_local", fake_ensure)
    monkeypatch.setattr(ai_router, "_local_provider", lambda db: FakeLocal())

    result = await ai_router.generate(db, task="test", system="s", prompt="p")
    assert result.provider == "local"
    assert result.fallback_from is not None
    assert any(attempt["provider"] == "gemini" for attempt in result.attempts)


@pytest.mark.asyncio
async def test_auto_mode_without_fallback_permission_stops(db, monkeypatch):
    update_settings(
        db,
        {
            "ai_mode": "auto",
            "preferred_provider": "gemini",
            "allow_auto_fallback": False,
            "cloud_consent": True,
            "gemini_api_key": "k",
        },
    )

    def gemini_down(db):
        raise ProviderUnavailable("quota exhausted", provider="gemini")

    monkeypatch.setattr(ai_router, "_gemini_provider", gemini_down)
    monkeypatch.setattr(
        ai_router,
        "_ensure_local",
        lambda db, vision=False: (_ for _ in ()).throw(AssertionError("local must not be used")),
    )
    with pytest.raises(AIError):
        await ai_router.generate(db, task="test", system="s", prompt="p")


def test_provider_order_by_mode(db):
    update_settings(db, {"ai_mode": "local_only"})
    order, _ = ai_router._providers(db)
    assert order == ["local"]

    update_settings(db, {"ai_mode": "gemini"})
    order, _ = ai_router._providers(db)
    assert order == ["gemini"]

    update_settings(
        db, {"ai_mode": "auto", "preferred_provider": "local", "allow_auto_fallback": True}
    )
    order, _ = ai_router._providers(db)
    assert order == ["local", "gemini"]
