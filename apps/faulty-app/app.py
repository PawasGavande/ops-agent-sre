"""Faulty demo microservice for OpsAgent.

FAULT_MODE controls behaviour:
  healthy - serves traffic normally
  crash   - logs an error and exits non-zero after CRASH_DELAY_SECONDS
            (=> CrashLoopBackOff)
  leak    - allocates LEAK_MB_PER_TICK MB every second and never frees it
            (=> OOMKilled once the container memory limit is hit)
"""
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("faulty-app")

FAULT_MODE = os.getenv("FAULT_MODE", "healthy").lower()
CRASH_DELAY = float(os.getenv("CRASH_DELAY_SECONDS", "10"))
LEAK_MB = int(os.getenv("LEAK_MB_PER_TICK", "5"))
PORT = int(os.getenv("PORT", "8080"))

_leaked = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/healthz", "/"):
            body = f"ok mode={FAULT_MODE}\n".encode()
            self.send_response(200)
        else:
            body = b"not found\n"
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.info("http " + fmt, *args)


def crash_later():
    time.sleep(CRASH_DELAY)
    log.error("FATAL: simulated database connection failure: "
              "could not connect to postgres.db.svc:5432 (connection refused)")
    log.error("Shutting down with exit code 1")
    logging.shutdown()
    os._exit(1)


def leak_forever():
    while True:
        _leaked.append(bytearray(LEAK_MB * 1024 * 1024))
        log.warning("Cache size growing: %d MB retained", len(_leaked) * LEAK_MB)
        time.sleep(1)


def main():
    log.info("Starting faulty-app mode=%s port=%d", FAULT_MODE, PORT)
    if FAULT_MODE == "crash":
        threading.Thread(target=crash_later, daemon=True).start()
    elif FAULT_MODE == "leak":
        threading.Thread(target=leak_forever, daemon=True).start()
    elif FAULT_MODE != "healthy":
        log.error("Unknown FAULT_MODE=%s", FAULT_MODE)
        sys.exit(2)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
