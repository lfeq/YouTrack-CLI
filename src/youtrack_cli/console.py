import sys

def _reconfigure_stream(stream):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass

def _configure_output_encoding():
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)



