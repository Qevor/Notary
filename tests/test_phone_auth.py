from fastapi.testclient import TestClient
from apps.api.main import app
import pytest
from unittest.mock import AsyncMock, patch

client = TestClient(app)

def test_login_page_renders():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign In" in response.text
    assert "Register" in response.text
    assert "Password" in response.text


def test_public_route_metadata_is_available():
    assert client.head("/").status_code == 200
    assert client.get("/robots.txt").text == "User-agent: *\nAllow: /\n"
    assert client.get("/favicon.ico").status_code == 204


def test_profile_shortcut_redirects_anonymous_users_to_login():
    client.cookies.clear()
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/notaries", {}),
        ("/circle/login/init", {}),
        ("/commerce/x402/data", {"description": "test", "service_url": "https://example.com"}),
        ("/treasury/yield/process", {}),
        ("/markets/arbitrage/analyze", {"venues": []}),
    ],
)
def test_operator_routes_require_sign_in(path, payload):
    client.cookies.clear()
    response = client.post(path, data=payload if path != "/markets/arbitrage/analyze" else None, json=payload if path == "/markets/arbitrage/analyze" else None)
    assert response.status_code == 401


@patch("apps.api.main.get_app_service")
def test_register_user_success(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.register_user = AsyncMock(return_value={
        "username": "testuser",
        "wallet": "0x123",
        "circle_wallet_id": "circle_123"
    })
    
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        response = client.post(
            "/auth/register",
            data={"username": "testuser", "password": "password123", "confirm_password": "password123"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert "/app" in response.headers["location"]
        assert "notary_session" in response.cookies
        mock_service.register_user.assert_called_once_with("testuser", "password123")

def test_register_password_mismatch():
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "password123", "confirm_password": "mismatchpassword"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "/login" in response.headers["location"]
    assert "Passwords%20do%20not%20match" in response.headers["location"]

@patch("apps.api.main.get_app_service")
def test_login_user_success(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.authenticate_user = AsyncMock(return_value={
        "username": "testuser",
        "wallet": "0x123"
    })
    
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/app"
        assert "notary_session" in response.cookies
        mock_service.authenticate_user.assert_called_once_with("testuser", "password123")

@patch("apps.api.main.get_app_service")
def test_login_incorrect_password(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.authenticate_user = AsyncMock(side_effect=ValueError("Incorrect password. Please try again."))
    
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert "/login" in response.headers["location"]
        assert "Incorrect%20password" in response.headers["location"]

def test_dev_login_sandbox_phone():
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_env = "development"
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        response = client.post(
            "/auth/dev-login",
            data={"phone": "+1234567890"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/app"
        assert "notary_session" in response.cookies

@patch("apps.api.main.get_app_service")
def test_update_username_success(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.change_username = AsyncMock(return_value={
        "username": "newtestuser",
        "wallet": "0x123",
        "circle_wallet_id": "circle_123",
        "username_changed": True
    })
    
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        from apps.api.main import _sign_session
        session_cookie = _sign_session({
            "user": {"id": "testuser", "email": "testuser@notary.local", "role": "user"},
            "expiresAt": 9999999999
        })
        client.cookies.set("notary_session", session_cookie)
        
        response = client.post(
            "/ui/profile/update-username",
            data={"new_username": "newtestuser"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert "/profile" in response.headers["location"]
        assert "message=Username%20changed" in response.headers["location"]
        assert "notary_session" in response.cookies
        mock_service.change_username.assert_called_once_with("testuser", "newtestuser")

def test_update_username_unauthorized():
    client.cookies.clear()
    response = client.post(
        "/ui/profile/update-username",
        data={"new_username": "newtestuser"},
        follow_redirects=False
    )
    assert response.status_code == 401

@patch("apps.api.main.get_app_service")
def test_update_username_already_changed(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.change_username = AsyncMock(side_effect=ValueError("You can only change your username once."))
    
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        from apps.api.main import _sign_session
        session_cookie = _sign_session({
            "user": {"id": "testuser", "email": "testuser@notary.local", "role": "user"},
            "expiresAt": 9999999999
        })
        client.cookies.set("notary_session", session_cookie)
        
        response = client.post(
            "/ui/profile/update-username",
            data={"new_username": "anothernewuser"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert "/profile" in response.headers["location"]
        assert "error=You%20can%20only%20change" in response.headers["location"]

@pytest.mark.anyio
async def test_app_service_change_username_logic(tmp_path):
    from notary.config import Settings
    from notary.app_service import NotaryAppService
    
    settings = Settings(notary_db_path=tmp_path / "notary_test.sqlite3", notary_demo_mode=True)
    service = NotaryAppService(settings)
    
    # 1. Register a test user
    user = await service.register_user("testuser", "password123")
    assert user["username"] == "testuser"
    assert not user.get("username_changed")
    
    # 2. Change username successfully
    updated = await service.change_username("testuser", "newtestuser")
    assert updated["username"] == "newtestuser"
    assert updated["username_changed"] is True
    
    # Check old user is removed and new user exists
    assert service.store.get("profiles", "testuser") is None
    new_profile = service.store.get("profiles", "newtestuser")
    assert new_profile is not None
    assert new_profile["username"] == "newtestuser"
    assert new_profile["username_changed"] is True
    
    # 3. Changing again should fail (only once)
    with pytest.raises(ValueError, match="You can only change your username once"):
        await service.change_username("newtestuser", "anotheruser")
        
    # 4. Try changing to an already taken username
    await service.register_user("takenuser", "password123")
    await service.register_user("changeable", "password123")
    with pytest.raises(ValueError, match="is already taken"):
        await service.change_username("changeable", "takenuser")

@pytest.mark.anyio
async def test_get_user_transactions_logic(tmp_path):
    from notary.config import Settings
    from notary.app_service import NotaryAppService
    
    settings = Settings(notary_db_path=tmp_path / "notary_test_tx.sqlite3", notary_demo_mode=True)
    service = NotaryAppService(settings)
    
    await service.register_user("alice", "password123")
    await service.register_user("bob", "password123")
    
    txs = service.get_user_transactions("alice")
    assert len(txs) == 0
    
    import time
    tx_record = {
        "tx_id": "tx_001",
        "type": "direct_transfer",
        "sender": "alice",
        "recipient": "bob",
        "amount_usdc": 100.0,
        "status": "completed",
        "timestamp": int(time.time()),
    }
    service.store.put("transfers", "tx_001", tx_record)
    
    alice_txs = service.get_user_transactions("alice")
    assert len(alice_txs) == 1
    assert alice_txs[0]["tx_id"] == "tx_001"
    assert alice_txs[0]["direction"] == "send"
    assert alice_txs[0]["amount_usdc"] == 100.0
    
    bob_txs = service.get_user_transactions("bob")
    assert len(bob_txs) == 1
    assert bob_txs[0]["tx_id"] == "tx_001"
    assert bob_txs[0]["direction"] == "receive"
    assert bob_txs[0]["amount_usdc"] == 100.0

@patch("apps.api.main.get_app_service")
def test_profile_endpoint_success(mock_get_service):
    from unittest.mock import Mock
    mock_service = mock_get_service.return_value
    mock_service.store.get.return_value = {
        "username": "profileuser",
        "wallet": "0x456"
    }
    mock_service.get_or_create_user_profile = AsyncMock(return_value={
        "username": "profileuser",
        "wallet": "0x456",
        "balance": "150.00"
    })
    mock_service.get_user_transactions = Mock(return_value=[
        {
            "tx_id": "tx_abc",
            "type": "direct_transfer",
            "direction": "receive",
            "party": "@senderuser",
            "amount_usdc": 50.0,
            "status": "completed",
            "description": "Direct transfer from @senderuser",
            "timestamp": 123456789
        }
    ])
    
    response = client.get("/p/profileuser")
    assert response.status_code == 200
    assert "profileuser" in response.text
    assert "150.00 USDC" in response.text
    assert "Direct transfer from @senderuser" in response.text
    assert "50.0 USDC" in response.text

@patch("apps.api.main.get_app_service")
def test_profile_endpoint_404(mock_get_service):
    mock_service = mock_get_service.return_value
    mock_service.store.get.return_value = None
    
    response = client.get("/p/nonexistent")
    assert response.status_code == 404
    assert "User profile not found" in response.text

@pytest.mark.anyio
async def test_login_by_email_after_username_change(tmp_path):
    from notary.config import Settings
    from notary.app_service import NotaryAppService
    
    settings = Settings(notary_db_path=tmp_path / "notary_test_email.sqlite3", notary_demo_mode=True)
    service = NotaryAppService(settings)
    
    user = await service.register_user("mebstel@gmail.com", "password123")
    assert user["username"] == "mebstel"
    assert user["email"] == "mebstel@gmail.com"
    
    updated = await service.change_username("mebstel", "maris")
    assert updated["username"] == "maris"
    assert updated["email"] == "mebstel@gmail.com"
    
    assert service.store.get("profiles", "mebstel") is None
    assert service.store.get("profiles", "maris") is not None
    
    auth = await service.authenticate_user("mebstel@gmail.com", "password123")
    assert auth["username"] == "maris"
    assert auth["email"] == "mebstel@gmail.com"
    
    auth2 = await service.authenticate_user("maris", "password123")
    assert auth2["username"] == "maris"

@pytest.mark.anyio
async def test_login_by_email_after_username_change_migrated_compatibility(tmp_path):
    from notary.config import Settings
    from notary.app_service import NotaryAppService
    
    settings = Settings(notary_db_path=tmp_path / "notary_test_compat.sqlite3")
    service = NotaryAppService(settings)
    
    import hashlib
    import os
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', "password123".encode('utf-8'), salt, 100000)
    
    legacy_profile = {
        "username": "maris",
        "wallet": "0x123",
        "password_hash": key.hex(),
        "salt": salt.hex(),
    }
    service.store.put("profiles", "maris", legacy_profile)
    
    p = service.store.get("profiles", "maris")
    assert "email" not in p
    
    auth = await service.authenticate_user("mebstel@gmail.com", "password123")
    assert auth["username"] == "maris"
    assert auth["email"] == "mebstel@gmail.com"
    
    p_updated = service.store.get("profiles", "maris")
    assert p_updated["email"] == "mebstel@gmail.com"


@pytest.mark.anyio
async def test_live_registration_requires_circle_wallet(tmp_path):
    from notary.config import Settings
    from notary.app_service import NotaryAppService

    settings = Settings(notary_db_path=tmp_path / "notary_test_live_wallet.sqlite3", notary_demo_mode=False)
    service = NotaryAppService(settings)

    class FailingCircle:
        async def create_agent_wallet(self, owner_hint):
            raise RuntimeError("Circle CLI unavailable")

    service.circle = FailingCircle()

    with pytest.raises(RuntimeError, match="Circle agent wallet provisioning is required"):
        await service.register_user("liveuser", "password123")


@pytest.mark.anyio
async def test_live_registration_uses_circle_wallets_api_when_configured(tmp_path, monkeypatch):
    from notary.config import Settings
    from notary.app_service import NotaryAppService
    from notary.services.circle_wallets_api import CircleDeveloperWalletClient

    settings = Settings(
        notary_db_path=tmp_path / "notary_wallets_api.sqlite3",
        notary_demo_mode=False,
        circle_api_key="TEST_API_KEY:abc:def",
        circle_entity_secret="1" * 64,
        circle_wallet_set_id="wallet-set-1",
    )
    service = NotaryAppService(settings)
    called = {"wallets_api": False, "cli": False}

    def fake_create_user_wallet(self, username):
        called["wallets_api"] = True
        return {
            "walletId": "circle-user-wallet-1",
            "address": "0x" + "7" * 40,
            "walletSetId": self.wallet_set_id,
            "provider": "circle_developer_wallets",
            "demo": False,
        }

    class FailingIfCalledCircle:
        async def create_agent_wallet(self, owner_hint):
            called["cli"] = True
            raise RuntimeError("CLI should not be used when Wallets API is configured")

    monkeypatch.setattr(CircleDeveloperWalletClient, "create_user_wallet", fake_create_user_wallet)
    service.circle = FailingIfCalledCircle()

    profile = await service.register_user("walletapi@example.com", "secure-pass")

    assert called["wallets_api"] is True
    assert called["cli"] is False
    assert profile["wallet"] == "0x" + "7" * 40
    assert profile["circle_wallet_id"] == "circle-user-wallet-1"

