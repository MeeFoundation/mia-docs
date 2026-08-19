## 1. Storage in the data layer

- [x] 1.1 Make the storage configuration a required field of `SpawnOptions`: memory by name, or a directory (D1). Thread it through every spawn entry, remove the unset form, and update the spawn helpers so the workspace's suites name memory explicitly.
- [x] 1.2 Provision the directory at spawn: create it with owner-only permissions when absent, checking the permissions of what was created as 1.4 does for the key, and lay it out as `docs/` for the fork's replica store and its persisted author, `blobs/` for payloads, `node.key` for the endpoint key (D2). Name the layout in the crate docs — a person looking at a volume should be able to tell what they are looking at.
- [x] 1.3 Build the replica store with `Docs::persistent(<dir>/docs)` and the blob store with the filesystem store on `<dir>/blobs` when a directory is configured, keeping the in-memory pair otherwise. Nothing else in the assembly changes: the same access provider, validator and observer are installed either way, which is the property that makes this cheap.
- [x] 1.4 Read or generate the endpoint's secret key in `bind_endpoint`: read `node.key` when it is there, otherwise generate one and write it with owner-only permissions, creating the file exclusively so two starts cannot mint different keys onto one directory. Check the permissions of what was written, not only that the file exists. Write the key beside and rename it over, so no half-written key can exist; a key file that cannot be parsed stops the start with an error naming it — never a regenerated key — with a test that truncates the file and asserts the refusal.
- [x] 1.5 Take the node's author from the fork's persisted default author instead of minting one per store (D3): the private metadata store, the connection metadata store and the runtime's writer author all take the same one. Delete the per-store author minting rather than leaving it beside the new path.
- [x] 1.6 Prove the author decision is not vacuous with two tests that fail without it: a path written, the node restarted, the path written again, asserting the replica holds one live record; and a device withdrawn from a device set, the node restarted, asserting the withdrawn device is still absent when the set is read.
- [x] 1.7 Refuse a second node on a directory another running node holds, with an error naming the directory and the cause (D7). Check that the running node is unaffected by the refused start — the point of the check is that the refusal is not a lock error that reads as corruption.
- [x] 1.8 Update `SyncNode`'s docs where they state storage is in memory, so the contract and the code agree.
- [x] 1.9 Verify against the fork that an entry never reads as stored while its payload is absent — the readable order is payload first, entry last — so a stop between the two leaves an unreadable entry, not a stored entry whose payload never landed. If the fork commits the entry first, record it as a finding of this change (D11) rather than working around it. Verify in the same pass that the blob store makes an acknowledged payload durable at the acknowledgement rather than at a later flush — an ack that outruns the disk is the same kind of finding, and its fix lives in the write path, not in shutdown.

## 2. Opening a store the node already holds

- [x] 2.1 Add the constructor recovery needs to `PrivateMetadataStore`: open on a namespace the node already holds, without a ticket and without creating anything. `create` and `import` are the two that exist, and neither describes a replica that is already here.
- [x] 2.2 Check that importing a ticket for a replica the store already holds is idempotent — recovery re-imports the identity's own data namespace from the directory's `data` ticket, and the binder re-imports granted namespaces. If it is not idempotent, that is where recovery has to be shaped around it, and the finding belongs in the design rather than in a workaround.
- [x] 2.3 Test the round trip at the data-layer level: write entries into a directory and a data namespace, shut the node down, spawn one on the same directory, open both, and read the entries with their payloads — with no peer running, so nothing can have arrived over the network.

## 3. The hosted-identities record and recovery

- [x] 3.1 Write the record in the runtime's directory when an identity is created and when a link completes, holding the `PdnId` and its directory namespace and nothing else (D4). Write it after provisioning and before hosting, and remove the line when hosting ends (D5). Replace the file whole on every change — written beside, renamed over — never editing it in place.
- [x] 3.2 Recover at spawn: read the record, and for each line open the directory, register it for session classification, insert the hosted entry, and start the connection armer — the same tail `create` runs after provisioning. Recovery performs no dialogue and dials no peer.
- [x] 3.3 Bring the identity's data namespace back from the directory's `data` ticket on the same path, so a read addressed to the identity resolves after recovery.
- [x] 3.4 Fail the start when the record cannot be read or parsed, naming the file; treat an absent record as a first start. A start that hosts nothing while looking healthy is the outcome this refuses.
- [x] 3.5 Test recovery at the runtime level: an identity created, an entry written, the runtime shut down, a runtime spawned on the same directory — the identity hosted, the entry readable, and the node id unchanged. Break the record deliberately (remove the line) and confirm the identity is not hosted and reads are refused as not hosted, so the test is not passing on something else.
- [x] 3.6 Test the several-identities case: two identities with a connection each, restarted, each hosting its own and listing its own connections only.
- [x] 3.7 Test that an interrupted provisioning hosts nothing: a runtime whose record was not written for a provisioned store set hosts no identity from it after a restart.
- [x] 3.8 Test the record writer at its edges: an injected failure during replacement — a full disk above all — fails the operation and leaves the previous record intact, so a second identity's failed create keeps the first hosted; assert the writer never edits the file in place.

## 4. Connections, grants, and what an outage does to them

- [x] 4.1 Check that the connection armer's first sweep after recovery opens each pair from the directory's published tickets, and that `own_store_toward` finds the own replica through the directory rather than creating a second one — a restart that split the own replica would be this change's own defect.
- [x] 4.2 Check that the grant binder's first sweep after recovery imports what the counterparty's replica grants, and that the binding it records is the one a later withdrawal removes.
- [x] 4.3 Test the withdrawal during an outage: a grant live, the audience's runtime stopped, the grant withdrawn, the runtime started and reconnected — the namespace stops being readable and its issuer resolves to nothing. Pair it with the re-grant over the same claim afterwards, which must import again with no ceremony.
- [x] 4.4 Test that a replica no live grant explains is never served after a restart: reads refused, sessions refusing, whatever bytes remain on the disk. This is the fail-closed half of D6 and the only one this change asserts.

## 5. The host and the image

- [x] 5.1 Read `PDN_DATA_DIR` in the host beside the variables it already reads, and pass it into the runtime spawn. Exit with an error naming the variable when it is unset — the host offers no in-memory mode.
- [x] 5.2 Exit with an error naming the directory when the runtime cannot use it, serving neither liveness nor the debug surface — never falling back to memory.
- [x] 5.3 Set `PDN_DATA_DIR` in the image to its state directory and make that directory writable by the non-root user the binary runs as; declare no volume in the image (D9). Check that a container started with nothing mounted over that directory provisions it and serves.
- [x] 5.4 Update the host crate's docs with the variable, what an unusable directory does, and that an unset variable stops the start.

## 6. The stand

- [x] 6.1 Give the harness a start operation for a stopped container, and re-read the published port after it — a stopped container's mapping is released and the port it comes back on is a different one, which may by then belong to another test's container (D8). Every URL handed out after a start comes from that read.
- [x] 6.2 Write the restart scenario: a node with an identity, a connection and a grant, stopped and started again — same node id, identity hosted, connection listed, grant readable, an entry written before the stop still readable, and no ceremony repeated.
- [x] 6.3 Put its denial in the same scenario: a node started from the same image on an empty state directory hosts nothing, lists nothing, and refuses reads addressed to the restarted node's identity.
- [x] 6.4 Assert the counterparty converges on an entry the restarted node writes after coming back, with no invite minted and no linking performed after the restart — the property that distinguishes a recovered connection from a re-established one.
- [x] 6.5 Replace the scenario stating a stopped node is never started again; keep the stopped-device scenario beside it, which asserts something else.
- [x] 6.6 Write the bounded-filesystem scenario: one node whose state directory is a size-bounded mount, entries written until the store refuses, asserting the refusal arrives as a failed request and that a read does not report the value as stored.
- [x] 6.7 Check the suite's timings after the move to a disk-backed store, and adjust the convergence budgets only if a measurement says to — a budget widened on suspicion hides the regression it was widened for.
- [x] 6.8 Add the kill arm to the restart scenario: the same node killed with no grace and started again, with the same assertions and no extra ones — same node id, identity hosted, connection listed, grant readable, an entry acknowledged before the kill readable (D8). Recovery that needs the polite stop is a defect of this change.
- [x] 6.9 Add the mid-stream kill: a writer streams entries and collects acknowledgements, the container is killed without grace mid-stream, and after the start every entry acknowledged before the kill reads back with its payload, while an unacknowledged one is absent or whole — never torn (D8). This scenario is a primary subject of 8.3's stress pass.

## 7. The demo

- [x] 7.1 Give each node in `compose.yml` a volume of its own, mounted over the image's state directory; the image's `PDN_DATA_DIR` needs no per-node override.
- [x] 7.2 Remove the volumes with the containers on every exit of the `demo` recipe, the failing one included, and check it by running a demo that fails part-way.
- [x] 7.3 Add the restart step to the narration: one node stopped and started again mid-show, its connection still standing, nothing established a second time.

## 8. Verification

- [x] 8.1 Run `just test` and confirm the workspace's suites are unchanged and no slower — they still run in memory, named at their spawn helpers, and a measurable slowdown means a directory leaked into a suite's spawn.
- [x] 8.2 Run `just test-docker` from a clean image and confirm the stand's suite passes, the new scenarios included.
- [x] 8.3 Stress the stand's suite and the runtime scenarios this change touches (`just hunt-stand`, `just stress` over the affected binaries), and diagnose any failure as a defect of this change rather than carrying it forward — per `code-practices/flaky-tests.md`, sized as that spec requires.
- [x] 8.4 Run `just precommit-check`.
- [x] 8.5 Record what the change costs: the suite's wall-clock time before and after, and the size of a demo node's directory after a full show.

## 9. Documentation and sweeps

- [x] 9.1 Update the crate docs that state storage is in memory — `data-layer`'s `CLAUDE.md` and `SyncNode`, `pdn-node`'s `CLAUDE.md` where hosting is described as per-process, and `pdn-node-http`'s `CLAUDE.md` for the new variable.
- [x] 9.2 Sweep `openspec/specs/**` for statements this change makes false — "storage is in memory", "a restarted node keeps no state", "takes a new node id" — since the main spec tree is not validated by the tool and a delta only covers what it names.
- [x] 9.3 Sweep the active changes for the same, and the workspace `README.md` if it describes the stand's state.
- [x] 9.4 Validate (`openspec validate disk-persistence --strict`) and archive once the scenarios are green.
