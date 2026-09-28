# Proposal: cells-mergeable-document-merge

## Why

A cell stores a mergeable-document as its operations: every edit is an entry of its own at `by/<pdnid>/mergeable-document/<id>/<op>`, `<op>` naming the writer's author key, the writer's membership sequence and the writer's own operation sequence, so two writers' operations never share a key ([cell stores](../../specs/components/mee-pdn/data-layer/cell-store/spec.md)). The platform admits the operations of every member, holds them, reconciles and relays them whole among member devices, and hands them back through the cells service's `read_ops`, each with its writer, as opaque bytes ([pdn-node cells](../../specs/components/mee-pdn/pdn-node/cells/spec.md)). What a document reads as — its operations merged into one state — nothing computes: no operation encoding is defined, and neither the platform nor a host merges. Storage, sync and admission are what load testing needs; a person editing a note needs the document.

**Example:** Bob, on his phone b1, and Carol, on her phone c1, disconnected from each other, edit the shopping list under Alice's name, which reads "milk".

| | on every member device once they sync |
|---|---|
| Bob replaces "milk" with "oat milk" | an entry naming b1's author, Bob's sequence 1 and b1's operation 4 |
| Carol removes the line "milk" | an entry naming c1's author, Carol's sequence 1 and c1's operation 2 |
| `read_ops` | both entries, each with its writer, as opaque bytes |
| what the list reads as | computed by nothing: "oat milk", an empty list and both lines are each a merge some rule could choose |

## What Changes

The change settles how a mergeable-document's operations become one document — the merge, the encoding of an operation, where the merge runs, what keeps a document's history from growing without end, and what an editor shows of concurrent edits — and then specifies and builds the answer. Nothing is decided; the options stand under Open Questions, strongest first. The storage, the admission and the reconciliation of operations stay as they are.

## Open Questions

### Which merge serves which content

A mergeable-document is a markdown note or a rich text held as a JSON tree of text nodes, and each needs a merge that keeps both of two concurrent edits.

- An existing CRDT library that serves both a text and a tree — Automerge, Yjs through its Rust port yrs, or Loro — its license checked against the embeddable runtime, as the KERI libraries' were. Its change format becomes the operation encoding, and its wasm build decides whether the browser host merges too.
- A CRDT of the platform's own for text, and one for the tree. The encoding and the merge are ours to fit to the key layout, at the cost of building and proving a merge.

**Example:** Bob's and Carol's concurrent edits of Why, under each option.

| option | the list reads as | where the rule comes from |
|---|---|---|
| an existing library | "oat milk" on every device: Bob's edit removes "milk" and inserts "oat milk", both removals take the same letters, and a text type keeps a concurrent insertion | the library's documented semantics |
| a CRDT of our own | "oat milk", or both lines, or nothing, the same on every device | a rule this change writes and tests |

### Where the merge runs

- In pdn-layer: the cells service returns a document's state beside its operations, every host renders one document the same way, and pdn-layer learns the operation encoding, which below it stays opaque.
- In each host: the platform hands out operations, as `read_ops` does, and every host carries its own merge; two hosts built against different merges render one document differently.

**Example:** the mobile application and the HTTP host read the shopping list after Bob's and Carol's edits.

| option | the mobile application | the HTTP host |
|---|---|---|
| in pdn-layer | the state pdn-layer merged | the same state |
| in each host | its own merge of both operations | its own merge, which may read otherwise |

### What an operation carries beside its bytes

A key orders one writer's operations; a merge across writers needs the operations each edit saw.

- The dependencies in the payload, as a CRDT's change format carries them. The key layout stays, and a device merges once it holds a change's dependencies, which whole-store reconciliation brings.
- The dependencies read by the record view, which reads an operation only once the operations it depends on are held, as the membership fold counts an event only once what it rests on is held. A document is never merged over a gap, at the cost of a second reading of the payload below pdn-layer.

**Example:** Carol's removal of the line saw Bob's operation 3 and not his operation 4, and reaches Alice's laptop a2 before operation 3 does.

| option | a2 |
|---|---|
| dependencies in the payload | holds the removal; the merge waits for operation 3, or merges over the gap if it allows one |
| dependencies read by the record store | reads the removal only once operation 3 is held |

### What keeps a document's history bounded

Every operation is an entry for as long as the cell lives: no operation and no record leaves the store.

- A snapshot operation that folds the history below it, the operations it covers then removed: the record store gains a removal of operations, and who may write a snapshot of a document under another member's name is a question of the cell's rights.
- A new record that starts from the document's state: the platform stays as it is, links keep naming the old record, and the old record's history stays beside the new one for as long as records stay.
- None: a document's operations grow for as long as it lives.

**Example:** the shopping list after a year of daily edits by three members, about 5,000 operations.

| option | entries the record store holds for it |
|---|---|
| a snapshot operation | one snapshot and the operations written since |
| a new record from its state | the new record's operations since it was placed, beside the old record's 5,000 |
| none | about 5,000 |

### What an editor shows of concurrent edits

The rights table grants every member the edit of another member's mergeable-document with per-edit authorship preserved: each operation carries its writer. Whether an editor marks who wrote each part, shows a merged conflict as one text or as both versions, and lets a member undo another's edit is the product's; the change states what the platform hands the editor for it.

## Operating conditions

Several devices of one member edit one document while disconnected from each other: each writes under its own author, so their operations never share a key, and the merge has to take them as two writers. A member that left or was kicked keeps its operations from while it was a member in the document, and the merge takes them as any other. Clocks decide nothing: an entry's timestamp is set by its author, and the merge orders operations by what each saw. A restart loses nothing: operations are entries, and the merged state is derived from them.

## Out of Scope

- The storage, admission, reconciliation and relay of operations, which stay as the cell stores and the cells service specify them.
- A chat, whose stream of messages is a sync shape of its own.

## Capabilities

None is settled. Every option touches `components/mee-pdn/pdn-node/cells`, whose reading of a mergeable-document returns operations; a merge in pdn-layer adds a capability of pdn-layer, and a dependency read by the record store touches `components/mee-pdn/data-layer/cell-store`.

## Impact

- **`crates/pdn-layer`**: the operation encoding, and the merge if it runs there.
- **`crates/pdn-node`**: the reading of a mergeable-document.
- **The workspace's dependencies**: a CRDT library, if one is taken, under the license and supply-chain checks `cargo-deny` holds.
