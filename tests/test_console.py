from youtrack_cli.console import _reconfigure_stream

class MockStream:
    def __init__(self):
        self.reconfigured_kwargs = None

    def reconfigure(self, **kwargs):
        self.reconfigured_kwargs = kwargs

def test_reconfigure_stream_calls_reconfigure_with_correct_args():
    stream = MockStream()
    _reconfigure_stream(stream)
    assert stream.reconfigured_kwargs == {
        "encoding": "utf-8",
        "errors": "backslashreplace",
    }

def test_reconfigure_stream_handles_no_reconfigure_gracefully():
    class StreamWithoutReconfigure:
        pass

    stream = StreamWithoutReconfigure()
    # This should not raise an exception
    _reconfigure_stream(stream)

def test_reconfigure_stream_swallows_value_and_os_errors():
    class RaisingStream:
        def reconfigure(self, **kwargs):
            raise ValueError("Invalid configuration")

    class OSRaisingStream:
        def reconfigure(self, **kwargs):
            raise OSError("OS error during reconfiguration")

    # These should not raise exceptions
    _reconfigure_stream(RaisingStream())
    _reconfigure_stream(OSRaisingStream())

def test_configure_output_encoding_reconfigures_stdout_and_stderr(monkeypatch):
    from youtrack_cli.console import _configure_output_encoding


    stdout_mock = MockStream()
    stderr_mock = MockStream()

    monkeypatch.setattr("sys.stdout", stdout_mock)
    monkeypatch.setattr("sys.stderr", stderr_mock)

    _configure_output_encoding()

    assert stdout_mock.reconfigured_kwargs == {
        "encoding": "utf-8",
        "errors": "backslashreplace",
    }
    assert stderr_mock.reconfigured_kwargs == {
        "encoding": "utf-8",
        "errors": "backslashreplace",
    }

def test_cp1252_regression():
    import io
    import pytest

    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp1252")

    # Writing "Pending → Processing" should raise UnicodeEncodeError because of '→'
    with pytest.raises(UnicodeEncodeError):
        stream.write("Pending → Processing")
        stream.flush()

    # Now, reconfigure the stream
    _reconfigure_stream(stream)

    # Writing "Pending → Processing" should now succeed
    stream.write("Pending → Processing")
    stream.flush()

    # The output byte string will contain the UTF-8 representation of '→' (b'\xe2\x86\x92')
    value = buffer.getvalue()
    assert b"Pending \xe2\x86\x92 Processing" in value


