from functools import partial

import pytest

from keycmd.logs import set_verbose, log, vlog, error, vwarn


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
