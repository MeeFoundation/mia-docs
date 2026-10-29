## 1. The pending set

- [x] 1.1 `PendingInvites` in pdn-node's `src/ceremony.rs` keeps an entry's state beside what it was minted for: `verify_and_burn` marks a live entry burned and leaves an expired or presented one as it is, `mint` sweeps every entry whose lifetime ended, a call marks a burned entry used by its newcomer, and a read answers `InviteState` (D1, D5); unit tests in the same file cover pending, burned, used, expired, swept and a refused presentation, and fail with the entry removed at the burn as before

## 2. The serving halves and the service calls

- [x] 2.1 `serve` in `src/linking.rs` marks the invite used by the connection's peer once the reply and its finish returned (D2); `linking_invite_state` on the identity service answers from `pending_linking_invites` for the identity the payload names (D3, D4)
- [x] 2.2 `serve_join` in `src/pods.rs` marks the invite used by `request.joiner` once the tickets' write returned, on both paths — the joined event and the device statement of a member already listed — and over the in-process pipe as over the network (D2); `invite_state` on the pods service refuses an unhosted identity and answers from `pending_pod_invites` for the identity and the pod (D3, D4)
- [x] 2.3 `InviteState` exported from pdn-node beside `PodInvite` and `LinkingPayload`, its docs one contract line each; `just check` green

## 3. Scenario tests in pdn-node

- [x] 3.1 pods "A served join marks the invite used by the joiner": two invites minted, a join with the first from another runtime, the first read pending before and used by the joiner after, the second pending throughout, in `tests/pods.rs`; fails with the mark in `serve_join` removed
- [x] 3.2 pods "A join cut short after the burn leaves the invite burned": `fail_next_joined_write_for_test`, the invite read burned, then a second invite joined and read used; fails with used marked at the burn
- [x] 3.3 pods "A refused presentation leaves a pending invite pending": a never-minted secret presented, the pending invite read pending and the dialer's unknown, beside the existing wrong-secret scenario
- [x] 3.4 pods "A member whose join lost the reply is named by the second invite": `drop_next_join_reply_for_test`, the first invite burned and the second used by C, on the existing lost-reply scenario
- [x] 3.5 pods "Between two identities of one node the invite is answered for its own identity alone": the in-process join, the inviter reading used by the co-located identity and the co-located one reading unknown, and an unhosted identity refused as unknown
- [x] 3.6 pods "An invite never presented reads expired after its lifetime" and "A restart forgets every invite's state": a lifetime of 1 second read expired after 2 seconds and unknown after a further mint; a used invite read unknown after the runtime stopped and started on its directory
- [x] 3.7 device-linking "A served linking marks the invite used by the newcomer": the invite read pending before and used by B's node id after, the id equal to the one A registered, in `tests/linking.rs`; fails with the mark in `serve` removed
- [x] 3.8 device-linking "A linking cut short after the burn leaves the invite burned" and "A refused linking presentation leaves a pending invite pending": `fail_next_pending_device_write_for_test`, and a never-minted secret presented beside a pending invite
- [x] 3.9 device-linking "A linking invite never presented reads expired after its lifetime" and "A restart forgets every linking invite's state", as 3.6

## 4. The hosts

- [x] 4.1 pdn-node-http: `POST /debug/identities/{identity}/pods/invite-state` with the invite as the join route takes it, and `POST /debug/linking-invite-state` with the payload as the link route takes it, each answering the state as JSON from one service call; the parsers' and the error table's unit tests in `src/` cover the bodies
- [x] 4.2 pdn-node-http "An invite's state is read over HTTP": a container test in `tests/stand_pods.rs` minting a pod invite and a linking invite on one host, consuming each on a second, and reading each pending before and used after; run with `just test-docker`
- [x] 4.3 pdn-mobile: `pod_invite_state(identity, code)` and `linking_payload_state(code)` and the exported `InviteState` enum (D6), a code decoded as its consuming call decodes it; a facade test in `tests/surface.rs` reads a pod invite and a linking payload pending, then used once consumed through a second handle, and a code of the wrong kind refused as malformed
- [x] 4.4 The delta of `mobile-host-surface` at `components/mee-pdn/pdn-mobile/host`: the two calls among the operations the facade covers and in its exact exported set, and a requirement of their own with an example and the scenarios 4.3 proves

## 5. Docs

- [x] 5.1 The `CLAUDE.md` of `crates/pdn-node`, `crates/pdn-node-http` and `crates/pdn-mobile`, where they list the services' or the surface's calls
- [x] 5.2 At archive: `invite_state` in the service listing of `components/mee-pdn/pdn-node/pods/spec.md`, which no delta reaches

## 6. Gates

- [x] 6.1 `just check` and `just test` green
- [x] 6.2 Stress pass per `specs/code-practices/flaky-tests.md` on the linking and join scenarios of `tests/linking.rs` and `tests/pods.rs`, the new ones among them: 100 iterations, no failure
- [x] 6.3 `openspec validate --all --strict` and `python3 -I scripts/check-docs.py` before archiving
