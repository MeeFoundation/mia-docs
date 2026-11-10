# KEL

## Overview

A KEL, a key event log, is the signed, hash-chained sequence of an [AID](aid.md)'s key events: an inception, then rotations, and interaction events where the AID's configuration allows them. Each event names the SAID of the one before it, so a KEL is read from its first event, and folding it gives the AID's [key state](key-state.md).

**Example:** Alice's KEL holds her inception at sequence number 0 and rotations 1 to 4; rotation 3 names rotation 2's SAID as its prior digest.
