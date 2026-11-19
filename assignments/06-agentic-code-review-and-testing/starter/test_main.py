import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_create_habit_valid():
    r = client.post("/habits", json={"name": "Meditate"})
    assert r.status_code == 200
    assert r.json()["name"] == "Meditate"


@pytest.mark.parametrize("invalid_name", ["", "   ", "\t", "\n", " \t \n "])
def test_create_habit_empty_or_whitespace_rejected(invalid_name):
    r = client.post("/habits", json={"name": invalid_name})
    assert r.status_code == 422
    assert "Habit name cannot be empty or whitespace-only" in r.text


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "malformed_day",
    [
        "not-a-date",
        "2026/09/22",
        "2026-9-22",
        "22-09-2026",
        "2026-09-22T00:00:00",
        "",
        "   ",
        "abcd-ef-gh",
    ],
)
def test_checkin_malformed_date_rejected(malformed_day):
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": malformed_day})
    assert r.status_code == 422
    assert "Day must be a valid calendar date in YYYY-MM-DD format" in r.text


@pytest.mark.parametrize(
    "impossible_day",
    [
        "2026-02-30",
        "2026-02-29",
        "2026-04-31",
        "2026-13-01",
        "2026-00-10",
        "2026-01-32",
        "2026-01-00",
    ],
)
def test_checkin_impossible_calendar_date_rejected(impossible_day):
    hid = client.post("/habits", json={"name": "Walk"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": impossible_day})
    assert r.status_code == 422
    assert "Day must be a valid calendar date in YYYY-MM-DD format" in r.text


def test_checkin_valid_leap_day():
    hid = client.post("/habits", json={"name": "Leap Day Run"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2024-02-29"})
    assert r.status_code == 200
    assert r.json()["day"] == "2024-02-29"
