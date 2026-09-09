# Breaking Change Rules

This document is the reference catalogue for every rule applied by the
comparison tool. Each rule has an identifier, a severity, and an
explanation of what a client experiences when the change is deployed.

The severity in this document always matches the severity returned by the
tool. If they ever disagree, the tool is authoritative.

---

## The governing principle

An API change is safe when it does not invalidate any assumption an
existing client already relies on.

    Requests may become MORE PERMISSIVE.
    Responses may become RICHER.
    The opposite direction is BREAKING.

A client sends requests and reads responses. Loosening what the server
accepts cannot break a caller that was already sending valid data.
Adding data to a response cannot break a caller that ignores unknown
fields. Tightening a request or shrinking a response can break both.

---

## Endpoint rules

### ENDPOINT_REMOVED — BREAKING

A method and path combination that existed before is gone. Every client
calling it receives 404 or 405 immediately after deployment.

Note that the comparison key is method plus path, not path alone. Removing
`DELETE /api/products/{id}` while keeping `GET /api/products/{id}` is a
breaking change even though the path still exists.

Correct approach: deprecate first, remove later. See `deprecation-policy.md`.

### ENDPOINT_ADDED — SAFE

A new method and path combination. No existing client calls it, so nothing
can break.

### RESPONSE_STATUS_REMOVED — BREAKING

A documented status code disappeared. Clients that branch on that status
now fall into their default or error path. This is easy to overlook because
the endpoint itself still works for the common case.

---

## Query and path parameter rules

### PARAM_REMOVED — BREAKING

Strictly, many servers ignore unknown query parameters, so the request may
still succeed. It is classified as breaking because the client's intent is
silently discarded: a caller filtering a list now receives the unfiltered
list and may act on wrong data. Silent wrong behaviour is worse than a
loud failure.

### PARAM_NOW_REQUIRED — BREAKING

A parameter that was optional is now mandatory. Every client that omitted
it receives 400 Bad Request. This is one of the most common accidental
breaking changes, because in Java it is a one-word edit:

    @RequestParam(required = false) Category category
    @RequestParam(required = true)  Category category

Correct approach: keep the parameter optional and apply a default value on
the server.

### PARAM_NOW_OPTIONAL — SAFE

The constraint was relaxed. Clients that still send the parameter continue
to work unchanged.

### PARAM_ADDED_REQUIRED — BREAKING

A new mandatory parameter. No existing client sends it, so every existing
call fails with 400.

### PARAM_ADDED_OPTIONAL — SAFE

New capability, no obligation. Existing clients are unaffected.

### PARAM_TYPE_CHANGED — BREAKING

The accepted type changed, for example `string` to `integer`. Requests
carrying the old type are rejected during deserialisation.

The type includes the OpenAPI `format`. A change from `number/double` to
`number` still counts, because precision and range guarantees differ even
though the base type is identical.

### PARAM_ENUM_VALUE_REMOVED — BREAKING

The set of accepted values shrank. A client sending a removed value gets
400. This is easy to miss in Java because removing a constant from an enum
     looks like a local cleanup, not an API change.

### PARAM_ENUM_VALUE_ADDED — SAFE

The set of accepted values grew. Every previously valid request is still
valid.

### PARAM_ENUM_INTRODUCED — BREAKING

A parameter that accepted any value is now restricted to a fixed list.
Requests carrying values outside the list are rejected.

### PARAM_ENUM_REMOVED — SAFE

The restriction was lifted. Everything previously accepted is still
accepted.

---

## Request body rules

Request fields follow the same direction as parameters: the server may
accept more, never less.

### REQUEST_FIELD_REMOVED — BREAKING

A field the client was sending is no longer part of the contract. The data
is silently dropped, so the created or updated resource is not what the
caller intended.

### REQUEST_FIELD_TYPE_CHANGED — BREAKING

Deserialisation of existing client payloads fails, usually as 400.

### REQUEST_FIELD_NOW_REQUIRED — BREAKING

Clients that omitted the field are rejected. Same shape of problem as
`PARAM_NOW_REQUIRED`.

### REQUEST_FIELD_ADDED_REQUIRED — BREAKING

No existing client sends the new field, so every existing call fails.

### REQUEST_FIELD_ADDED — SAFE

An optional new field. Existing payloads remain valid.

### REQUEST_ENUM_VALUE_REMOVED — BREAKING

A value the client could previously send is now rejected.

### REQUEST_ENUM_VALUE_ADDED — SAFE

More values accepted, nothing previously valid becomes invalid.

---

## Response body rules

Response fields follow the mirrored direction: the server may return more,
never less.

### RESPONSE_FIELD_REMOVED — BREAKING

The client reads that field. Depending on its deserialiser it either gets
`null` and fails later with a NullPointerException far from the real cause,
or it fails immediately on a missing required property. This is the most
frequently underestimated breaking change, because the API owner's own
tests usually still pass.

### RESPONSE_FIELD_TYPE_CHANGED — BREAKING

The client's model no longer matches the payload. In Java a change from
`Double` to `BigDecimal` shows up as `number/double` becoming `number`,
and typed clients fail to deserialise.

### RESPONSE_FIELD_ADDED — SAFE

Clients that ignore unknown fields are unaffected. Note the assumption:
this is safe only because well-behaved clients tolerate unknown
properties. A client configured to fail on unknown fields, such as Jackson
with `FAIL_ON_UNKNOWN_PROPERTIES` enabled, will break. That configuration
is considered a client-side defect, not an API-side one.

### RESPONSE_ENUM_VALUE_ADDED — WARNING

Not breaking at the transport level, but a client with an exhaustive
`switch` over the old values, or a Java `Enum.valueOf` call, throws at
runtime when the new value first appears. Whether this matters depends on
how clients are written, which is why it is a warning rather than a
verdict.

### RESPONSE_ENUM_VALUE_REMOVED — SAFE

The client has a branch that will never be taken. Dead code, not a failure.

---

## Rules deliberately not implemented

Listed so their absence is understood as a scope decision rather than an
oversight:

- authentication and security scheme changes
- header parameter changes
- pagination and rate-limit behaviour
- semantic changes with an unchanged schema, for example a field that keeps
  its type but changes its unit from euros to cents

The last category is worth emphasising. No schema comparison tool can
detect it. Only a changelog written by a human can.