# Key event seal

## Overview

A key event seal is a seal that names an event of another [KEL](kel.md) by its [AID](aid.md), its sequence number and its SAID, written `{i, s, d}`. An event that carries it approves or endorses that event; KERI approves a delegated event this way, by a key event seal in an accepted event of the delegator's KEL. It differs from a [digest seal](digest-seal.md), which names data by its digest alone and approves nothing.

**Example:** Rotation 1 of Alice's KEL carries `{"i": "E-phone", "s": "0", "d": "E-phone"}`, and so approves the inception of her phone's device AID.
