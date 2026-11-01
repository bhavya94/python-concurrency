"""A slow web server on this machine, so every wait in the lab is a real network wait.

A request for /item/<n> waits `delay` seconds, then gets a short answer. The server answers each request on its
own thread (ThreadingHTTPServer), so it can hold many waits at once. Any limit you see therefore comes from the
client: that is the part the lab measures.
"""

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)


class _SlowHandler(BaseHTTPRequestHandler):
    delay = 0.0
    protocol_version = "HTTP/1.0"  # one request per connection; the server closes it after the answer

    def do_GET(self):
        time.sleep(self.delay)
        body = f"answer for {self.path}\n".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        log.debug("server: " + format, *args)


class _Server(ThreadingHTTPServer):
    # The listen backlog: connections the OS queues before the server accepts them. The default is 5. With 64
    # requests at once, the OS would drop the rest and the client would retry after about a second, so the
    # limit would be the server's after all.
    request_queue_size = 128


class SlowServer:
    """Use it as `with SlowServer(delay=0.2) as server:`. It listens on 127.0.0.1, on a free port."""

    def __init__(self, delay: float):
        self.delay = delay
        self._httpd: ThreadingHTTPServer | None = None

    def __enter__(self) -> "SlowServer":
        handler = type("Handler", (_SlowHandler,), {"delay": self.delay})
        self._httpd = _Server(("127.0.0.1", 0), handler)  # port 0: the OS picks a free port
        threading.Thread(target=self._httpd.serve_forever, name="server", daemon=True).start()
        log.info("slow server on port %d: every answer waits %.0f ms", self.port, self.delay * 1000)
        return self

    def __exit__(self, *exc):
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def url(self, item: int) -> str:
        return f"http://127.0.0.1:{self.port}/item/{item}"
