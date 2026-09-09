"""
normalizer.py
-------------
Transforma un spec OpenAPI brut intr-o structura plata, usor de comparat.

Rezultatul lui normalize() arata asa:

{
  "GET /api/products": {
      "params":    {"category": {"in": "query", "required": True,
                                 "type": "string", "enum": [...]}},
      "body":      {},
      "responses": {"200": {"[].id": {"type": "integer/int64", ...}, ...}}
  },
  ...
}

Cheia e METHOD + PATH, nu doar PATH: daca dispare doar metoda DELETE,
calea ramane si nu ai vedea nimic comparand doar caile.
"""

import json

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_ref(schema, spec, depth=0):
    """Urmareste $ref pana ajunge la schema reala din components."""
    while isinstance(schema, dict) and "$ref" in schema and depth < 20:
        parts = schema["$ref"].split("/")[1:]  # "#/components/schemas/Product"
        node = spec
        for part in parts:
            node = node.get(part, {}) if isinstance(node, dict) else {}
        schema = node
        depth += 1
    return schema if isinstance(schema, dict) else {}


def type_of(schema, spec):
    """
    Tipul = type + format impreuna.
    Double -> BigDecimal schimba doar 'format', deci comparate separat
    nu s-ar vedea nimic.
    """
    schema = resolve_ref(schema, spec)
    t = schema.get("type", "any")
    if isinstance(t, list):                      # OpenAPI 3.1: ["string", "null"]
        t = "|".join(sorted(t))
    if t == "array":
        return "array<%s>" % type_of(schema.get("items", {}), spec)
    fmt = schema.get("format")
    return f"{t}/{fmt}" if fmt else t


def flatten(schema, spec, prefix=""):
    """
    Aplatizeaza o schema intr-un dict {"cale.camp": {type, enum, required}}.
    Obiectele imbricate devin "address.city", array-urile devin "[].name".
    """
    schema = resolve_ref(schema, spec)
    if not schema:
        return {}

    if schema.get("type") == "array" or "items" in schema:
        return flatten(schema.get("items", {}), spec, prefix + "[]")

    props = schema.get("properties")
    if props:
        required = set(schema.get("required", []))
        out = {}
        for name, sub in props.items():
            sub = resolve_ref(sub, spec)
            path = f"{prefix}.{name}" if prefix else name
            if sub.get("properties") or sub.get("type") == "array":
                out.update(flatten(sub, spec, path))
            else:
                out[path] = {
                    "type": type_of(sub, spec),
                    "enum": sub.get("enum"),
                    "required": name in required,
                }
        return out

    if prefix:  # scalar simplu (ex. response care e doar un string)
        return {prefix: {"type": type_of(schema, spec),
                         "enum": schema.get("enum"),
                         "required": False}}
    return {}


def pick_media(content):
    """Springdoc pune request-urile pe application/json si response-urile pe */*."""
    if not content:
        return None
    for key in ("application/json", "*/*"):
        if key in content:
            return content[key]
    return next(iter(content.values()))


def normalize(spec):
    endpoints = {}
    for path, item in (spec.get("paths") or {}).items():
        shared_params = item.get("parameters", [])
        for method, op in item.items():
            if method not in HTTP_METHODS:
                continue

            params = {}
            for p in shared_params + op.get("parameters", []):
                p = resolve_ref(p, spec)
                sch = resolve_ref(p.get("schema", {}), spec)
                params[p.get("name")] = {
                    "in": p.get("in"),
                    "required": bool(p.get("required", False)),
                    "type": type_of(sch, spec),
                    "enum": sch.get("enum"),
                }

            body = {}
            request_body = resolve_ref(op.get("requestBody", {}), spec)
            media = pick_media(request_body.get("content", {}))
            if media:
                body = flatten(media.get("schema", {}), spec)

            responses = {}
            for status, resp in (op.get("responses") or {}).items():
                resp = resolve_ref(resp, spec)
                media = pick_media(resp.get("content", {}))
                responses[str(status)] = flatten(media.get("schema", {}), spec) if media else {}

            endpoints[f"{method.upper()} {path}"] = {
                "params": params,
                "body": body,
                "responses": responses,
            }
    return endpoints


if __name__ == "__main__":
    import sys
    print(json.dumps(normalize(load_spec(sys.argv[1])), indent=2, ensure_ascii=False))