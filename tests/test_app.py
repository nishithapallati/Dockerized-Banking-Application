import sys
import os

# Add the backend folder to Python's module search path
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

from app import app


def test_home_page():
    app.config["TESTING"] = True

    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200


def test_login_page():
    app.config["TESTING"] = True

    client = app.test_client()

    response = client.get("/login")

    assert response.status_code == 200


def test_register_page():
    app.config["TESTING"] = True

    client = app.test_client()

    response = client.get("/register")

    assert response.status_code == 200


def test_dashboard_requires_login():
    app.config["TESTING"] = True

    client = app.test_client()

    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_logout():
    app.config["TESTING"] = True

    client = app.test_client()

    response = client.get("/logout")

    assert response.status_code == 302
    assert "/login" in response.location