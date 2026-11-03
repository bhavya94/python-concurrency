"""A slow web server on this machine, so every wait in these labs is a real wait on a network socket.

A request for /item/<n> sleeps `delay` seconds, then answers. An item listed in `fail` answers with an error,
HTTP 500, after the same wait. The server answers each request on its own
thread, so it never makes one request wait for another. Any queueing you see is the client's doing.
"""

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)


class _SlowHandler(BaseHTTPRequestHandler):
    delay = 0.0
    fail: frozenset[int] = frozenset()
    protocol_version = "HTTP/1.0"  # one request per connection: the server closes it after the answer

    def do_GET(self):
        # ThreadingHTTPServer runs each request on a new thread, named like "Thread-3 (process_request_thread)".
        # A short name keeps the log readable.
        threading.current_thread().name = "handler-" + self.path.rsplit("/", 1)[-1]
        log.info("received %s; sleeping %.0f ms", self.path, self.delay * 1000)
        time.sleep(self.delay)
        failing = int(self.path.rsplit("/", 1)[-1]) in self.fail
        log.info("answering %s%s", self.path, " with an error, HTTP 500" if failing else "")
        body = f"answer for {self.path}\n".encode()
        self.send_response(500 if failing else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # do_GET logs each request; the library's own access line would repeat it


class _Server(ThreadingHTTPServer):
    # The listen backlog: connections the OS holds until this server accepts them. The default is 5. When many
    # threads connect at once, the OS drops the extra connection attempts, and each client retries about a
    # second later.
    request_queue_size = 128

    def process_request(self, request, client_address):
        # Runs on the "server" thread, which only accepts connections. The parent class starts a new thread for
        # each one, so this thread is free to accept the next connection at once.
        log.info("connection accepted; starting a new thread to handle it")
        super().process_request(request, client_address)


class SlowServer:
    """`with SlowServer(delay=0.2) as server:` starts it on 127.0.0.1, on a free port, and stops it at the end."""

    def __init__(self, delay: float, fail: frozenset[int] = frozenset()):
        self.delay = delay
        self.fail = fail

    def __enter__(self) -> "SlowServer":
        handler = type("Handler", (_SlowHandler,), {"delay": self.delay, "fail": self.fail})
        self._httpd = _Server(("127.0.0.1", 0), handler)  # port 0: the OS picks a free port
        threading.Thread(target=self._httpd.serve_forever, name="server", daemon=True).start()
        log.info("slow server on port %d; every answer waits %.0f ms", self.port, self.delay * 1000)
        log.info("threads running: %s", ", ".join(t.name for t in threading.enumerate()))
        return self

    def __exit__(self, *exc) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]


def url(port: int, item: int) -> str:
    return f"http://127.0.0.1:{port}/item/{item}"
