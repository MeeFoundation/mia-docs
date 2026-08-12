# KERI wire profile

The byte-level interoperability contract for KERI events, stored `KEL1` containers, linking transcripts, replicated proofs, and `/pdn/linking/1` frames. This capability deliberately fixes every identity-affecting preimage and every stored-or-streamed event bound rather than delegating protocol bytes to an implementation library or another component.

## ADDED Requirements

### Requirement: Profile version 1 fixes the KERI event bytes

Protocol profile `1` SHALL use KERI `1.0` with JSON serialization. The normative event bytes are UTF-8 compact JSON with no insignificant whitespace and with fields emitted in this exact order:

- `icp`: `v,t,d,i,s,kt,k,nt,n,bt,b,c,a`;
- `dip`: `v,t,d,i,s,kt,k,nt,n,bt,b,c,a,di`;
- `ixn`: `v,t,d,i,s,p,a`.

The `v` field SHALL be the KERI 1.0 JSON version string whose 6 lowercase hexadecimal size digits count the complete event bytes. A sequence number SHALL be in `0..=u64::MAX` and encoded as canonical lowercase hexadecimal without a prefix: exactly `"0"` for zero and otherwise 1 through 16 digits with no leading zero. An input longer than 16 hexadecimal digits SHALL be rejected before numeric conversion. Each identifier SHALL have exactly 1 transferable Ed25519 current key (`D` derivation code), signing threshold `"1"`, exactly 1 BLAKE3-256 next-key digest (`E` code), next threshold `"1"`, witness threshold `"0"`, no witnesses, and no configuration traits. The next-key digest preimage SHALL be the exact 44 ASCII bytes of the next transferable public key's CESR-qualified `D...` value, not its 32 raw Ed25519 key bytes; the 32-byte BLAKE3-256 result SHALL be encoded with CESR code `E`. Event SAIDs and self-addressing AIDs SHALL use BLAKE3-256 and CESR code `E`. A delegated inception SHALL carry only `di`; it SHALL NOT carry a delegating-location seal. Its `a` list SHALL be empty. An anchoring `ixn` SHALL contain exactly 1 event seal with fields in `i,s,d` order.

Every event signature SHALL be an indexed Ed25519 signature at index `0` over the exact event bytes, encoded with CESR code `A`. In this fixed subset, qualified qb64 encoding SHALL be unpadded base64url over the complete CESR prepad plus raw material: `D = base64url(0x0c || public-key[32])`, `E = base64url(0x10 || digest[32])`, and index-0 `A = base64url(0x00 || 0x00 || signature[64])`. Decoding SHALL base64url-decode the whole qualified string, require and remove those exact prepad bytes, and then require the raw length; stripping the visible `D`, `E`, or `AA` characters before base64 decoding is invalid. A stored or streamed signed event SHALL retain those exact event bytes and signature bytes; parsing and reserialization SHALL NOT create the bytes that are verified. `keripy` `v1.0.0`, commit `6478fee8688a0a3e978827d5327f8fd05e3d3737`, is the compatibility oracle for this profile. The rules and vectors in this specification remain authoritative if a later oracle release changes defaults.

SAIDification SHALL use this exact pipeline. Start with the ordered event mapping above and `v="KERI10JSON000000_"`. For `icp` and `dip`, replace both `d` and `i` with 44 ASCII `#` bytes, serialize compact JSON, replace the 6 size digits in `v` with the lowercase hexadecimal length of that complete dummy serialization, and serialize again. BLAKE3-256 the second dummy serialization, encode the digest with CESR code `E`, replace both `d` and `i` with that identical 44-byte qualified value, and serialize without changing `v`; the length SHALL remain equal. For `ixn`, apply the same steps with only `d` replaced by 44 `#` bytes while `i` remains the controller AID. Verification SHALL reconstruct and hash the appropriate dummy serialization and compare the result to `d`; inception verification SHALL additionally require `i == d`. Hashing final JSON that already contains its claimed SAID is invalid.

#### Scenario: Independent implementations derive the same identifier

- **WHEN** 2 implementations receive the same profile version, key material, store commitments, and event inputs
- **THEN** they emit identical event bytes, SAIDs, AIDs, and indexed signatures

#### Scenario: Semantically equivalent JSON is not the signed representation

- **WHEN** an event has equivalent parsed fields but different field order, whitespace, version-size bytes, or number spelling
- **THEN** it is not the profile event whose signature was supplied and verification fails

#### Scenario: Inception SAIDification has no digest cycle

- **WHEN** an implementation derives an `icp` or `dip`
- **THEN** it hashes the size-correct serialization with 44 `#` bytes in both `d` and `i`, then inserts the one derived qualified digest into both fields

### Requirement: Store commitments use one fixed construction

A `StoreCommitment` SHALL be the BLAKE3-256 digest of the following exact byte string:

`ASCII("mee-pdn.store-commitment.v1") || 0x00 || role-octet || namespace-id`

`namespace-id` SHALL be exactly the 32 raw capability bytes. `role-octet` SHALL be `0x01` for `directory` and `0x02` for `data`; no other role is valid in profile 1. At the KERI boundary the 32-byte digest SHALL be encoded as the 44-byte CESR BLAKE3-256 qualified digest with code `E`. The root inception `a` list SHALL contain exactly 2 digest-seal objects, each encoded as `{"d":"<qualified commitment>"}`, in `directory`, then `data` order. There is no implicit separator, text normalization, namespace encoding, or implementation-selected hash.

#### Scenario: A role swap changes the commitment

- **WHEN** the same namespace identifier is committed once as `directory` and once as `data`
- **THEN** the preimages differ at the role octet and the commitments differ

#### Scenario: Namespace capability bytes do not enter the KEL

- **WHEN** a root inception seals its store set
- **THEN** only the qualified commitment digests appear in the event, not either raw namespace identifier

### Requirement: Ceremony signatures cover canonical binary transcripts

All application-level transcript integers SHALL be unsigned big-endian. Every variable byte string SHALL be encoded as `u32 length || bytes`. Fixed byte strings SHALL be emitted without a length. Lists SHALL be `u32 count` followed by their elements. A `NodeId`, nonce, secret digest, and unqualified BLAKE3 digest are fixed 32 bytes; an Ed25519 signature is fixed 64 bytes; an AID, SAID, and qualified `StoreCommitment` is its 44 ASCII CESR bytes. The secret digest SHALL be BLAKE3-256 over `ASCII("mee-pdn.link-secret.v1") || 0x00 || the exact 32 secret bytes`. An event location is `aid || u64 sequence-number || u8 ilk || said`, where `ilk` is `0x01` for `icp`, `0x02` for `dip`, and `0x03` for `ixn`.

Each signature preimage SHALL begin with the listed ASCII domain followed by `0x00`, then the fields below in order. `versions` means protocol-version followed by profile-version, each a `u16`; both SHALL be `1`.

- `mee-pdn.link-request.v1`: versions, secret digest, nonce, root AID, inviter AID, newcomer AID, inviter `NodeId`, newcomer `NodeId`, newcomer `dip` SAID.
- `mee-pdn.link-manifest.v1`: versions, nonce, root AID, inviter AID, newcomer AID, inviter `NodeId`, newcomer `NodeId`, newcomer `dip` SAID, anchor event location, inviter key-state event location, frame inventory.
- `mee-pdn.link-confirmation.v1`: versions, root AID, newcomer AID, newcomer `NodeId`, signed-request digest, signed-manifest digest, directory commitment, data commitment, anchor event location, newcomer key-state event location.
- `mee-pdn.founder-binding.v1`: versions, root AID, founder AID, founder `NodeId`, founder `dip` SAID, directory commitment, data commitment, root-anchor event location, founder key-state event location, root key-state event location.

A frame-inventory element SHALL be `0x01 || 32-byte BLAKE3-256 digest of the exact encoded signed-KERI-event frame body`. The inventory SHALL enumerate, in stream order, every event frame preceding the manifest. It SHALL NOT include the manifest itself, which would be circular, or the tickets frame. Protocol order fixes manifest and tickets after the inventoried events. Newcomer confirmation signs both sealed store commitments and, by protocol rule, SHALL be produced only after the exact byte-bound pair has been consumed successfully; it does not contain the tickets-frame digest or capability-verdict evidence, so another device verifies the newcomer's signed assertion of local completion rather than independently replaying those ticket checks. For `N` inventory elements, the fixed profile-1 fields before the inventory occupy 495 bytes, the list count occupies 4 bytes, and the elements occupy `33 * N` bytes, so the exact manifest-preimage length SHALL be `499 + 33 * N`. The complete canonical `PDL1/0x03` manifest body SHALL therefore be `572 + 33 * N` bytes: 4 magic bytes, 1 kind byte, a 4-byte blob length, the preimage, and the 64-byte signature. Under the inclusive 65,536-byte complete-body limit, `N` SHALL be at most 1,968; 1,968 elements produce a 65,516-byte body, while 1,969 would produce 65,549 bytes and SHALL be rejected before signing, sending, or accepting the manifest. A signed-object digest SHALL be BLAKE3-256 over `ASCII("mee-pdn.signed-object.v1") || 0x00 || u32 preimage-length || preimage || 64-byte signature`. Application signatures SHALL be plain Ed25519 over the exact preimage and SHALL be verified against the accepted KERI key state named in that preimage. Unknown versions, fields, roles, kinds, trailing bytes, non-canonical lengths, or alternate domain labels SHALL be rejected rather than normalized.

For replicated proof bytes, `signed(preimage, signature)` SHALL be `u32 preimage-length || preimage || signature[64]`. `PendingLinkedOffer` SHALL be `ASCII("PDO1") || signed(request) || signed(manifest)`. A replicated `PendingRecord` SHALL be `ASCII("PDR1") || u64 inviter-created-at-unix-seconds || PendingLinkedOffer`, with the timestamp encoded unsigned big-endian like every other profile integer. `DeviceBindingProof` SHALL be either `ASCII("PDB1") || 0x01 || signed(request) || signed(manifest) || signed(confirmation)` for `Linked`, or `ASCII("PDB1") || 0x02 || u32 founder-preimage-length || founder-preimage || founder-signature[64] || root-signature[64]` for `Created`. No anchor or trusted authorization field is appended outside these signed preimages. Unknown tags, non-canonical lengths, or trailing bytes invalidate the payload. The pending timestamp is lifecycle metadata governed by `pdn-node-device-linking`; it is not part of either signature and SHALL NOT contribute to access.

#### Scenario: A directory writer cannot synthesize confirmation

- **WHEN** a writer has the signed request and signed manifest but did not receive the newcomer's confirmation signature
- **THEN** it cannot construct a valid `link-confirmation` object for the confirmed binding

#### Scenario: A field moved between transcript domains is rejected

- **WHEN** valid bytes signed under one transcript domain are presented as another transcript type
- **THEN** the domain and ordered-field check fails before the signature can authorize that type

### Requirement: Stored and streamed signed events share one profile bound

Profile 1 SHALL define `signed-event material` as the exact final canonical KERI event JSON bytes followed by the fixed 88 ASCII bytes of its CESR indexed signature. Signed-event material SHALL be at most 61,440 bytes, so event JSON SHALL be at most 61,352 bytes in this one-signature profile. This one limit SHALL apply to every producer and consumer of a request inception, a reply signed-event frame, a stored KEL payload, and a durable accepted-head reconstruction set; no component SHALL define a wider stored-event limit or a narrower transport-only interpretation.

The canonical stored container SHALL be:

`ASCII("KEL1") || u32 event-json-length || event-json || indexed-signature[88]`

The length SHALL be unsigned big-endian and name the exact event JSON bytes. A canonical `KEL1` container is therefore at most 61,448 bytes. Its decoder SHALL require a nonzero event length, reject before allocating or reading event bytes when the announced length plus 88 would exceed the 61,440-byte signed-event-material limit, and require exactly one complete event and signature with no alternate tag, extra attachment, non-canonical length, or trailing byte.

The canonical `PDL1/0x02` body below wraps the identical signed-event material with `PDL1`, the kind octet, and the event-length field, so it is at most 61,449 bytes and necessarily fits the distinct 65,536-byte complete-body limit. Conversion between `KEL1` and `PDL1/0x02` SHALL preserve the event JSON and indexed-signature bytes exactly rather than parse and reserialize them. The common limit is a storage invariant as well as a transport limit: an event too large for canonical replay SHALL NOT be stored, accepted into a head, or retained in a reconstruction set, because another identity device could never receive that accepted event through profile 1.

#### Scenario: A stored event is always replayable

- **WHEN** signed-event material is accepted into `KEL1`, a durable reconstruction set, or an accepted KEL head
- **THEN** the identical event and signature fit a canonical `PDL1/0x02` body under the profile's complete-body limit

#### Scenario: Every signed-event reader rejects the same oversized material

- **WHEN** a request, reply frame, or `KEL1` container announces or carries event JSON whose length plus 88 exceeds 61,440
- **THEN** its reader rejects it before accepting the event, and no KEL entry, accepted head, anchor, or pending record is produced from it

### Requirement: Linking profile 1 has one canonical frame encoding

`/pdn/linking/1` SHALL NOT serialize Rust/Serde data structures directly. Every transport message SHALL be `u32 little-endian body-length || body`; the prefix is not part of the body. Every body SHALL be at most 65,536 bytes and SHALL begin with the 4 ASCII bytes `PDL1` followed by 1 kind octet. Both inviter and newcomer SHALL reject an announced body length over 65,536 before allocating or reading the claimed body. Within a body all integer lengths and versions SHALL be unsigned big-endian. `blob(x)` means `u32 byte-length || x`. A KERI indexed signature is its fixed 88 ASCII CESR bytes; an application Ed25519 signature is 64 raw bytes.

The only valid bodies are:

- request `0x01`: `PDL1 || 0x01 || u16 protocol-version || u16 profile-version || secret[32] || nonce[32] || blob(dip-event-json) || indexed-signature[88] || request-signature[64]`;
- signed event `0x02`: `PDL1 || 0x02 || blob(event-json) || indexed-signature[88]`;
- manifest `0x03`: `PDL1 || 0x03 || blob(manifest-preimage) || manifest-signature[64]`;
- tickets `0x04`: `PDL1 || 0x04 || blob(directory-ticket) || blob(data-ticket)`;
- end `0x05`: exactly `PDL1 || 0x05` and no payload.

The request versions SHALL both be `1`. The request frame SHALL carry no request preimage and no claimed `NodeId`. Before anchoring or writing pending state, the inviter SHALL reconstruct the sole canonical `link-request` preimage from the frame versions, secret digest, nonce, invite's root and inviter AIDs, the newcomer AID and `dip` SAID verified from the signed event, its own authenticated local `NodeId`, and the connection's authenticated peer `NodeId`, then verify `request-signature` over those reconstructed bytes. No body field may override either endpoint identity. The newcomer SHALL likewise require the returned manifest's 2 `NodeId` fields to equal the same local and authenticated peer identities before accepting it. Each ticket blob SHALL be the lowercase ASCII canonical `DocTicket` string produced by `iroh_tickets::Ticket::encode_string` for the `pdn-store` ticket format at commit `721de6263212676080e67438c9eb8a4eee1be9d7`; decoding and re-encoding SHALL reproduce identical bytes. This pins only the existing ticket payload carried by the frame, not an alternate ticket format.

The request's delegated-inception JSON plus its indexed signature and every reply `0x02` event JSON plus its indexed signature SHALL satisfy the shared 61,440-byte signed-event-material limit above. The inviter SHALL enforce it while decoding the request before anchoring, and the newcomer SHALL enforce it while decoding every reply event. A local encoder SHALL refuse to produce a request, reply frame, stored `KEL1`, or accepted reconstruction record that violates it.

One request body is followed by a reply containing every signed-event body in root-to-inviter order including the new anchor, exactly 1 manifest, exactly 1 tickets body, and exactly 1 end body, in that order. No body may follow end. EOF, an unknown kind, a duplicate or out-of-order singleton, non-canonical ticket text, a length mismatch, or trailing body bytes SHALL be refused. Uniform inviter refusal is connection close without a valid end sequence; there is no error body. The manifest inventory digest is BLAKE3-256 over each complete `0x02` body, including `PDL1`, kind, lengths, event, and signature. The end-frame golden encoding is body hex `50444c3105` and complete transport bytes `0500000050444c3105`.

#### Scenario: Independent implementations inventory the same frame

- **WHEN** 2 implementations encode the same event JSON and indexed signature
- **THEN** their complete `0x02` bodies and the BLAKE3-256 inventory digest over those bodies are byte-for-byte equal

#### Scenario: Manifest inventory stops before its frame overflows

- **WHEN** a manifest inventories 1,968 event frames, and separately when a manifest would inventory 1,969
- **THEN** the first canonical manifest body is 65,516 bytes and valid, while the second would be 65,549 bytes and is rejected before signing or sending

#### Scenario: A reply ends explicitly

- **WHEN** tickets arrive without the exact end body or any bytes arrive after end
- **THEN** the reply is incomplete or malformed and is refused

#### Scenario: A request cannot claim another endpoint

- **WHEN** a caller signs a request transcript containing a `NodeId` other than the authenticated connection peer
- **THEN** the inviter's reconstruction produces different signed bytes and request verification fails before any anchor or pending record is written

### Requirement: The profile carries a normative golden vector

The following fixture is normative. Seeds are public test inputs and SHALL never be used as production keys. Root current, root next, founder current, and founder next Ed25519 seeds are respectively byte ranges `00..1f`, `20..3f`, `40..5f`, and `60..7f`. Directory and data namespace identifiers are respectively byte ranges `00..1f` and `20..3f`.

```text
directory commitment: EF00fc52PBJlNg9Ac-HGzaMeJEviv2xfQm7058_PmEbB
data commitment:      EPeDkCQK3KCPtGaes0BkL6TKEJy11OmGqhcS1wHj6_Gu

root icp bytes: {"v":"KERI10JSON000194_","t":"icp","d":"EA2m7nAGaydwTayW7Hk2b9MIy5LBVXW8QARy5Nk6Tasd","i":"EA2m7nAGaydwTayW7Hk2b9MIy5LBVXW8QARy5Nk6Tasd","s":"0","kt":"1","k":["DAOhB7_zzhC-HXDdGOdLwJln5NYwm6UNXx3chmQSVTG4"],"nt":"1","n":["EHD_4H_FDewzcl3RNnxInvOdHwPxZx3gp6f-3X3459Dl"],"bt":"0","b":[],"c":[],"a":[{"d":"EF00fc52PBJlNg9Ac-HGzaMeJEviv2xfQm7058_PmEbB"},{"d":"EPeDkCQK3KCPtGaes0BkL6TKEJy11OmGqhcS1wHj6_Gu"}]}
root icp SAID input: {"v":"KERI10JSON000194_","t":"icp","d":"############################################","i":"############################################","s":"0","kt":"1","k":["DAOhB7_zzhC-HXDdGOdLwJln5NYwm6UNXx3chmQSVTG4"],"nt":"1","n":["EHD_4H_FDewzcl3RNnxInvOdHwPxZx3gp6f-3X3459Dl"],"bt":"0","b":[],"c":[],"a":[{"d":"EF00fc52PBJlNg9Ac-HGzaMeJEviv2xfQm7058_PmEbB"},{"d":"EPeDkCQK3KCPtGaes0BkL6TKEJy11OmGqhcS1wHj6_Gu"}]}
root icp signature: AAAmbzxPy8n2LoC8L8H7eZczHYmQnDsw8wUJ8Hb-uV0lyvZ-CxgIeDhl27p9SSWTStHkE3PZhigrIpNlBn8Ktw0O

founder dip bytes: {"v":"KERI10JSON00015f_","t":"dip","d":"EN3Qeassn9W_vfTIB7U8w7fHfYK7zcN-LCivOAf_ZMR3","i":"EN3Qeassn9W_vfTIB7U8w7fHfYK7zcN-LCivOAf_ZMR3","s":"0","kt":"1","k":["DCVDuS_xCVURR2rcg2nbbdyTNmWhGXjdoUBO4QZsqVWd"],"nt":"1","n":["EERqDvf5wqsMwXCYJmWuUHbTjueSSqTm437sQJbWRHTf"],"bt":"0","b":[],"c":[],"a":[],"di":"EA2m7nAGaydwTayW7Hk2b9MIy5LBVXW8QARy5Nk6Tasd"}
founder dip signature: AACJfa3IE9ytj2BndsyVgViWzNNs8ipXqYyYjQzWdHZSf2y_GQWRf6unVPrm8uYx5D5EpfIuC9NIBRSyGu8uo-sE

root ixn bytes: {"v":"KERI10JSON00013a_","t":"ixn","d":"EG8bM-_PrYtFymSSFxO1EA4oCWkQAKwUy7GwEbL_wcjt","i":"EA2m7nAGaydwTayW7Hk2b9MIy5LBVXW8QARy5Nk6Tasd","s":"1","p":"EA2m7nAGaydwTayW7Hk2b9MIy5LBVXW8QARy5Nk6Tasd","a":[{"i":"EN3Qeassn9W_vfTIB7U8w7fHfYK7zcN-LCivOAf_ZMR3","s":"0","d":"EN3Qeassn9W_vfTIB7U8w7fHfYK7zcN-LCivOAf_ZMR3"}]}
root ixn signature: AAB9ZGqwZ7KL_JcagQyggN77Hi7rTUsk7VNTyIRCe4tKEmD07HrKA2U6OniVkbgevoA-WDR8ueSdRCqP0W0t6RgI
```

The directory commitment preimage hex is `6d65652d70646e2e73746f72652d636f6d6d69746d656e742e76310001000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`; the data preimage hex is `6d65652d70646e2e73746f72652d636f6d6d69746d656e742e76310002202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f`.

The following encoding fixture is also normative. It tests binary transcript/container/framing rules independently of ceremony topology: the root fields above occupy the inviter slots, the founder fields occupy newcomer slots, inviter and newcomer `NodeId` values are byte ranges `00..1f` and `20..3f`, the one-time secret is `c0..df`, and the nonce is `e0..ff`. Its anchor location is `(root AID, 1, ixn, root-ixn SAID)`, inviter/root key-state location is `(root AID, 1, icp, root AID)`, and newcomer key-state location is `(founder AID, 0, dip, founder AID)`; these deliberately synthetic location values exercise field encoding, not KEL semantic acceptance. The pending timestamp is decimal `1800000000`. BLAKE3 values below are raw lowercase hexadecimal digests of the complete named byte strings. An implementation SHALL reconstruct the bytes from the grammar and fixture fields and match both length and digest; signatures SHALL match exactly.

```text
request preimage:      len 332, blake3 ef72eda359947f7d56dca08bfa9baea472739f8425085db50645522eb2ddae40
request signature:     84ed75cb8eed467a193062854bf9a8bd5627ac6ca777ec95c32997887ef803a45b98b98a63fa8b7ce849226d73ead4f2c45d4fdb894301b1b07fd0b3e1f52709
manifest preimage:     len 532, blake3 cf4859c71865ec15611616fba9895a6fd2f5682f9016343d55358a19c1c07b24
manifest signature:    495132bf835d0b422379e41b2b7952f7fa30e388dd574ffe82ba2cdbe5015b754db78495cc429070bc97f49ac3622e22e7d9a129dc4e2d7f7b7a344ac6616a0d
confirmation preimage: len 499, blake3 52e0225eb40db2b0400c35519cc7e09de3e48155074008e7099505d4427f0dcc
confirmation signature: ad350337b63836c55665e851fc7660415c41d7077a27f7b711b2bf633c2473f1ff83e6e4933608e8006f71c9f0a38248a9dcab6b1bad20e89ec6294b6c092804
founder preimage:      len 574, blake3 7e862d1fc75bf6de8a95dee05c389073aa658910a3ed43182b551c47e8bdd746
founder signature:     dce65ffd09862f86a2572722a3b9ddae7aaaa825a93cbe54efb834a66345d8915f9e462db4e2fba41c8fb7c9c4bfeb08c82f771999c3d64bbf502dec36f44c05
root countersignature: e23245fdb0314b9c878a71a6f42379b9454360ea1f7f230354e883f3473ca0b46ce40d9ddece8279239ddf9e414da4fe112011717eb5891abf4509f4cfccf90b

PDO1:       len 1004, blake3 b11c1cd09f95654704a16e58378096ca2b8148cd84e5039b50f1a14b50a56f26
PDR1:       len 1016, blake3 8d494f791a8091f3dc19b5094458f47dfb5e179991ba88270792d1652bd276c5
PDB1 linked: len 1572, blake3 9e3aaf247fa24f6653870ad862d8dddb3355e8ad81238948e29b67b6f75c283c
PDB1 created: len 711, blake3 458c59b2186677af5a0b450a5a9e775b926ca86b6f53ad95ce5812285a801099

signed-event 0x02 body: len 411, blake3 e4510b2b12353a0a85b76f708536e2d3a9b6c321030974c11cff82fe5f9637cc
frame inventory:        len 37, blake3 75fd95f67a716fa93a49e3a187f28ba9a84c0c1a29a9098ff47743456a9f8867
frame inventory hex:    0000000101e4510b2b12353a0a85b76f708536e2d3a9b6c321030974c11cff82fe5f9637cc
```

The exact `0x02` body hex used by that inventory is:

```text
50444c31020000013a7b2276223a224b45524931304a534f4e3030303133615f222c2274223a2269786e222c2264223a22454738624d2d5f5072597446796d535346784f314541346f43576b51414b77557937477745624c5f77636a74222c2269223a224541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b3654617364222c2273223a2231222c2270223a224541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b3654617364222c2261223a5b7b2269223a22454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233222c2273223a2230222c2264223a22454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233227d5d7d414142395a4771775a374b4c5f4a636167517967674e3737486937725455736b37564e54794952436534744b456d44303748724b413255364f6e69566b626765766f412d5744523875655364524371503057307436526749
```

The same root `ixn` event and indexed signature in the canonical stored container are `KEL1: len 410, blake3 5971c416486dbe44bfff029340d038c8e95b21b6e9992a18324d2fd7963cf807`, with exact hex:

```text
4b454c310000013a7b2276223a224b45524931304a534f4e3030303133615f222c2274223a2269786e222c2264223a22454738624d2d5f5072597446796d535346784f314541346f43576b51414b77557937477745624c5f77636a74222c2269223a224541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b3654617364222c2273223a2231222c2270223a224541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b3654617364222c2261223a5b7b2269223a22454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233222c2273223a2230222c2264223a22454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233227d5d7d414142395a4771775a374b4c5f4a636167517967674e3737486937725455736b37564e54794952436534744b456d44303748724b413255364f6e69566b626765766f412d5744523875655364524371503057307436526749
```

The request preimage hex is included to catch endpoint order and the absence of a wire-supplied preimage:

```text
6d65652d70646e2e6c696e6b2d726571756573742e763100000100014e47e43802a49d570b91147db4a55cc6fb2df52aebda515d4d1fae6d2684725ee0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff4541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b36546173644541326d376e4147617964775461795737486b3262394d4979354c425658573851415279354e6b3654617364454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f454e3351656173736e39575f76665449423755387737664866594b377a634e2d4c4369764f41665f5a4d5233
```

#### Scenario: The checked oracle reproduces the vector

- **WHEN** the pinned oracle and the implementation generate this fixture
- **THEN** every commitment, event byte, AID, SAID, transcript, replicated container, frame inventory, and signature is byte-for-byte equal to the values above
