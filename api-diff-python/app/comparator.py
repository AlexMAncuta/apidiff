"""
Breaking-change rules for OpenAPI specifications.

Central principle:
    requests may become MORE PERMISSIVE   (fewer constraints)
    responses may become RICHER           (more data)
    the opposite direction is BREAKING

The verdict is decided here, in Python. The language model only explains
the result; it never decides whether a change is breaking.
"""

import json

from app.normalizer import normalize

BREAKING = "BREAKING"
WARNING = "WARNING"
SAFE = "SAFE"


def _finding(severity: str, rule: str, location: str, detail: str) -> dict:
    return {
        "severity": severity,
        "rule": rule,
        "location": location,
        "detail": detail,
    }


def _enum_diff(old, new):
    o = set(old or [])
    n = set(new or [])
    return sorted(o - n), sorted(n - o)


def _compare_params(old: dict, new: dict, loc: str, out: list) -> None:
    for name, o in old.items():
        n = new.get(name)

        if n is None:
            out.append(_finding(BREAKING, "PARAM_REMOVED", loc,
                                f"parameter '{name}' was removed"))
            continue

        if not o["required"] and n["required"]:
            out.append(_finding(BREAKING, "PARAM_NOW_REQUIRED", loc,
                                f"'{name}': optional -> required"))
        elif o["required"] and not n["required"]:
            out.append(_finding(SAFE, "PARAM_NOW_OPTIONAL", loc,
                                f"'{name}': required -> optional"))

        if o["type"] != n["type"]:
            out.append(_finding(BREAKING, "PARAM_TYPE_CHANGED", loc,
                                f"'{name}': {o['type']} -> {n['type']}"))

        if o["enum"] is None and n["enum"] is not None:
            out.append(_finding(BREAKING, "PARAM_ENUM_INTRODUCED", loc,
                                f"'{name}': free value -> restricted to {n['enum']}"))
        elif o["enum"] is not None and n["enum"] is None:
            out.append(_finding(SAFE, "PARAM_ENUM_REMOVED", loc,
                                f"'{name}': enum restriction lifted"))
        else:
            removed, added = _enum_diff(o["enum"], n["enum"])
            if removed:
                out.append(_finding(BREAKING, "PARAM_ENUM_VALUE_REMOVED", loc,
                                    f"'{name}': values removed {removed}"))
            if added:
                out.append(_finding(SAFE, "PARAM_ENUM_VALUE_ADDED", loc,
                                    f"'{name}': values added {added}"))

    for name, n in new.items():
        if name in old:
            continue
        if n["required"]:
            out.append(_finding(BREAKING, "PARAM_ADDED_REQUIRED", loc,
                                f"new required parameter '{name}'"))
        else:
            out.append(_finding(SAFE, "PARAM_ADDED_OPTIONAL", loc,
                                f"new optional parameter '{name}'"))


def _compare_fields(old: dict, new: dict, loc: str,
                    direction: str, out: list) -> None:
    """direction is REQUEST or RESPONSE - the rules are mirrored."""
    is_request = direction == "REQUEST"

    for name, o in old.items():
        n = new.get(name)

        if n is None:
            out.append(_finding(BREAKING, f"{direction}_FIELD_REMOVED", loc,
                                f"field '{name}' disappeared"))
            continue

        if o["type"] != n["type"]:
            out.append(_finding(BREAKING, f"{direction}_FIELD_TYPE_CHANGED", loc,
                                f"'{name}': {o['type']} -> {n['type']}"))

        if is_request and not o["required"] and n["required"]:
            out.append(_finding(BREAKING, "REQUEST_FIELD_NOW_REQUIRED", loc,
                                f"'{name}': optional -> required"))

        removed, added = _enum_diff(o["enum"], n["enum"])

        if is_request:
            if removed:
                out.append(_finding(BREAKING, "REQUEST_ENUM_VALUE_REMOVED", loc,
                                    f"'{name}': values removed {removed}"))
            if added:
                out.append(_finding(SAFE, "REQUEST_ENUM_VALUE_ADDED", loc,
                                    f"'{name}': values added {added}"))
        else:
            if added:
                out.append(_finding(WARNING, "RESPONSE_ENUM_VALUE_ADDED", loc,
                                    f"'{name}': values added {added} - clients "
                                    f"with exhaustive switches may fail"))
            if removed:
                out.append(_finding(SAFE, "RESPONSE_ENUM_VALUE_REMOVED", loc,
                                    f"'{name}': values removed {removed}"))

    for name, n in new.items():
        if name in old:
            continue
        if is_request and n["required"]:
            out.append(_finding(BREAKING, "REQUEST_FIELD_ADDED_REQUIRED", loc,
                                f"new required field '{name}'"))
        else:
            out.append(_finding(SAFE, f"{direction}_FIELD_ADDED", loc,
                                f"new field '{name}'"))


def compare_specs(old_spec: dict, new_spec: dict) -> dict:
    """
    Compare two raw OpenAPI documents.

    Args:
        old_spec: parsed OpenAPI document of the older version.
        new_spec: parsed OpenAPI document of the newer version.

    Returns:
        A dictionary with a summary and the list of findings.
    """
    old = normalize(old_spec)
    new = normalize(new_spec)
    findings: list[dict] = []

    for key in sorted(set(old) - set(new)):
        findings.append(_finding(BREAKING, "ENDPOINT_REMOVED", key,
                                 "the endpoint no longer exists"))

    for key in sorted(set(new) - set(old)):
        findings.append(_finding(SAFE, "ENDPOINT_ADDED", key,
                                 "new endpoint"))

    for key in sorted(set(old) & set(new)):
        o, n = old[key], new[key]

        _compare_params(o["params"], n["params"], key, findings)
        _compare_fields(o["body"], n["body"], key, "REQUEST", findings)

        for status in sorted(set(o["responses"]) - set(n["responses"])):
            findings.append(_finding(BREAKING, "RESPONSE_STATUS_REMOVED", key,
                                     f"status {status} is no longer documented"))

        for status in sorted(set(o["responses"]) & set(n["responses"])):
            _compare_fields(o["responses"][status], n["responses"][status],
                            f"{key} [{status}]", "RESPONSE", findings)

    order = {BREAKING: 0, WARNING: 1, SAFE: 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["location"], f["rule"]))

    return {
        "summary": {
            "breaking": sum(f["severity"] == BREAKING for f in findings),
            "warning": sum(f["severity"] == WARNING for f in findings),
            "safe": sum(f["severity"] == SAFE for f in findings),
            "compatible": not any(f["severity"] == BREAKING for f in findings),
        },
        "findings": findings,
    }


def compare_files(old_path: str, new_path: str) -> dict:
    """Convenience wrapper for local testing without Cloud Storage."""
    with open(old_path, encoding="utf-8") as f:
        old_spec = json.load(f)
    with open(new_path, encoding="utf-8") as f:
        new_spec = json.load(f)
    return compare_specs(old_spec, new_spec)


if __name__ == "__main__":
    import sys

    old_path = sys.argv[1] if len(sys.argv) > 1 else "knowledge/openapi-v1.json"
    new_path = sys.argv[2] if len(sys.argv) > 2 else "knowledge/openapi-v2.json"

    result = compare_files(old_path, new_path)
    s = result["summary"]

    print(f"\n{s['breaking']} BREAKING | {s['warning']} WARNING | {s['safe']} SAFE")
    print("Compatible:", "YES" if s["compatible"] else "NO")
    print("-" * 78)

    for f in result["findings"]:
        print(f"[{f['severity']:<8}] {f['rule']:<32} {f['location']}")
        print(f"{'':11} {f['detail']}")