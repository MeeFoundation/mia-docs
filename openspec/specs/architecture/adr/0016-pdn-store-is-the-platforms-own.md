---
status: accepted
date: 2026-10-16
---
# pdn-store is the platform's own crate: it holds what the platform uses, and upstream is watched for fixes

## Context and Problem Statement

pdn-store is the workspace's variant of n0's `iroh-docs` ([ADR-0014](0014-store-sessions-judged-by-the-embedder.md)): the sessions the embedder judges, the dial controls a pod's pass uses, the rule that an entry affects only its own key. It starts from upstream's 0.101.0 release, and `crates/pdn-store/UPSTREAM.md` gives every upstream commit since a verdict, so that upstream's work can flow into it. The question is what relation to upstream the crate keeps, and what it keeps of upstream's code.

Facts about the crate and its upstream:

1. The platform calls a fraction of what upstream's release carries. Of the 27 requests its in-process API defines, the data layer sends 15; of its three feature sets and its two targets, the product builds one.
2. Of the six upstream commits after the 0.101.0 release, `UPSTREAM.md` records each as adapted by hand, not applicable, or already fixed in the crate. None applies as it is: the code each touches has diverged.
3. Several defects are fixed in the crate ahead of upstream, and two of those fixes are open pull requests against upstream.
4. Upstream and the crate still share the code at their core: the set reconciliation, the wire codec and the redb store file. A defect upstream finds there is likely a defect of the crate too.
5. Upstream has no access provider, no judgement of a session and no dial controls, so a design of upstream's for a new feature answers a question the crate asks only in part.

## Decision Drivers

* A reader of the crate — a reviewer, an agent adapting the engine, someone chasing a flaky test — meets only code the platform reaches.
* A fix upstream makes to the code both still share reaches the crate.
* Nothing in the crate is kept on the chance that an upstream patch will apply to it.
* A change that needs the store to do something new does not rediscover what upstream already designed.

## Considered Options

* **The platform's own crate, with a watch on upstream's fixes and a look at upstream for every new need** ← chosen
* **Track every upstream commit**
* **No watch on upstream at all**

## Decision Outcome

Chosen option: **the platform's own crate, with a watch on upstream's fixes and a look at upstream for every new need**, because it keeps every fix of the shared core within reach while the crate carries only what the platform uses.

**What the crate holds.** The crate holds what a crate of the workspace reaches, and nothing else: an item no other crate names and no test of kept behaviour uses goes, with the tests whose subject it is. It carries the workspace's version number, is never published, and keeps upstream's license files and authors, which the MIT and Apache licenses ask to keep with the code.

**A watch on fixes.** At every bump of iroh, iroh-blobs or iroh-gossip in the workspace, upstream's commits since the last pass and its open pull requests titled as fixes are read. Each one that touches code the crate still holds gets an entry with a verdict in `crates/pdn-store/UPSTREAM.md`, and a defect it confirms in the crate is fixed or recorded as a change of its own. One about code the crate no longer holds is recorded as not applicable in one line.

**A look per need.** A change that needs the store to do something new reads upstream's code and its open pull requests for an answer first, and its design says what it found.

**Example:** the next bump of iroh. Upstream's log from the last commit `UPSTREAM.md` records is read, with its open fix pull requests; a pull request bounding the in-memory public key cache, code the crate holds too, gets an entry with a verdict, while one fixing download policies, which the crate does not hold, gets the one line "not applicable".

### Consequences

* Good — the crate is what the platform runs: one configuration, a public surface that other crates name, and a compiler that reports crate-private code nothing calls.
* Good — a fix to the set reconciliation, the codec or the store file that upstream makes reaches the crate at the next bump of iroh.
* Bad — upstream's fixes reach the crate only through that watch: one that lands between two bumps waits for the next.
* Bad — a feature upstream adds to code the crate removed is ported by hand if the platform comes to need it.
* Neutral — the wire format and the store file stay upstream's, so a node of the crate and an upstream node still speak the same sync protocol.

## Validation

`crates/pdn-store/UPSTREAM.md` records each pass with its date and the newest upstream commit read, and a verdict for every commit and pull request it read. A bump of iroh, iroh-blobs or iroh-gossip without a pass newer than the bump's date in that file is a review finding.

## Pros and Cons of the Options

### The platform's own crate, with a watch and a look per need (chosen)

* Good — only reachable code to read and to test.
* Good — the shared core's fixes still arrive.
* Bad — a feature upstream holds and the crate removed returns only by hand.

### Track every upstream commit

* Good — nothing upstream does goes unread.
* Bad — most entries are about code the crate does not hold or holds diverged, so the reading buys a verdict of "not applicable" or "adapted by hand" at every commit.
* Bad — code kept so that patches might apply holds the crate at upstream's size, which every reader of the crate pays for.

### No watch on upstream at all

* Good — no reading at all.
* Bad — a fix upstream makes to the set reconciliation, the codec or the store file, which both still share, never reaches the crate.

## More Information

The crate's guidance, `crates/pdn-store/CLAUDE.md`, lists each rule the crate's behaviour follows with its reason; what a session serves and admits is specified in [reconciliation sessions](../../components/mee-pdn/data-layer/reconciliation-sessions/spec.md), and the crate's own place in the workspace in [pdn-store crate](../../components/mee-pdn/pdn-store/crate/spec.md).

Related: [ADR-0014](0014-store-sessions-judged-by-the-embedder.md) (why the crate is a variant of iroh-docs at all).

External references: n0's `iroh-docs`, <https://github.com/n0-computer/iroh-docs>, branch `main`.
