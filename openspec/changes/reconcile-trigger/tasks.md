# Tasks: reconcile-trigger

Scope: the live path for capability-scoped peers — a directed, content-free trigger on a covered write, coalesced per peer, best-effort, prompting a filtered reconciliation. Depends on subset-rbsr (filter, read capability, scoped-peers-outside-swarm). Correctness and confidentiality are subset-rbsr's.

## 1. Trigger

- [ ] 1.1 On a write, resolve the scoped peers whose capabilities cover the written claim (reusing subset-rbsr's capability / audience index) and send each a content-free trigger over its direct connection
- [ ] 1.2 Coalescing: consecutive covered writes collapse into one pending trigger per peer until that peer reconciles; a missed trigger is left to reconciliation-on-contact
- [ ] 1.3 A triggered peer runs a capability-filtered reconciliation and receives exactly the covered claims

## 2. Transport & policy

- [ ] 2.1 Choose the transport (docs ALPN frame vs dedicated protocol) and the retry policy (how long before giving up to reconciliation-on-contact) — the design open questions

## 3. Tests

- [ ] 3.1 Worked-example scenario (one issuer, many claims, scoped peers): an unshared write triggers no scoped peer; a covered write triggers exactly the covering peer, which fetches it through filtered reconciliation; nothing reaches scoped peers over gossip
- [ ] 3.2 Coalescing: a burst of covered writes leaves one pending trigger per peer until it reconciles
- [ ] 3.3 Flake check on the new scenarios; lints + full suite (`just precommit-check`)

## 4. Docs & archive

- [ ] 4.1 On archive: place `data-layer-reconcile-trigger` into `components/mee-pdn/data-layer/`
