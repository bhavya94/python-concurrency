"""A slow web server on this machine, so every wait in these labs is a real wait on a network socket.

A request for /item/<n> sleeps `delay` seconds, then answers. The server answers each request on its own
thread, so it never makes one request wait for another. Any queueing you see is the client's doing.
"""

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)


class _SlowHandler(BaseHTTPRequestHandler):
    delay = 0.0
    protocol_version = "HTTP/1.0"  # one request per connection: the server closes it after the answer

    def do_GET(self):
        time.sleep(self.delay)
        body = f"answer for {self.path}\n".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # the client logs each request already; a server line too would double the output


class SlowServer:
    """`with SlowServer(delay=0.2) as server:` starts it on 127.0.0.1, on a free port, and stops it at the end."""

    def __init__(self, delay: float):
        self.delay = delay

    def __enter__(self) -> "SlowServer":
        handler = type("Handler", (_SlowHandler,), {"delay": self.delay})
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)  # port 0: the OS picks a free port
        threading.Thread(target=self._httpd.serve_forever, name="server", daemon=True).start()
        log.info("slow server on port %d; every answer waits %.0f ms", self.port, self.delay * 1000)
        return self

    def __exit__(self, *exc) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def url(self, item: int) -> str:
        return f"http://127.0.0.1:{self.port}/item/{item}"
