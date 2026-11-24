"""Final-fixture-check helper for Stage 2 and Stage 3 (new file; no frozen Stage 1 file is imported or edited).

Problem seen in Stage 1: the last fixture check ("oracle after") can fail only because a short-lived
`ros2` command-line node (name `_ros2cli_<pid>`, started by one of the model's ROS tool calls) is still
shutting down. Such a node shows up as an extra publisher/subscriber in `ros2 topic info --verbose`
or as an extra entry in `ros2 node list --all`. More tool calls leave more of them behind, so the
failure rate rises with the number of calls per episode. (The mechanism is from the Codex review of
2026-11-22 plus the fixture code; the 54 of 59 laptop attempts were not re-counted here.)

Two defences, applied together, so a real fixture fault is never hidden:
  1. WAIT: poll until no transient CLI node is visible, up to `settle_timeout_s`.
  2. IGNORE: after the wait, drop whatever transient CLI names remain from the comparison, and
     RECORD their names. A fixture node (any name not matching the transient pattern) is never dropped.
If the wait times out, the check still runs and the report says `settled=False`; it is data, not an error.
"""
import re
import subprocess
import time

# `_ros2cli_<digits>` is one CLI invocation. `_ros2cli_daemon_<n>_<uuid>` is the discovery daemon, which
# the run owns and stops itself, so it is treated as transient for graph comparison only.
TRANSIENT_CLI_PATTERN = re.compile(r"^/?(?:[^/\s]+/)*_ros2cli_(?:daemon_)?[0-9A-Za-z_]+$")


def is_transient_cli_node(full_name):
    """True only for ros2 command-line helper nodes. Fixture nodes never start with `_ros2cli_`."""
    return bool(TRANSIENT_CLI_PATTERN.match(full_name.strip()))


def visible_nodes(run_command, timeout_s=15):
    """All node names including hidden ones, minus the listing command's own helper node.
    `run_command(args, timeout_s)` returns (stdout_text, child_pid). `--all` is needed because
    `ros2 node list` hides names that start with an underscore. The listing command creates its own
    `_ros2cli_<its pid>` node and sees it, so that one name is removed (found by the first real-ROS
    test: without this the wait never settles)."""
    text, own_pid = run_command(["ros2", "node", "list", "--all", "--no-daemon", "--spin-time", "4"], timeout_s)
    names = [line.strip() for line in text.splitlines() if line.strip()]
    return [n for n in names if n != f"/_ros2cli_{own_pid}"]


def wait_until_no_transient_nodes(run_command, settle_timeout_s=30.0, poll_interval_s=1.0, clean_listings_needed=2, expected_nodes=(), clock=time.monotonic, sleep=time.sleep):
    """Returns dict(settled, waited_s, transient_seen, discovery_misses). `settled` is False if the timeout ended the wait.

    Empty-discovery retry: a short discovery spin on a busy machine can list NO node, or miss a live fixture node (seen on the laptop). When `expected_nodes` is given, a listing that lacks any of
    them is a DISCOVERY MISS: it never counts as clean, it is counted, and the poll goes on. A listing that contains every expected node proves discovery worked, so ONE such clean listing settles.
    Without `expected_nodes` only an EMPTY listing is known to be wrong, so `clean_listings_needed` (default 2) clean listings in a row are required."""
    started = clock()
    transient_seen = set()
    clean_in_a_row = 0
    discovery_misses = 0
    needed = 1 if expected_nodes else clean_listings_needed
    while True:
        nodes = visible_nodes(run_command)
        transient_now = [n for n in nodes if is_transient_cli_node(n)]
        transient_seen.update(transient_now)
        trustworthy = bool(nodes) and all(n in nodes for n in expected_nodes)   # an empty listing is never trusted: a live fixture always has nodes
        if not trustworthy:
            discovery_misses += 1
        clean_in_a_row = clean_in_a_row + 1 if (trustworthy and not transient_now) else 0
        if clean_in_a_row >= needed:
            return dict(settled=True, waited_s=round(clock() - started, 2), transient_seen=sorted(transient_seen), discovery_misses=discovery_misses)
        if clock() - started >= settle_timeout_s:
            return dict(settled=False, waited_s=round(clock() - started, 2), transient_seen=sorted(transient_seen), discovery_misses=discovery_misses)
        sleep(poll_interval_s)


def drop_transient(names):
    """Split a list of node names into (kept, ignored). Used on node lists and on topic-endpoint node names."""
    kept = [n for n in names if not is_transient_cli_node(n)]
    ignored = [n for n in names if is_transient_cli_node(n)]
    return kept, ignored


def compare_endpoints(expected, observed):
    """Compare expected and observed endpoint node sets for one topic after dropping transient CLI nodes.
    Returns dict(match, missing, unexpected, ignored). `unexpected` is non-empty only for real extra nodes."""
    kept, ignored = drop_transient(sorted(observed))
    missing = sorted(set(expected) - set(kept))
    unexpected = sorted(set(kept) - set(expected))
    return dict(match=not missing and not unexpected, missing=missing, unexpected=unexpected, ignored=ignored)


def check_fixture_graph(run_command, expected_nodes, allowed_extra_nodes=(), settle_timeout_s=30.0, poll_interval_s=1.0, clock=time.monotonic, sleep=time.sleep):
    """The final (or initial) fixture check of Stage 2 and Stage 3, in one call: wait for transient CLI nodes to go, then compare the real node set.
    ok is False only for a missing expected node or a REAL extra node (not a CLI helper, not in `allowed_extra_nodes`). `settle` carries settled/waited_s/discovery_misses/transient_seen so the row
    records what was waited for and ignored; a timeout (settled False) is data, and the comparison still runs on what is visible."""
    settle = wait_until_no_transient_nodes(run_command, settle_timeout_s, poll_interval_s, expected_nodes=expected_nodes, clock=clock, sleep=sleep)
    kept, ignored = drop_transient(visible_nodes(run_command))
    missing = sorted(n for n in expected_nodes if n not in kept)
    unexpected = sorted(n for n in kept if n not in expected_nodes and n not in allowed_extra_nodes)
    return dict(ok=not missing and not unexpected, missing=missing, unexpected=unexpected, ignored=sorted(ignored), settle=settle)


def real_run_command(args, timeout_s, env=None):
    """Runs one command; returns (stdout, pid of the command). Raises with stderr on a non-zero exit."""
    process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    if process.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed ({process.returncode}): {stderr.strip()[:200]}")
    return stdout, process.pid
