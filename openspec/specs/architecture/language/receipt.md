# Receipt

## Overview

A receipt is a [witness](witness.md)'s signature over an event, attached to the event as an indexed signature into the witness list the event falls under, or carried as a receipt couple of the witness's prefix and its signature. An event of a witnessed [KEL](kel.md) is accepted once enough of its witnesses' receipts are attached.

**Example:** Alice's inception lists W-tellipod under witness threshold 1, and is accepted with W-tellipod's indexed signature at index 0 attached; without it, it waits for receipts.
