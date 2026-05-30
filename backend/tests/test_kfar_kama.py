import pytest

from src.services.telegram_notifier import TelegramNotifier
from src.utils.kfar_kama import (
    collect_active_track_ids,
    event_affects_kfar_kama,
    event_track_ids,
    is_kfar_kama_city,
)


def test_is_kfar_kama_hebrew():
    assert is_kfar_kama_city({"name": "כפר כמא", "city_id": 1235})


def test_is_kfar_kama_english():
    assert is_kfar_kama_city({"name": "Kfar Kama"})


def test_is_kfar_kama_by_city_id_only():
    assert is_kfar_kama_city({"city_id": 1235, "coords": [32.72, 35.44]})


def test_is_not_kfar_kana():
    assert not is_kfar_kama_city({"name": "Kfar Kana", "city_id": 1255})


def test_event_affects_kfar_kama():
    event = {
        "id": "test-1",
        "all_cities": [{"name": "תל אביב - יפו", "coords": [32.08, 34.78]}],
        "clusters": [{"cities": [{"name": "כפר כמא", "coords": [32.72, 35.44]}]}],
    }
    assert event_affects_kfar_kama(event)


def test_event_affects_kfar_kama_via_trajectory_target():
    event = {
        "all_cities": [],
        "clusters": [],
        "trajectories": [{"target_coords": [32.71999, 35.44193]}],
    }
    assert event_affects_kfar_kama(event)


def test_event_no_kfar_kama():
    event = {
        "all_cities": [{"name": "חיפה", "coords": [32.79, 34.99]}],
        "clusters": [],
    }
    assert not event_affects_kfar_kama(event)


def test_nearby_city_coords_without_name_not_kfar_kama():
    event = {
        "all_cities": [{"name": "Nearby town", "coords": [32.71999, 35.44193]}],
        "clusters": [],
    }
    assert not event_affects_kfar_kama(event)


def test_notify_key_stable_on_city_expansion():
    notifier = TelegramNotifier()
    base = {"id": "a1", "category": "missiles", "all_cities": [{"name": "כפר כמא"}]}
    expanded = {
        "id": "a1",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}, {"name": "חיפה"}],
    }
    assert notifier._notify_key(base) == notifier._notify_key(expanded)


def test_event_track_ids_includes_merged_siblings():
    event = {"id": "master", "merged_ids": ["sim-a", "sim-b"]}
    assert event_track_ids(event) == {"master", "sim-a", "sim-b"}
    assert event_track_ids(event, "sim-a") == {"master", "sim-a", "sim-b"}


def test_collect_active_track_ids_includes_live_raw_ids():
    events_list = [{"id": "master", "merged_ids": ["child"]}]
    active_events = {
        "master": {"end_time": None},
        "ghost-nf": {"end_time": None},
        "ended": {"end_time": 1.0},
    }
    ids = collect_active_track_ids(events_list, active_events)
    assert ids == {"master", "child", "ghost-nf"}
    assert "ended" not in ids


async def _noop_async(*_a, **_k):
    return None


async def _success_async(*_a, **_k):
    return True


@pytest.mark.asyncio
async def test_skips_simulation_active():
    notifier = TelegramNotifier()
    notifier._enabled = True
    notifier._send_kfar_kama_alert = _noop_async

    await notifier.notify_events_if_kfar_kama([{
        "id": "sim-1",
        "is_simulation": True,
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }])
    assert "sim-1" not in notifier._started_alert_ids
    assert "sim-1" not in notifier._last_notify_key


@pytest.mark.asyncio
async def test_termination_only_after_start():
    notifier = TelegramNotifier()
    notifier._enabled = True
    notifier._send_kfar_kama_alert = _noop_async
    notifier._send_message = _noop_async
    notifier._send_photo = _noop_async

    event = {
        "id": "sim-test",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא", "coords": [32.72, 35.44]}],
    }
    await notifier.notify_kfar_kama_terminated(event, "sim-test")
    assert "sim-test" not in notifier._terminated_alert_ids

    notifier._started_alert_ids.add("sim-test")
    await notifier.notify_kfar_kama_terminated(event, "sim-test")
    assert "sim-test" in notifier._terminated_alert_ids


@pytest.mark.asyncio
async def test_termination_matches_merged_sibling_id():
    notifier = TelegramNotifier()
    notifier._enabled = True
    notifier._send_kfar_kama_alert = _noop_async
    notifier._send_message = _noop_async

    event = {
        "id": "master",
        "merged_ids": ["sim-child"],
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    notifier._started_alert_ids.add("master")
    notifier._started_alert_ids.add("sim-child")

    await notifier.notify_kfar_kama_terminated(event, "sim-child")
    assert "sim-child" in notifier._terminated_alert_ids
    assert "master" in notifier._terminated_alert_ids


@pytest.mark.asyncio
async def test_map_capture_fail_does_not_mark_started():
    notifier = TelegramNotifier()
    notifier._enabled = True

    async def fail_capture(*_a, **_k):
        return False

    notifier._send_kfar_kama_alert = fail_capture
    event = {
        "id": "cap-fail",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    await notifier.notify_events_if_kfar_kama([event])
    assert "cap-fail" not in notifier._started_alert_ids
    assert "cap-fail" not in notifier._last_notify_key


@pytest.mark.asyncio
async def test_successful_start_marks_started():
    notifier = TelegramNotifier()
    notifier._enabled = True
    notifier._send_kfar_kama_alert = _success_async
    event = {
        "id": "cap-ok",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    await notifier.notify_events_if_kfar_kama([event])
    assert "cap-ok" in notifier._started_alert_ids


@pytest.mark.asyncio
async def test_concurrent_notify_serializes_dedup():
    import asyncio

    notifier = TelegramNotifier()
    notifier._enabled = True
    calls = []

    async def slow_success(*_a, **_k):
        calls.append(1)
        await asyncio.sleep(0.05)
        return True

    notifier._send_kfar_kama_alert = slow_success
    event = {
        "id": "burst",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    await asyncio.gather(
        notifier._notify_events_safe([event]),
        notifier._notify_events_safe([event]),
    )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_close_cancels_pending_and_closes_session():
    import asyncio

    notifier = TelegramNotifier()
    notifier._enabled = True
    started = asyncio.Event()

    async def block_forever(*_a, **_k):
        started.set()
        await asyncio.sleep(3600)
        return True

    notifier._send_kfar_kama_alert = block_forever
    event = {
        "id": "pending",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    notifier.schedule_notify_events_if_kfar_kama([event])
    await asyncio.wait_for(started.wait(), timeout=2)
    await notifier.close()
    assert not notifier._pending_tasks
    assert notifier._session is None
    assert notifier._tile_session is None


@pytest.mark.asyncio
async def test_stale_scheduled_active_skipped_after_end():
    notifier = TelegramNotifier()
    notifier._enabled = True
    sends = []

    async def track_send(_event, *, started):
        sends.append(started)
        return True

    notifier._send_kfar_kama_alert = track_send
    event = {
        "id": "stale-1",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    notifier._terminated_alert_ids.add("stale-1")
    await notifier._notify_events_safe([event])
    assert sends == []


@pytest.mark.asyncio
async def test_active_skipped_if_end_during_map_capture():
    import asyncio

    notifier = TelegramNotifier()
    notifier._enabled = True
    sends = []

    async def slow_start(_event, *, started):
        if started:
            notifier._terminated_alert_ids.add("race-1")
            await asyncio.sleep(0.02)
            return True
        sends.append(started)
        return False

    notifier._send_kfar_kama_alert = slow_start
    event = {
        "id": "race-1",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    await notifier.notify_events_if_kfar_kama([event])
    assert "race-1" not in notifier._started_alert_ids
    assert "race-1" not in notifier._last_notify_key


@pytest.mark.asyncio
async def test_concurrent_end_single_send():
    import asyncio

    notifier = TelegramNotifier()
    notifier._enabled = True
    end_calls = []

    async def track_end(_event, *, started):
        if not started:
            end_calls.append(1)
            await asyncio.sleep(0.02)
        return False

    notifier._send_kfar_kama_alert = track_end
    event = {
        "id": "end-once",
        "category": "missiles",
        "all_cities": [{"name": "כפר כמא"}],
    }
    notifier._started_alert_ids.add("end-once")
    await asyncio.gather(
        notifier.notify_kfar_kama_terminated(event, "end-once"),
        notifier.notify_kfar_kama_terminated(event, "end-once"),
    )
    assert len(end_calls) == 1


@pytest.mark.asyncio
async def test_supersede_pattern_fires_end_when_started():
    """Contract: main newsFlash supersede must call notify_kfar_kama_terminated when started."""
    notifier = TelegramNotifier()
    notifier._enabled = True
    ended = []

    async def track_end(_event, *, started):
        if not started:
            ended.append(1)
        return False

    notifier._send_kfar_kama_alert = track_end
    nf_event = {
        "id": "nf-ghost",
        "category": "newsFlash",
        "all_cities": [{"name": "כפר כמא"}],
    }
    notifier._started_alert_ids.add("nf-ghost")
    await notifier.notify_kfar_kama_terminated(nf_event, "nf-ghost")
    assert len(ended) == 1
