# Migration Guide

What to do once the comparison tool has reported breaking changes. The
first section is for the API owner, the second for the client developer.

---

## For the API owner: avoid the break

Most findings have an additive alternative. Below, each rule is paired with
the change that achieves the same goal without breaking anyone.

### ENDPOINT_REMOVED

Do not delete. Mark `@Deprecated`, announce a sunset date, measure usage,
remove in the next major version. See `deprecation-policy.md`.

If the endpoint moved rather than disappeared, keep the old path returning
`301` or `308` to the new one for one release cycle.

### PARAM_NOW_REQUIRED

Keep the parameter optional and apply the default on the server:

    // breaking
    @RequestParam(required = true) Category category

    // additive
    @RequestParam(required = false) Category category
    // ... if (category == null) return everything;

If the requirement is genuinely non-negotiable, add a new endpoint with the
stricter contract and deprecate the old one.

### PARAM_ENUM_VALUE_REMOVED and REQUEST_ENUM_VALUE_REMOVED

Keep the constant in the enum. Reject the value at the service layer with a
clear error message, or map it to its replacement. The client then receives
a 422 explaining what happened, rather than a 400 from deserialisation with
no context.

### RESPONSE_FIELD_REMOVED

Keep returning the field for one release cycle, populated from the new
source of truth if the underlying data moved. Mark it deprecated in the
schema so the intent is visible.

### RESPONSE_FIELD_TYPE_CHANGED and REQUEST_FIELD_TYPE_CHANGED

Add a new field beside the old one instead of changing the existing one:

    private Double price;            // deprecated, still populated
    private BigDecimal priceExact;   // new

Both are populated during the transition. The old field is removed in the
next major version.

### RESPONSE_ENUM_VALUE_ADDED

Not breaking, but announce it. Clients written with an exhaustive switch or
a bare `Enum.valueOf` will throw the first time the new value appears in
production data, which may be weeks after the deploy.

---

## When the break is unavoidable

Some changes cannot be made additively, usually because the old contract
was wrong rather than merely outdated. In that case:

1. Bump the major version and expose the new contract on a new path.
2. Keep the previous version running for the announced window.
3. Publish a changelog that lists every breaking finding, grouped by root
   cause, with the exact client-side edit required for each.
4. Contact the known callers directly. A changelog is not a notification.
5. Measure traffic on the old version until it reaches zero.

---

## For the client developer: assess the impact

A breaking change in the specification only matters if the client actually
touches the affected part of the contract. The comparison output is a list
of possible impacts; the code decides which ones are real.

For each BREAKING finding, ask three questions in order.

**Does the client call this endpoint at all?** If not, the finding is
irrelevant regardless of severity.

**Does the client read the affected field?** A removed response field the
client never deserialises costs nothing. A removed field that feeds a
calculation is an outage.

**Does the client send the affected value?** A removed enum constant only
matters if that constant appears in outgoing requests. Search the codebase
for the literal.

The findings that survive all three questions are the real work. In
practice this is usually a small fraction of the reported total, because
one schema change is reported once per affected endpoint.

---

## Reading the output correctly

When a shared schema such as `Product` changes, the tool reports the change
separately for every endpoint that uses that schema. Removing one field
from a schema used by six operations produces six findings.

This is intentional and should not be deduplicated: each finding is a real
place where a client can break, and different clients call different
endpoints. Group by root cause when writing the changelog, but scope the
client-side impact analysis by endpoint.