"""Tests for the EventBus pub/sub system."""

import pytest

from src.core.events import EventBus


@pytest.fixture(autouse=True)
def clean_event_bus():
    """Reset EventBus state before each test."""
    EventBus.reset()
    yield
    EventBus.reset()


def test_publish_stores_event_in_history():
    EventBus.publish("test.event", {"key": "value"})
    history = EventBus.get_history()
    assert len(history) == 1
    assert history[0].type == "test.event"
    assert history[0].payload == {"key": "value"}


def test_subscribe_receives_published_event():
    received = []
    EventBus.subscribe("my.event", lambda e: received.append(e))

    EventBus.publish("my.event", {"data": 42})

    assert len(received) == 1
    assert received[0].type == "my.event"
    assert received[0].payload["data"] == 42


def test_subscribe_does_not_receive_other_events():
    received = []
    EventBus.subscribe("a.event", lambda e: received.append(e))
    EventBus.publish("b.event", {"data": 1})

    assert len(received) == 0


def test_wildcard_subscriber_receives_all_events():
    received = []
    EventBus.subscribe("*", lambda e: received.append(e))

    EventBus.publish("first.event")
    EventBus.publish("second.event")

    assert len(received) == 2
    assert received[0].type == "first.event"
    assert received[1].type == "second.event"


def test_multiple_subscribers_for_same_event():
    results_a = []
    results_b = []
    EventBus.subscribe("shared", lambda e: results_a.append(e))
    EventBus.subscribe("shared", lambda e: results_b.append(e))

    EventBus.publish("shared", {"x": 1})

    assert len(results_a) == 1
    assert len(results_b) == 1


def test_clear_history():
    EventBus.publish("event1")
    EventBus.publish("event2")
    assert len(EventBus.get_history()) == 2

    EventBus.clear_history()
    assert len(EventBus.get_history()) == 0


def test_get_history_returns_copy():
    EventBus.publish("event")
    history = EventBus.get_history()
    history.clear()  # mutate the copy
    assert len(EventBus.get_history()) == 1  # original untouched


def test_publish_default_empty_payload():
    EventBus.publish("no_payload")
    history = EventBus.get_history()
    assert history[0].payload == {}


def test_event_has_timestamp():
    EventBus.publish("timestamped")
    event = EventBus.get_history()[0]
    assert event.timestamp is not None


def test_subscriber_exception_does_not_break_dispatch():
    received = []

    def bad_handler(e):
        raise RuntimeError("boom")

    def good_handler(e):
        received.append(e)

    EventBus.subscribe("err.event", bad_handler)
    EventBus.subscribe("err.event", good_handler)

    EventBus.publish("err.event")
    assert len(received) == 1


def test_reset_clears_subscribers_and_history():
    EventBus.subscribe("x", lambda e: None)
    EventBus.publish("x")
    assert len(EventBus.get_history()) == 1

    EventBus.reset()
    assert len(EventBus.get_history()) == 0
    # publishing after reset should still work (no subscribers to crash)
    EventBus.publish("x")
    assert len(EventBus.get_history()) == 1
