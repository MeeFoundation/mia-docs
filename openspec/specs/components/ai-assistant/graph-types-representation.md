```cypher
// ============================================================
// GRAPH
// ============================================================

CREATE GRAPH mee;
USE mee;
```

## 1. `TypeDef`

`TypeDef` is a named ontological type. It represents domain concepts such as `Person`, `DriverLicense`, `DateOfBirth`, `Day`, `Month`, `Year`, `LicenseNumber`.

Anonymous intermediate nesting levels are **not** materialized as `TypeDef`.

```cypher
CREATE NODE TABLE TypeDef(
  // Stable ontology type identifier.
  // Example: mee:DriverLicense, mee:DateOfBirth, mee:Person
  type_id STRING PRIMARY KEY,

  // Human-readable ontology name.
  // Example: DriverLicense, DateOfBirth, Person
  name STRING,

  // Normalized ontology name.
  // Example: driver_license, date_of_birth, person
  canonical_name STRING,

  // Ontological kind.
  // Expected values:
  //   entity      = subject/entity type, e.g. Person
  //   scalar      = atomic semantic value, e.g. DateOfBirth, Month
  //   compound    = structured semantic value, e.g. DriverLicense
  //   list        = named list-like semantic value, if explicitly modeled
  //   ref         = reference to another Subject
  //   secret      = secret-bearing value
  //   credential  = credential-like compound value
  kind STRING,

  // Physical primitive carrier for scalar TypeDefs.
  // Expected values when kind = scalar:
  //   bool
  //   int
  //   float
  //   decimal
  //   string
  //   date
  //   timestamp
  //   blob
  //
  // Null for non-scalar TypeDefs.
  primitive_representation STRING
);
```

## 2. `FieldSpec`

`FieldSpec` is a slot inside a compound structure. It is not runtime data. It says that a parent type or anonymous structural field may contain a member with a given structural key.

```cypher
CREATE NODE TABLE FieldSpec(
  // Stable field identifier.
  // Example: mee:DriverLicense.license_number
  // Example: mee:DriverLicense.holder.birth.date_of_birth
  field_id STRING PRIMARY KEY,

  // Structural member key used in serialized object form.
  // Example: license_number, holder, date_of_birth
  member_key STRING,

  // Human-friendly label.
  // Example: License number, Holder, Date of birth
  display_name STRING,

  // Whether the field must be present.
  required BOOL,

  // Field cardinality.
  // Expected values:
  //   one       = exactly one value
  //   optional  = zero or one value
  //   many      = multiple values, usually represented through a list value
  cardinality STRING,

  // Optional display/source order inside the parent shape.
  // This is not the identity of the field.
  ordinal INT64
);
```

## 3. Ontology shape relationships

A named compound `TypeDef` owns top-level fields.

```cypher
CREATE REL TABLE TYPE_HAS_FIELD(
  FROM TypeDef TO FieldSpec
);
```

An anonymous structural `FieldSpec` owns nested fields.

```cypher
CREATE REL TABLE FIELD_HAS_FIELD(
  FROM FieldSpec TO FieldSpec
);
```

A typed field points to the ontological type of the value occupying that field.

```cypher
CREATE REL TABLE FIELD_VALUE_TYPE(
  FROM FieldSpec TO TypeDef
);
```

Interpretation:

```text
TypeDef(DriverLicense)
  -- TYPE_HAS_FIELD -->
FieldSpec(holder)

FieldSpec(holder)
  -- FIELD_HAS_FIELD -->
FieldSpec(date_of_birth)

FieldSpec(date_of_birth)
  -- FIELD_VALUE_TYPE -->
TypeDef(DateOfBirth)
```

A `FieldSpec` has one of two roles:

```text
Typed field:
  FieldSpec -- FIELD_VALUE_TYPE --> TypeDef

Anonymous structural field:
  FieldSpec -- FIELD_HAS_FIELD --> child FieldSpec(s)
```

Leaf fields must eventually resolve to `FIELD_VALUE_TYPE`.

## 4. `Subject`

`Subject` is the thing a claim is about.

```cypher
CREATE NODE TABLE Subject(
  // Stable subject identifier.
  subject_id STRING PRIMARY KEY,

  // Human-readable display name.
  display_name STRING
);
```

Optional subject classification:

```cypher
CREATE REL TABLE SUBJECT_HAS_TYPE(
  FROM Subject TO TypeDef
);
```

## 5. `Claim`

`Claim` is the assertion envelope. In this minimized model, it only connects a `Subject` to one root `ValueNode`.

The claim itself is not typed.

```cypher
CREATE NODE TABLE Claim(
  // Stable claim identifier.
  claim_id STRING PRIMARY KEY,

  // Claim lifecycle state.
  // Expected values:
  //   active
  //   revoked
  //   superseded
  //   expired
  //   imported
  status STRING
);
```

Claim target:

```cypher
CREATE REL TABLE CLAIM_ABOUT(
  FROM Claim TO Subject
);
```

Claim payload:

```cypher
CREATE REL TABLE CLAIM_HAS_VALUE(
  FROM Claim TO ValueNode
);
```

## 6. `ValueNode`

`ValueNode` stores the actual claim value tree.

A scalar `ValueNode` stores a primitive value.
An object/list `ValueNode` acts as a container.

```cypher
CREATE NODE TABLE ValueNode(
  // Stable value node identifier.
  value_id STRING PRIMARY KEY,

  // Runtime representation shape.
  // Expected values:
  //   scalar
  //   object
  //   list
  //   null
  representation_kind STRING,

  // Physical stored value.
  // For object/list/null containers, use none_value.
  value UNION(
    none_value STRING,
    bool_value BOOL,
    int_value INT64,
    float_value DOUBLE,
    decimal_value DECIMAL(38, 10),
    string_value STRING,
    date_value DATE,
    timestamp_value TIMESTAMP,
    blob_value BLOB,
    ref_subject_id STRING
  )
);
```

The root claim value is explicitly typed:

```cypher
CREATE REL TABLE VALUE_HAS_TYPE(
  FROM ValueNode TO TypeDef
);
```

Object-member containment:

```cypher
CREATE REL TABLE VALUE_HAS_OBJECT_MEMBER(
  FROM ValueNode TO ValueNode,

  // Stable containment edge identifier.
  containment_id STRING,

  // Structural key in the represented object.
  // Example: license_number, holder, date_of_birth
  member_key STRING,

  // Optional source/display order.
  // This allows ordered-object behavior if desired,
  // but member_key remains the object-member identity.
  ordinal INT64
);
```

List-item containment:

```cypher
CREATE REL TABLE VALUE_HAS_LIST_ITEM(
  FROM ValueNode TO ValueNode,

  // Stable containment edge identifier.
  containment_id STRING,

  // Zero-based list position.
  index INT64
);
```

## Core invariants

```text
1. Claim is not typed.

2. Claim points to exactly one root ValueNode.

3. The root ValueNode has VALUE_HAS_TYPE -> TypeDef.

4. Nested ValueNodes do not need direct type edges.

5. For object values:
   ValueNode -- VALUE_HAS_OBJECT_MEMBER { member_key } --> child ValueNode

6. For list values:
   ValueNode -- VALUE_HAS_LIST_ITEM { index } --> child ValueNode

7. Object member identity is member_key.
   ordinal is optional ordering metadata, not identity.

8. List item identity is index.

9. Type inference for nested values is done from:
   root ValueNode -> TypeDef
   then TypeDef / FieldSpec shape traversal
   then runtime member_key / index traversal.

10. Within one parent shape, FieldSpec.member_key should be unique.

11. A FieldSpec is either:
   a typed value slot via FIELD_VALUE_TYPE,
   or an anonymous structural slot via FIELD_HAS_FIELD.

12. Leaf FieldSpecs must have FIELD_VALUE_TYPE -> TypeDef.
```

Minimal object set:

```text
TypeDef
FieldSpec
Subject
Claim
ValueNode
```

Minimal relationship set:

```text
TYPE_HAS_FIELD
FIELD_HAS_FIELD
FIELD_VALUE_TYPE

SUBJECT_HAS_TYPE

CLAIM_ABOUT
CLAIM_HAS_VALUE

VALUE_HAS_TYPE
VALUE_HAS_OBJECT_MEMBER
VALUE_HAS_LIST_ITEM
```
