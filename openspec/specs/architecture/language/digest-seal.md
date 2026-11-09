# Digest seal

## Overview

A digest seal is a seal that holds the digest of some data, written `{d}`. The event that carries it is signed, so the seal fixes the data at that point of the [KEL](kel.md) without putting the data in it; an event that carries a digest seal of some data anchors that data. A digest seal names no event, so it approves no delegation, which takes a [key event seal](key-event-seal.md).

**Example:** Erin's rotation 1 carries `{"d": "E-device"}`, the SAID of her device AID's inception; the inception stays waiting for its delegator's approval.
