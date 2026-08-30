from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.bot.jobs.daily_ayah import (
    _daily_ayah_job_name,
    _parse_daily_time,
    _resolve_timezone,
    remove_daily_ayah_job,
    schedule_user_daily_ayah,
)


def make_chat(
    *,
    chat_id: int = 12345,
    daily_time: str = "03:15",
    timezone: str | None = "Asia/Riyadh",
    daily_ayah: bool = True,
):
    return SimpleNamespace(
        chat_id=chat_id,
        daily_time=daily_time,
        timezone=timezone,
        daily_ayah=daily_ayah,
    )


def test_daily_ayah_job_name():
    assert _daily_ayah_job_name(12345) == "daily_ayah_12345"


def test_parse_daily_time_default():
    parsed = _parse_daily_time(make_chat(daily_time="03:15"))
    assert parsed is not None
    assert parsed.hour == 3
    assert parsed.minute == 15


def test_parse_daily_time_custom():
    parsed = _parse_daily_time(make_chat(daily_time="10:30"))
    assert parsed is not None
    assert parsed.hour == 10
    assert parsed.minute == 30


def test_parse_daily_time_invalid_returns_none():
    assert _parse_daily_time(make_chat(daily_time="not-a-time")) is None


def test_resolve_timezone_uses_default_when_none():
    tz = _resolve_timezone(make_chat(timezone=None))
    assert tz.key == "Asia/Riyadh"


def test_resolve_timezone_invalid_falls_back_to_utc():
    tz = _resolve_timezone(make_chat(timezone="Not/A_Zone"))
    assert tz.key == "UTC"


def test_schedule_user_daily_ayah_schedules_with_local_tz_time():
    scheduled = {}

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            return []

        def run_daily(self, callback, time, days, name, data):
            scheduled["name"] = name
            scheduled["time"] = time
            scheduled["days"] = days
            scheduled["data"] = data
            scheduled["callback"] = callback

    class FakeApplication:
        job_queue = FakeJobQueue()

    chat = make_chat(daily_time="03:15", timezone="Asia/Riyadh")
    schedule_user_daily_ayah(FakeApplication(), chat)

    assert scheduled["name"] == "daily_ayah_12345"
    assert scheduled["time"].hour == 3
    assert scheduled["time"].minute == 15
    assert scheduled["time"].tzinfo == ZoneInfo("Asia/Riyadh")
    assert scheduled["data"] == {"chat_id": 12345}


def test_schedule_user_daily_ayah_disabled_removes_job():
    class FakeJob:
        def __init__(self):
            self.removed = False

        def schedule_removal(self):
            self.removed = True

    jobs = [FakeJob()]

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            return jobs

        def run_daily(self, *args, **kwargs):
            raise AssertionError("should not schedule when disabled")

    class FakeApplication:
        job_queue = FakeJobQueue()

    schedule_user_daily_ayah(FakeApplication(), make_chat(daily_ayah=False))
    assert jobs[0].removed is True


def test_remove_daily_ayah_job_removes_all():
    removed = []

    class FakeJob:
        def schedule_removal(self):
            removed.append(True)

    class FakeJobQueue:
        def get_jobs_by_name(self, name):
            assert name == "daily_ayah_12345"
            return [FakeJob(), FakeJob()]

    class FakeApplication:
        job_queue = FakeJobQueue()

    remove_daily_ayah_job(FakeApplication(), 12345)
    assert removed == [True, True]
