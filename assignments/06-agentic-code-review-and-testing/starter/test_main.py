from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_habits.db"
    monkeypatch.setattr(main, "DB_PATH", test_db)
    main.init_db()


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


def test_streak_active_multiday():
    hid = client.post("/habits", json={"name": "Exercise"}).json()["id"]
    today = date.today()
    for offset in (2, 1, 0):
        day = (today - timedelta(days=offset)).isoformat()
        r = client.post(f"/habits/{hid}/checkin", json={"day": day})
        assert r.status_code == 200

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_broken():
    hid = client.post("/habits", json={"name": "Meditation"}).json()["id"]
    today = date.today()
    for offset in (2, 1):
        day = (today - timedelta(days=offset)).isoformat()
        r = client.post(f"/habits/{hid}/checkin", json={"day": day})
        assert r.status_code == 200

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 0}


def test_streak_no_checkins():
    hid = client.post("/habits", json={"name": "Journaling"}).json()["id"]
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 0}


def test_streak_unknown_habit_404():
    r = client.get("/habits/99999/streak")
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown habit"


def test_streak_gap_before_active():
    hid = client.post("/habits", json={"name": "Coding"}).json()["id"]
    today = date.today()
    for offset in (4, 1, 0):
        day = (today - timedelta(days=offset)).isoformat()
        r = client.post(f"/habits/{hid}/checkin", json={"day": day})
        assert r.status_code == 200

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 2}


def test_streak_duplicate_checkins_same_day():
    hid = client.post("/habits", json={"name": "Running"}).json()["id"]
    today = date.today()
    for offset in (1, 0):
        day = (today - timedelta(days=offset)).isoformat()
        r1 = client.post(f"/habits/{hid}/checkin", json={"day": day})
        assert r1.status_code == 200
        r2 = client.post(f"/habits/{hid}/checkin", json={"day": day})
        assert r2.status_code == 200

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 2}


def test_streak_future_checkin_ignored():
    hid = client.post("/habits", json={"name": "Writing"}).json()["id"]
    today = date.today()
    future_day = (today + timedelta(days=1)).isoformat()
    today_day = today.isoformat()

    r1 = client.post(f"/habits/{hid}/checkin", json={"day": future_day})
    assert r1.status_code == 200

    r_future_only = client.get(f"/habits/{hid}/streak")
    assert r_future_only.status_code == 200
    assert r_future_only.json() == {"habit_id": hid, "streak": 0}

    r2 = client.post(f"/habits/{hid}/checkin", json={"day": today_day})
    assert r2.status_code == 200

    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 1}
