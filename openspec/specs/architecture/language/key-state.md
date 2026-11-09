# Key state

## Overview

Key state is what an [AID](aid.md)'s [KEL](kel.md) says after its latest accepted event: the current keys and their threshold, the digests of the next keys and their threshold, the [witness](witness.md) list and its threshold, the configuration traits, and the delegator of a delegated AID. A validator reaches it by folding the KEL event by event, and the same events always fold to the same key state.

**Example:** After Alice's rotation 4 her key state lists her laptop's and her phone's keys under the threshold `["1/2","1/2"]`, three next-key digests under `["1/2","1/2","1"]`, and W-home as her one witness.
