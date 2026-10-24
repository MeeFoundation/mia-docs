# Resource release: every path out lets go

A resource is anything a process holds that the operating system or a peer counts against a limit: an open file, a socket or an HTTP connection, a child process, a store or database handle, a lock file, a thread or a task that holds any of these, and a temporary file left on disk. Code that opens or starts one is checked twice, once by its author and once in review, on one question: does every path out of the operation let it go, the failed paths as well as the successful one.

The check is owed because a missing release rarely fails where it happens. It fails later and elsewhere, as an unrelated operation that cannot get a resource of its own, and the numbers or the behaviour around it go quietly wrong before anything raises.

## What to check

- **Every exit between the open and the hand-over.** A resource is safe once something that releases it owns it: a `with` block, a `Drop`, a guard, a list whose owner stops what it lists. Between the open and that hand-over, every early return, every `?`, every raise, a panic, a dropped future and a signal is an exit, and each one either releases the resource or leaves it held for the rest of the process. The usual gap is a fallible step placed between starting something and registering it with its owner; the fix is to register first, or to release in the failure branch.
- **An owner that outlives the operation.** A resource put in a struct field, a map entry or a detached task lives as long as that owner. Ask who removes it, and whether a failed operation can leave it there with nobody left to remove it. A task that holds a strong reference and waits for something only the release would end never ends; the store's `Doc` holds its engine weakly, so a task holding a `Doc` does not keep a stopped engine alive.
- **A release that has to be explicit.** Rust closes a file on drop, but some resources need an ordered, asynchronous close: iroh's `Endpoint::close`, the blob store's `shutdown`, an engine's `shutdown`. Dropping them instead aborts the endpoint and the engine's actor rather than stopping them in order, or lets go of files later than the next open expects: on macOS a blob store that failed to start keeps its files open for a moment after the drop, and `test_default_author_persist` in pdn-store's `tests/client.rs` waits for it.
- **Counts that grow with the workload.** A handle per peer, per node, per request or per record is harmless at 4 and fails at 100. Multiply the count per unit by the largest size the code advertises, and compare the result with the open-file limit of the machines it runs on: macOS gives a process started from a terminal 256 open files by default (`launchctl limit maxfiles`). A process that needs more raises its own soft limit at start, or refuses to start and says why.
- **Exhaustion reported where it happens.** An operation that cannot get a resource reports the failure and counts it where a reader sees it. It does not end a helper thread silently, and it does not turn into a zero or an "ok" further down.
- **Scripts.** Python opens a file in a `with` block and closes a connection in a `finally`. A child process is stopped by whoever started it, including when the start itself fails halfway. A shell script removes its temporary files in a trap set for INT, TERM and HUP as well as EXIT, because dash runs no EXIT trap on a signal it has no trap for.

## When a leak is fixed

In the product a leak is a defect in behaviour, and [defect-reachability](defect-reachability.md) decides whether its fix is obliged: a resource that a host can make the runtime hold for good, through the public surface of `pdn-node` under some operating condition, is fixed. In a test, a scenario harness or the load test, a leak is fixed whenever it can change a result, because a run that exhausts a resource measures the harness instead of the platform.

## Worked example

A ramp of 100 nodes on a laptop shows what an unchecked count costs. The load test's coordinator holds, for every node, the node's event stream and the file that stream is written to, which makes 200 open files, and during a step it holds one connection per writer. With 99 writers and a step of 100 records, each writer places one record and closes its connection at once. From the first step of 500 records, each writer places about 5, spread over 25 seconds, and keeps its connection open all that time:

| Step | Records in the step | Records per writer | Files open at once | Outcome at a limit of 256 |
|---|---|---|---|---|
| the first five, to 500 held | 100 | 1 | about 200, plus a few | every write placed |
| the next, to 1,000 held | 500 | about 5 | about 200, plus 99 | 188 writes refused, the CPU sampler's thread gone |

Unchecked, every number after that goes wrong without a raise. The operating system's too-many-open-files error (`EMFILE`) ends the CPU sampler's thread on the first `ps` it cannot spawn, and within two rows the table reads 0% host load and no CPU per record. The refused writes show only in a CSV column the printed table leaves out, so the row says `ok`. The rule that ends a ramp at ten refusals in a row never fires, because a writer has about 5 records in a step and a count kept per step starts again with each one. One more release is missing on a failure path: a node whose join raises is not yet listed in its pod, so the pod's stop never reaches it, and it runs through the next N. `sync-test/load.py` raises its open-file limit to what the run needs before the first node starts, keeps its sampler alive through a failed sample, names refused writes in the printed row, counts refusals in a row across steps, and lists a node in its pod before the node joins.
