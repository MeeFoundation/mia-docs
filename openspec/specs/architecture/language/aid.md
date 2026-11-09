# AID

## Overview

An AID, KERI's autonomic identifier, is a self-certifying identifier bound to a [KEL](kel.md): either a basic prefix, which is the AID's one public key, or a self-addressing prefix, which is the SAID of the AID's inception event. Whoever can show the KEL proves control of the AID without asking any server, and the AID stays the same while the keys its KEL sets rotate.

**Example:** Alice's identity is the AID `EGgAfJDEPspRGYoC3NDQshV6tZ71usB01v-HKPYqY3uB`, the SAID of her inception; her phone's key `1AAJAsRjb5eK…` signs that inception and is replaced at her next rotation, and her AID is not.
