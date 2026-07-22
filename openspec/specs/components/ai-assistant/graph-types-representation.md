Here is the minimized core model.

## 1. `TypeDef`

`TypeDef` represents an ontological type.

It is used for named concepts that can type a whole claim value or a semantic leaf value.

Examples:

```text
Person
DriverLicense
DateOfBirth
Day
Month
Year
DocumentNumber
```

It is **not** used for anonymous intermediate nesting levels unless those levels are explicitly named by the ontology.

```cypher
CREATE NODE TABLE TypeDef(
  type_id STRING PRIMARY KEY,
  namespace STRING,
  name STRING,

  -- entity | scalar | compound | list | ref | secret | credential
  kind STRING,

  -- physical representation for scalar TypeDefs only:
  -- bool | int | float | decimal | string | date | timestamp | json | blob
  primitive_representation STRING,

);
```

Role:

```text
TypeDef says what a value means ontologically.
```

---

## 2. `FieldSpec`

`FieldSpec` represents a field slot inside a compound type or anonymous structural field.

It is ontology structure, not runtime data.

Examples:

```text
DriverLicense.document_number
DriverLicense.holder
DriverLicense.holder.biographic
DriverLicense.holder.biographic.birth.date_of_birth
DateOfBirth.day
DateOfBirth.month
DateOfBirth.year
```

A `FieldSpec` can either:

```text
point to a TypeDef if the field value has an ontological type,
or contain child FieldSpecs if it is an anonymous structural field.
```

```cypher
CREATE NODE TABLE FieldSpec(
  field_id STRING PRIMARY KEY,
  field_name STRING,
  canonical_name STRING,

  -- one | optional | many
  cardinality STRING,

  required BOOL,
  ordinal INT64,

  -- debug/import path, not the source of truth
  scope_path STRING,
);
```

Role:

```text
FieldSpec says where a value sits inside a compound structure.
```

---

## 3. Type-shape relationships

A named compound `TypeDef` owns top-level fields:

```cypher
CREATE REL TABLE TYPE_HAS_FIELD(
  FROM TypeDef TO FieldSpec
);
```

An anonymous structural `FieldSpec` owns nested fields:

```cypher
CREATE REL TABLE FIELD_HAS_FIELD(
  FROM FieldSpec TO FieldSpec
);
```

A typed field points to the ontological type of the value occupying that field:

```cypher
CREATE REL TABLE FIELD_VALUE_TYPE(
  FROM FieldSpec TO TypeDef
);
```

Essence:

```text
TypeDef --TYPE_HAS_FIELD--> FieldSpec
FieldSpec --FIELD_HAS_FIELD--> FieldSpec
FieldSpec --FIELD_VALUE_TYPE--> TypeDef
```

Example:

```text
TypeDef(Person)
  --TYPE_HAS_FIELD--> FieldSpec(date_of_birth)
  --FIELD_VALUE_TYPE--> TypeDef(DateOfBirth)

TypeDef(DateOfBirth)
  --TYPE_HAS_FIELD--> FieldSpec(day)
  --FIELD_VALUE_TYPE--> TypeDef(Day)
```

For anonymous nesting:

```text
TypeDef(SomeRootType)
  --TYPE_HAS_FIELD--> FieldSpec(a)

FieldSpec(a)
  --FIELD_HAS_FIELD--> FieldSpec(aa)

FieldSpec(aa)
  --FIELD_HAS_FIELD--> FieldSpec(aaa)

FieldSpec(aaa)
  --FIELD_VALUE_TYPE--> TypeDef(AaaValue)
```

---

## 4. `Subject`

`Subject` is the thing the claim is about.

Examples:

```text
Alice
A company
A device
A credential holder
```

```cypher
CREATE NODE TABLE Subject(
  subject_id STRING PRIMARY KEY,
  display_name STRING,
);
```

Optional type classification:

```cypher
CREATE REL TABLE SUBJECT_HAS_TYPE(
  FROM Subject TO TypeDef
);
```

Since Subject is most likely to always be a MeeIdentity, the type specification can be redundant.

Role:

```text
Subject is the target of a claim.
```

---

## 5. `Claim`

`Claim` is the assertion envelope.

It says:

```text
This subject has this root value.
```

The claim itself is not typed. The root `ValueNode` is typed.

```cypher
CREATE NODE TABLE Claim(
  claim_id STRING PRIMARY KEY,

  status STRING,       -- active | revoked | superseded | expired | imported
  claim_role STRING,   -- asserted | self_attested | imported | derived

  issued_at TIMESTAMP,
  valid_from TIMESTAMP,
  valid_until TIMESTAMP,

  proof_type STRING,
  proof_json JSON,
  proof_hash STRING,

  source_doc_id STRING,
  source_json_path STRING,
  source_hash STRING
);
```

Claim-to-subject:

```cypher
CREATE REL TABLE CLAIM_ABOUT(
  FROM Claim TO Subject
);
```

Claim-to-root-value:

```cypher
CREATE REL TABLE CLAIM_HAS_VALUE(
  FROM Claim TO ValueNode
);
```

Role:

```text
Claim gives subject/proof/context to one root typed value.
```

---

## 6. `ValueNode`

`ValueNode` is the runtime value object.

It stores the actual primitive value, or acts as an object/list container when the value is compound.

```cypher
CREATE NODE TABLE ValueNode(
  value_id STRING PRIMARY KEY,

  value UNION(
    none_value STRING,
    bool_value BOOL,
    int_value INT64,
    float_value DOUBLE,
    decimal_value DECIMAL(38, 10),
    string_value STRING,
    date_value DATE,
    timestamp_value TIMESTAMP,
    json_value JSON,
    blob_value BLOB,
    ref_subject_id STRING
  ),
);
```

The root claim value has an explicit type:

```cypher
CREATE REL TABLE VALUE_HAS_TYPE(
  FROM ValueNode TO TypeDef
);
```

Nested values are connected by field-slot edges:

```cypher
CREATE REL TABLE VALUE_HAS_FIELD_VALUE(
  FROM ValueNode TO ValueNode,
  containment_id STRING,
  ordinal INT64
);
```

Role:

```text
ValueNode stores the actual value tree of the claim.
```

---

## Core invariant

```text
TypeDef defines ontological types.

FieldSpec defines slots inside compound structures.

Claim points to one root ValueNode.

The root ValueNode has VALUE_HAS_TYPE -> TypeDef.

Nested ValueNodes are connected through VALUE_HAS_FIELD_VALUE edges.

The types for subfields of ValueNodes are expected to be inferred from the connected TypeDef and corresponding FieldSpecs.
```

## Minimal mental model

```text
Ontology:

TypeDef
  -> FieldSpec
      -> TypeDef
          -> FieldSpec
              -> TypeDef

Runtime:

Subject
  <- Claim
      -> root ValueNode
          -> TypeDef
          -> child ValueNode
              -> child ValueNode
```
