from functools import partial

import pytest

from keycmd.logs import error, log, set_verbose, vlog, vwarn


def test_logging(capsys, request):
    vlog("foo")
    vwarn("foo")
    log("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"

    set_verbose()
    request.addfinalizer(partial(set_verbose, False))

    vlog("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"
    vwarn("foo")
    assert capsys.readouterr().out == "keycmd: warning: foo\n"
    log("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"

    with pytest.raises(SystemExit) as exc_info:
        error("foo")
    assert exc_info.value.args[0] == 1
    assert capsys.readouterr().err == "keycmd: error: foo\n"

    set_verbose(False)

    vlog("foo")
    assert capsys.readouterr().out == ""


def test_error_hints(capsys):
    """What went wrong is rarely the same line as what to do about it"""
    with pytest.raises(SystemExit) as exc_info:
        error("no", "try this", "or this")
    assert exc_info.value.args[0] == 1
    assert capsys.readouterr().err == (
        "keycmd: error: no\nkeycmd: hint: try this\nkeycmd: hint: or this\n"
    )
