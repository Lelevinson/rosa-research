"""Status-only notifications: ntfy (default) and optional Gmail. Never carries research content.
Config lives OUTSIDE the repository in ~/.config/rosa-exam/ (never committed): notify.env holds NTFY_TOPIC (random) and, optionally, the Gmail app password:
    NTFY_SERVER=https://ntfy.sh        NTFY_TOPIC=<random string made by `notify.py init`>
    EMAIL_ENABLED=1  GMAIL_USER=<GMAIL_ADDRESS>  GMAIL_APP_PASSWORD=<16-character app password>  EMAIL_TO=...
Usage:  python notify.py init | test KIND | test-all | show-topic
Safety: a message is built only from the fixed templates below; every value must be an integer or a short token of letters, digits, space, dot, dash or underscore.
Task ids, model answers, trace paths and file names cannot pass the check."""
import os
import re
import secrets
import smtplib
import sys
import time
import urllib.request
from email.message import EmailMessage
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("ROSA_EXAM_CONFIG_DIR", Path.home() / ".config" / "rosa-exam"))
ENV_FILE = CONFIG_DIR / "notify.env"
LOG_FILE = CONFIG_DIR / "notify.log"
TEMPLATES = {
    "finished": ("Exam queue finished", "Exam queue finished on {machine}: {done} of {total} cells done, {skipped} skipped.", "default"),
    "crash": ("Exam queue stopped", "Exam queue runner on {machine} stopped unexpectedly. Done {done} of {total} cells.", "urgent"),
    "no_progress": ("No progress", "No progress for {minutes} min on {machine}. Done {done} of {total} cells.", "high"),
    "ollama_down": ("Ollama down", "Ollama unreachable from {machine} for {minutes} min. Done {done} of {total} cells.", "high"),
    "low_disk": ("Low disk", "Low disk on {machine}: {free_gb} GB free. Done {done} of {total} cells.", "high"),
    "study_failing": ("A block keeps failing", "A block group keeps failing on {machine} and was skipped after {tries} tries. Done {done} of {total} cells.", "high"),
    "daily": ("Daily summary", "Daily summary {machine}: done {done} of {total} cells, tier {tier}, {skipped} skipped, disk {free_gb} GB free.", "default"),
    "test": ("Test notification", "Test notification of kind {kind} from {machine}.", "low"),
}
SAFE_VALUE = re.compile(r"^[A-Za-z0-9 ._-]{1,32}$")


def load_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_message(kind, **values):
    if kind not in TEMPLATES:
        raise ValueError(f"unknown notification kind {kind!r}")
    for key, value in values.items():
        if not (isinstance(value, int) and not isinstance(value, bool)) and not (isinstance(value, (str, float)) and SAFE_VALUE.match(str(value))):
            raise ValueError(f"value for {key!r} is not allowed in a status message")
    title, template, priority = TEMPLATES[kind]
    return title, template.format(**values), priority


def log(line):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as handle:
        handle.write(f"{time.strftime('%F %T')} {line}\n")


def send_ntfy(title, message, priority, env):
    topic = env.get("NTFY_TOPIC")
    if not topic:
        raise RuntimeError("NTFY_TOPIC missing: run `python notify.py init`")
    request = urllib.request.Request(f"{env.get('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')}/{topic}", message.encode(), {"Title": title, "Priority": priority, "Tags": "robot"})
    urllib.request.urlopen(request, timeout=15).read()


def send_email(title, message, env):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = f"[ROSA exam] {title}", env["GMAIL_USER"], env["EMAIL_TO"]
    msg.set_content(message)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(env["GMAIL_USER"], env["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)


def send(kind, **values):
    """Send one status message. Returns a dict of which channels succeeded. A failure never raises: the runner must not stop because a phone message failed."""
    title, message, priority = build_message(kind, **values)
    if os.environ.get("ROSA_EXAM_NOTIFY_DRY"):  # tests: write the message that would be sent instead of sending it
        with open(os.environ["ROSA_EXAM_NOTIFY_DRY"], "a") as handle:
            handle.write(f"{kind}\t{message}\n")
        return {"ntfy": "dry", "email": None}
    env = load_env()
    result = {"ntfy": False, "email": None}
    try:
        send_ntfy(title, message, priority, env)
        result["ntfy"] = True
    except Exception as error:  # noqa: BLE001
        log(f"ntfy failed for {kind}: {type(error).__name__}: {error}")
    if env.get("EMAIL_ENABLED") == "1":
        try:
            send_email(title, message, env)
            result["email"] = True
        except Exception as error:  # noqa: BLE001
            result["email"] = False
            log(f"email failed for {kind}: {type(error).__name__}: {error}")
    log(f"sent {kind}: {result}")
    return result


def init():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    env = load_env()
    if env.get("NTFY_TOPIC"):
        print("topic already exists (not changed):", env["NTFY_TOPIC"])
        return
    topic = "rosa-exam-" + secrets.token_urlsafe(12).replace("_", "x").replace("-", "y")
    ENV_FILE.write_text(f"# local, untracked, never commit\nNTFY_SERVER=https://ntfy.sh\nNTFY_TOPIC={topic}\n# optional email through a Gmail app password:\n# EMAIL_ENABLED=1\n# GMAIL_USER=\n# GMAIL_APP_PASSWORD=\n# EMAIL_TO=\n")
    ENV_FILE.chmod(0o600)
    print("created", ENV_FILE, "with topic", topic, "\nSubscribe to this topic in the ntfy app (server ntfy.sh).")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    machine = os.environ.get("ROSA_EXAM_MACHINE", "laptop")
    if command == "init":
        init()
    elif command == "show-topic":
        print(load_env().get("NTFY_TOPIC", "(not set)"))
    elif command == "test":
        kind = sys.argv[2]
        sample = dict(machine=machine, done=3, total=8, skipped=0, minutes=15, free_gb=12.5, tier="tier1", tries=3, kind=kind)
        print(send(kind, **{k: v for k, v in sample.items() if "{" + k + "}" in TEMPLATES[kind][1]}))
    elif command == "test-all":
        for kind in TEMPLATES:
            sample = dict(machine=machine, done=3, total=8, skipped=0, minutes=15, free_gb=12.5, tier="tier1", tries=3, kind=kind)
            print(kind, send(kind, **{k: v for k, v in sample.items() if "{" + k + "}" in TEMPLATES[kind][1]}))
            time.sleep(1)
    else:
        print(__doc__)
