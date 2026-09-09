# Deprecation Policy

Deprecation is how something is removed from an API without breaking the
clients that still use it. It converts an immediate failure into a planned
migration.

---

## The three phases

**Announce.** The endpoint or field is marked deprecated but continues to
work exactly as before. Nothing changes at runtime. Clients are told what
to use instead and by when.

**Observe.** Usage is measured. Deprecated elements are logged with the
caller's identity, so the owner knows who is still affected and can contact
them directly. Removal without this data is guesswork.

**Remove.** Only after usage has reached zero, or the announced window has
expired and the remaining callers have been notified individually. This is
the step the comparison tool reports as `ENDPOINT_REMOVED` or
`RESPONSE_FIELD_REMOVED`, and it is a MAJOR version change.

Skipping the middle phase is the usual failure. A deprecation notice that
nobody reads and nobody measures does not protect anyone.

---

## Marking a deprecation in OpenAPI

Set `deprecated: true` on the operation, the parameter, or the schema
property. It appears in the generated specification and in Swagger UI.

In Spring Boot, the Java `@Deprecated` annotation is picked up by springdoc
and produces the same result:

    @Deprecated
    @GetMapping("/old-endpoint")
    public List<Product> oldEndpoint() { ... }

For a field, springdoc also honours an explicit schema annotation:

    @Schema(deprecated = true, description = "Use 'summary' instead.")
    private String description;

Marking something deprecated is not a breaking change. It carries no
runtime effect and the comparison tool does not flag it. That is the point:
it lets the API owner communicate intent without any risk.

---

## Communicating at runtime

The specification is read by developers. The response headers are read by
running systems. Both matter.

    Deprecation: Wed, 01 Oct 2025 00:00:00 GMT
    Sunset: Wed, 01 Apr 2026 00:00:00 GMT
    Link: <https://docs.example.com/migration/v2>; rel="deprecation"

`Sunset` is defined by RFC 8594 and states when the endpoint will stop
working. A client can monitor for these headers and raise an alert long
before the removal date.

---

## Choosing the window

The window should be long enough for a client team to schedule the work
into a normal sprint, not long enough to be forgotten. As a starting point:
one quarter for internal clients, two quarters for partners, one year for
public APIs.

Announce the date at the start of the window and do not move it forward.
Moving a sunset date earlier destroys the trust that makes deprecation
work at all.

---

## What deprecation does not solve

A field whose meaning changes while its type stays the same cannot be
deprecated, because there is nothing new to point clients at. If `price`
changes from euros to cents, both the old and the new contract are
`number`. No tool detects it and no header communicates it.

Changes of that kind require a new field name, so that the old and the new
meaning can coexist and be told apart.