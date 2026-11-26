"""textext-improved: tests for centring the dialog on Inkscape's window (macos_front.centered_position)."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "macos_front", os.path.join(os.path.dirname(__file__), "..", "textext", "macos_front.py"))
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)


def test_centred_on_target():
    assert mf.centered_position((1800, 30, 3200, 1770), (500, 525), (1800, 30, 3200, 1770)) == (2150 + 1200 - 200, 652)


def test_clamped_to_monitor_work_area():
    # target hanging off the left edge of the monitor: dialog stays fully on it
    assert mf.centered_position((-50, 0, 400, 400), (500, 525), (0, 30, 1800, 3170)) == (0, 30)


def test_clamped_on_the_right_and_bottom():
    assert mf.centered_position((1700, 3100, 400, 400), (500, 525), (0, 30, 1800, 3170)) == (1300, 2675)


def test_lookup_returns_none_for_missing_app():
    assert mf.find_window_bounds(pids=(), owner_substring="no-such-app-xyz") is None
