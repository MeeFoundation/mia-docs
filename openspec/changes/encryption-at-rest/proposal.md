# Proposal: encryption-at-rest

## Why

Everything a node keeps lies in its storage directory in the clear. The data layer says as much where it creates the directory: the replica store holds namespace secrets and the blob store holds payload bytes in the clear, so the boundary sits on the directory, readable by its owner alone (`DIR_MODE` in its `src/node.rs`). An identity's replica store holds the secret of every pod store it writes to, its authors' secret keys and its PMS, and the PMS holds the identity key pair; the blob store holds every payload of every record of every pod the identity belongs to; `node.key` is the endpoint's secret key.

That boundary stops another user of the machine and nothing that runs as its owner. A data stealer — malware that runs as the logged-in user and copies application data directories and credential stores wholesale, browser profiles, messenger sessions and wallets among them, and sends them off within seconds — reads the directory like the node does. Full-disk encryption does not stop it either: FileVault, BitLocker and the file-based encryption of a phone protect a device that is off or locked, and a stealer runs in a session that is unlocked.

The platform puts more in that directory than a client of a central service keeps. Decentralization means a person's device is the server: each of their devices holds a full replica of every pod they belong to and the keys that write to it. Encryption on the wire protects what crosses the network, and keeping data on the person's own devices protects it from a provider; a copied directory undoes both at once, since the data leaves through the file system rather than the network, and the copy writes as the person until the identity's keys change. Encryption at rest therefore comes, on every platform the node runs on, so that what a stealer copies is ciphertext and the key is not in the copy.

**Example:** Alice's laptop a1 hosts Alice-work, a member of "Family" and "Office"; a stealer running as Alice copies the node's directory.

| what the copy holds | today | encrypted at rest, the key in the platform's keystore |
|---|---|---|
| `identities/<Alice-work>/docs.redb` | both pods' store secrets, Alice-work's authors' secret keys, the PMS with the identity key pair | ciphertext |
| `blobs/data/<hash>.data` | every payload of both pods: files, claims, the operations of every note | ciphertext |
| `node.key` | the secret that lets a node answer as a1 | ciphertext |
| what the stealer can do with the copy | read everything both pods hold, and write to both pods and to Alice-work's PMS as Alice-work | nothing, without the key from a1's keystore |

## What Changes

Encryption at rest is decided; nothing about how is. The change settles where the key lives and how each store is encrypted, and then specifies and builds the answer. A direction is fixed already:

- Each store is encrypted on its own rather than inside one container, so a store is read as it is read today and no container has to be opened whole: the replica stores page by page, the blob store's payloads file by file, the small files whole.
- The key lives in the platform's keystore and never in the directory, which holds at most the key wrapped by it.

A payload's bytes move in pieces through the whole stack — a payload is imported into the blob store from a stream and read from it with a reader, sync serves and fetches it in ranges of 16 KiB chunk groups, and a partial download writes at offsets — and encryption keeps every one of those paths working in pieces:

- A blob's file is encrypted in segments, each authenticated on its own and readable without the others, aligned with the chunk groups sync reads and writes, so a range costs what it costs today and memory stays flat whatever the payload's size. A tag of 16 bytes per segment of 16 KiB is 0.1% of the file.
- An import encrypts as it writes, its temp file included: an import cut short leaves ciphertext, which the next start removes as it removes such files today (iroh-blobs-010).
- A reader decrypts one segment at a time, and nothing decrypted is written outside the stores: a host shows a file from a reader, never from a decrypted copy in a cache. A download is the person's own act, written where the person chose.

## Out of Scope

- What members see of each other's payloads: every member reads every record of a pod by design, and encrypting payloads between members is another change.
- A stealer that drives the running application or reads its memory: encryption at rest keeps the copy of a directory closed, and does nothing for a session the stealer controls.
- Rotating an identity's keys after a copy has leaked: the identity work owns it.

## Open Questions

### Where the key lives, platform by platform

On macOS and iOS a keychain item bound to the application's code signature, which another application reaches only through a prompt the person answers; on Android a key in the Android Keystore that never leaves it and wraps the store key. On Windows and Linux the user's own keystore — DPAPI, the Secret Service — answers any process of that user, so a stealer running as the user can ask it as the node does; what those platforms offer beyond it is open. On a phone the sandbox already keeps other applications out of the directory, so the desktops are where a stealer reads it.

**Example:** a stealer running as Alice on each of her devices.

| device | what it gets of the key |
|---|---|
| a1, a Mac | a keychain prompt Alice has to answer |
| a2, an Android phone | nothing: the key never leaves the Keystore, and the directory is outside the stealer's sandbox |
| a3, a Windows laptop | the key, through DPAPI, unless the platform offers more |

### What a device that lost its key does

A keystore wiped by a reset or a new login leaves the directory unreadable. Every record a device holds is held by the pods' other devices too, and every PMS entry by the identity's other devices, so the device can start over: linked again, it catches up. What it loses is what reached no other device before the key went.

**Example:** a1's keychain is reset after Alice placed a claim that a1's sessions had not yet carried anywhere.

| option | what a1 has afterwards |
|---|---|
| start over and link again | every pod's records but the one claim |
| keep a recovery copy of the key outside the keystore | everything, and a copy of the key a stealer can look for |

### One key per node or one per identity

Several identities on one node share its directory. One key per identity lets one stay closed while another is open — Alice-work's pods locked while Alice-leisure syncs — at the cost of a key and an unlock for each.

**Example:** a3 hosts Alice-work and Alice-leisure, and Alice opens only Alice-leisure on a Saturday.

| option | what a3 can read that Saturday |
|---|---|
| one key per node | both identities' stores |
| one key per identity | Alice-leisure's stores alone |

### Whether a blob file's name keeps the content hash

The hash of a payload is what members agree on, and it stays over the plaintext. A file named by it tells a thief who holds the same content which contents a device holds; a name derived from the hash with a key hides that, and costs a lookup at every read.

**Example:** a thief holding a leaked document checks a copied directory.

| option | what the thief learns |
|---|---|
| `blobs/data/<hash>.data` | that a1 holds the document |
| a name derived with a key | nothing from the names |

### When the node may run

A key the platform releases only while the device is unlocked keeps a stolen phone closed and stops sync while it is locked; one released after the first unlock lets it sync in a pocket and is readable by whatever runs after that first unlock.

**Example:** Bob's phone b1 in his pocket, locked, while Carol places a file in "Family".

| option | b1 |
|---|---|
| the key while unlocked alone | fetches the file once Bob unlocks |
| the key from the first unlock on | fetches the file in his pocket |
