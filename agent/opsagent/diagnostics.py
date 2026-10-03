"""Read-only kubectl diagnostics.

Safety: only an allowlist of read verbs is ever executed, arguments are passed
as a list (no shell), and namespace/pod names are validated against the
Kubernetes DNS-label pattern so alert labels cannot inject flags.
"""
import re
import subprocess

from .config import settings
from .models import Diagnostics

READ_ONLY_VERBS = {"logs", "describe", "get"}
_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$")


class UnsafeArgument(ValueError):
    pass


def validate_name(value: str) -> str:
    if not value or len(value) > 253 or not _NAME_RE.match(value):
        raise UnsafeArgument(f"invalid kubernetes name: {value!r}")
    return value


def run_kubectl(args: list[str]) -> str:
    if not args or args[0] not in READ_ONLY_VERBS:
        raise UnsafeArgument(f"kubectl verb not allowed: {args[:1]}")
    proc = subprocess.run(
        [settings.kubectl_bin, *args],
        capture_output=True,
        text=True,
        timeout=settings.kubectl_timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"kubectl exited {proc.returncode}")
    return proc.stdout


def collect(namespace: str, pod: str) -> Diagnostics:
    ns, p = validate_name(namespace), validate_name(pod)
    tail = str(settings.log_tail_lines)
    d = Diagnostics(namespace=ns, pod=p)
    steps = {
        "logs": ["logs", p, "-n", ns, f"--tail={tail}"],
        "previous_logs": ["logs", p, "-n", ns, "--previous", f"--tail={tail}"],
        "describe": ["describe", "pod", p, "-n", ns],
        "events": ["get", "events", "-n", ns,
                   f"--field-selector=involvedObject.name={p}",
                   "--sort-by=.lastTimestamp"],
    }
    for field, args in steps.items():
        try:
            setattr(d, field, run_kubectl(args))
        except Exception as exc:  # keep going; partial data is still useful
            d.errors.append(f"{field}: {exc}")
    return d
