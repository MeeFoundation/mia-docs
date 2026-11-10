# Witness

## Overview

A witness is a server that [receipts](receipt.md) an [AID](aid.md)'s events, signing for each one that it has seen it, and receipts only the first event it sees at each position. An establishment event lists the AID's witnesses and how many receipts make an event accepted; a rotation changes the list by cutting and adding witnesses, and its own receipts come from the list after those changes. A witness's prefix is its key, so a validator checks its receipt without asking it.

**Example:** Alice's rotation 4 cuts W-tellipod and adds W-home under witness threshold 1: W-home's receipt makes it accepted, and W-tellipod's alone does not.
