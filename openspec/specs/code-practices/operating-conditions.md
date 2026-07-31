# Operating conditions: design for them, test where they bite

A scenario test runs in a world of one identity per node, devices that linked before anything happened, a network that never drops, a disk that never fills, a process that never restarts, and a capability granted once and never touched again. Every one of those is a simplification, and every one has a counterpart on a real device that the code will meet. The conditions below are that list — the circumstances a design has to survive, kept in one place so they are considered on purpose rather than remembered by luck.

This is not an instruction to multiply every test by every condition. The full product of them is unaffordable to write, unreadable afterwards, and mostly vacuous: for a given change, most conditions change nothing. The instruction is the other two steps — walk the list while designing, and where a condition genuinely changes the outcome, back that path with a requirement in the spec and a test that fails without it.

## The conditions

**Several identities on one node.** A node hosts the store sets of any number of identities, and co-location is not a trust boundary. The mistakes have a shape: a check that asks "is this our node" where it must ask "is this device one of *this identity's*", a set derived from the wrong identity's directory, a cache keyed by node where it must be keyed by identity. Two identities of the same person are as separate here as two strangers.

**One device, or several.** An identity may live on one device forever or on four, and nothing may assume a founder. Anything phrased as "the device that did X is the device that will do Y" is a defect waiting for the second device. Watch addressing in particular: a ticket names the device that minted it, so a set of contacts built from tickets alone quietly encodes "one device" inside what looks like a routing detail.

**A device links before, during, or after.** Linking is not a setup step that precedes the interesting part. A device can join before any connection exists, between the halves of a ceremony running on a sibling, or long after a grant was published, consumed, and forgotten about. Each arrival has to converge on the same state, and a device that arrives late must reach it by replication rather than by having been present.

**The connection is unstable.** A phone on 3G, a train tunnel, a lift. A dialogue can die between its halves, a sync session can stop mid-exchange, and a peer can vanish immediately after committing its own half of an act. Three consequences to design for: a caller must be able to tell "the peer refused me" from "I never reached the peer", a half-completed act must leave state a retry converges from rather than state a retry duplicates, and a timeout is never an answer — it is the absence of one.

**The disk fills.** The device is fast and modern; its free space is not, because the person filled it with photographs. A write then fails at the storage layer, and the requirement is that it fails *loudly*: an exhausted disk must not turn into a swallowed error, a replica reported as converged when its last transaction did not commit, or a record whose payload never landed being read as a record that was never written. Reporting the failure is the whole obligation — recovering space is not this system's job.

**The device restarts.** A reboot, an app update, a killed process — the node comes back, and only what the stores hold comes back with it. Every in-memory structure on top of them — a memo of what was imported, a registry of what is bound, any count of who holds what — is empty at startup and rebuilt gradually, sweep by sweep. Two consequences to design for. A decision that destroys durable state must be grounded in durable evidence: taken against half-rebuilt bookkeeping it undercounts, and destroys what a holder that has not swept yet still owns. And derived state must be recomputable — a mechanism that is only correct while its bookkeeping is complete breaks on the first restart. The world did not pause meanwhile: grants were withdrawn, devices revoked, tombstones written while the device was off, and that whole backlog arrives compressed on reconnect — onto exactly the half-rebuilt state above.

**Capabilities move.** A capability is granted, narrowed to fewer claims, widened again, revoked, and granted anew over the very same claim. Any state that means "we once had access" goes stale the moment it is revoked, and any state that remembers a revocation blocks the re-grant that follows it. The path worth testing is rarely the first grant: it is the second one, after a withdrawal, over the same claim — and the two directions of a change of scope, because narrowing and widening fail differently.

## How to use this

**Walk the list once, while designing.** Note which conditions change the outcome of the change at hand. For most changes the honest answer is "none of them", and writing that down is a result.

**Back the ones that bite.** A condition that changes the outcome earns two things: a requirement in the spec, phrased as a scenario, and a test that fails when the mechanism is removed. Everything else is a note in the design, not a test.

**Say what you left out.** A condition deliberately out of scope is written as out of scope, with the reason. An unmentioned condition reads as one nobody thought about, and the next person cannot tell the two apart.

**Compose with the neighbouring practices.** These conditions say which situations to put a test in; [access-control-tests](access-control-tests.md) says that each such test needs its tightest denial beside it; [flaky-tests](flaky-tests.md) governs what to do when a test built on one of them — unstable connection and late-arriving device especially — fails once in a while. A scenario that turns a device off and waits for convergence from another is exactly the shape in which timing defects hide.
