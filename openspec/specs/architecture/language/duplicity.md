# Duplicity

## Overview

Duplicity is KERI's name for two different events at one position of one [KEL](kel.md), both validly signed, and KERI treats it as the mark of a compromised key. A validator keeps the event it accepted first; without superseding recovery, no event replaces an accepted one. Until the second event's signatures are checked against the key state at its position, the validator can call it only likely duplicitous, as keripy does: anyone can send an unsigned event to a taken position.

**Example:** Alice's rotation 4 is accepted, and a rival rotation 4 that adds W-rival instead arrives later. The validator answers that the rival is likely duplicitous, and her key state stays the one rotation 4 set; once the rival's signatures verify under the keys her rotation 3 committed to, the two rotations are duplicity.
