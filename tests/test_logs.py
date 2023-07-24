import pytest

from keycmd.logs import set_verbose, log, vlog, error, vwarn


def test_logging(capsys):
    vlog("foo")
    vwarn("foo")
    log("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"

    set_verbose()
    vlog("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"
    vwarn("foo")
    assert capsys.readouterr().out == "keycmd: warning: foo\n"
    log("foo")
    assert capsys.readouterr().out == "keycmd: foo\n"

    with pytest.raises(SystemExit) as exc_info:
        error("foo")
    assert exc_info.value.args[0] == 1
    assert capsys.readouterr().out == "keycmd: error: foo\n"
