# Identity key

## Overview

The identity key is the key pair an identity is created with: one per identity, minted on its first device and carried by the identity's [private metadata store](../../components/mee-pdn/data-layer/private-metadata-store/spec.md) to every device linked into it, so every device of the identity holds the same pair. The identity's `PdnId` derives from the public key, and a signature under the key proves that `PdnId` is the signer's own.

The identity signs with it what has to count as the identity's own word wherever it is read. In a [pod](pod.md) that is the created event of a pod it creates, whose pod id derives from the same key; its join statement when it joins; and every version of its device statement, the list of its devices. A device signs what it writes as a device with keys of its own — its node id, the author it writes with — so the identity key belongs to the identity, never to one of its devices.

**Example:** Alice is created on her phone a1, and her laptop a2 is linked into her. a1 mints her identity key and derives her `PdnId` from its public key; a2 takes the same pair from her PMS, and the device statement a2 writes in the pod "Family", listing itself, verifies under that key.

The key does not rotate, so losing it would rename the identity. [ADR-0003](../adr/0003-mee-identity-represents-keri-autonomic-namespace.md) records the direction that replaces it: a KERI autonomic identifier derived from an inception key, which the `PdnId` then names while the keys the identity signs with rotate.
