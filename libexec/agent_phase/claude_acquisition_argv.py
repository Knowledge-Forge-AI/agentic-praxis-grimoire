"""Closed argv grammar for the internal read-only acquisition route."""
from pathlib import Path


def validate(arguments, *, observation=False):
    """Task is supplied on stdin; no arbitrary native options are admitted.

    A closed grammar also rejects new provider aliases without waiting for a
    denylist update. Only the observation owner may add its two logging options.
    """
    result = []
    flags = {"--read-only": 0, "-p": 0, "--print": 0}
    if observation:
        flags.update({"--live-log": 1, "--live-display": 1})
    seen = set()
    index = 0
    while index < len(arguments):
        flag = arguments[index]
        key = "-p" if flag == "--print" else flag
        if flag not in flags or key in seen:
            raise ValueError("unsupported or ambiguous internal acquisition argument")
        seen.add(key)
        result.append(key)
        if flags[flag]:
            index += 1
            if index >= len(arguments) or not arguments[index] or arguments[index].startswith("-"):
                raise ValueError("missing internal observation option value")
            result.append(arguments[index])
        index += 1
    if not {"--read-only", "-p"} <= seen:
        raise ValueError("internal acquisition requires read-only stdin print mode")
    return result


def prepare_argv(argv):
    if len(argv) < 4 or Path(argv[0]).name != "claude-profile":
        raise ValueError("unsupported Claude profile seam")
    return [*argv[:2], *validate(argv[2:])]
