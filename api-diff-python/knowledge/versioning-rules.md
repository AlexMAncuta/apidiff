# API Versioning Rules

How to version an HTTP API so that breaking changes become a deliberate
decision rather than an accident.

---

## Semantic versioning applied to APIs

    MAJOR   a breaking change; existing clients must be modified
    MINOR   new capability, backwards compatible
    PATCH   bug fix, no contract change

The comparison tool answers exactly one question: does this diff force a
MAJOR bump? If it reports at least one BREAKING finding, the answer is yes.

---

## Where the version belongs

**URL path**, for example `/api/v1/products` and `/api/v2/products`.
Explicit, easy to route, easy to cache, easy to see in a log line. The cost
is duplicated paths in the specification. This is the most common choice
and the easiest one to operate.

**Header**, for example `Accept: application/vnd.company.v2+json`. Keeps
URLs stable and is closer to HTTP semantics, but it is invisible in logs
and browser address bars, and harder to test by hand.

**Query parameter**, for example `?version=2`. Simple but easy to forget,
and it interacts badly with caching.

Pick one and apply it consistently. Mixing schemes across an API surface
causes more confusion than any of them causes on its own.

---

## Only major versions need a number

A MINOR change does not create `/api/v1.1/products`. Clients cannot be
expected to track point releases, and every additional path is a
maintenance cost. Add the capability to the existing major version and
document it in the changelog.

---

## Run two major versions in parallel, not five

When a MAJOR version is released, keep the previous one running for a
defined window while clients migrate. Two active major versions is a
manageable maintenance load. Beyond that, every bug fix has to be
backported several times and the team slows down.

The window length depends on who the clients are:

- internal clients in the same organisation: weeks
- partner integrations: one to two quarters
- public API with unknown consumers: a year or more

---

## Additive change is almost always available

Most breaking changes have an additive alternative that costs slightly
more code and saves a migration for everyone.

Instead of changing a field's type, add a new field with the new type and
keep the old one populated. Instead of renaming a field, return both names
for one release cycle. Instead of making a parameter required, keep it
optional and apply a server-side default. Instead of deleting an endpoint,
mark it deprecated and leave it working.

The rule of thumb: **add, do not modify; deprecate, do not delete.**

---

## Automate the check

The reason breaking changes reach production is not that teams do not care.
It is that the diff between two specifications is large and mostly noise,
so nobody reads it carefully every time.

Generating the specification from the code, then comparing it against the
previously released specification on every pull request, turns a question
of discipline into a build step. A pull request that introduces a BREAKING
finding without a MAJOR version bump should fail the pipeline.