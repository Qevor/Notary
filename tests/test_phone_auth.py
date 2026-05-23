from fastapi.testclient import TestClient
from apps.api.main import app
import pytest
from unittest.mock import AsyncMock, patch

client = TestClient(app)

def test_login_page_renders():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Phone Number" in response.text
    assert "Email or Handle" in response.text

@patch("apps.api.main.get_app_service")
def test_send_phone_code(mock_get_service):
    with patch("apps.api.main.get_settings") as mock_settings:
        mock_settings.return_value.notary_session_secret = "6802f26f58a0a03258a7df394cdd7e94838562de25f34d7027d14717e7c02e21"
        response = client.post("/auth/send-phone-code", data={"phone": "+1234567890"}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/app"
        assert "notary_session" in response.cookies

def test_verify_phone_code():
    response = client.post(
        "/auth/verify-phone-code",
        data={"phone": "+1234567890", "token": "123456"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/app"

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
