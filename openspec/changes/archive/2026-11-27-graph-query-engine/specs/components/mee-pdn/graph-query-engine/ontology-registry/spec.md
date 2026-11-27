# Ontology registry

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Purpose

The types the graph query engine's graph is typed by ([ADR-0019](../../../../architecture/adr/0019-pods-read-through-a-graph-query-engine.md)): one registry, loaded into the graph from layers, mia-ontologies first and the application ontology on top, and read from the graph by everything that needs a type, a shape or a type's generalizations. A registry has five tables: the types, the fields, which type has which field, which type a field's value is, and which type extends which.

## ADDED Requirements

### Requirement: The registry is loaded layer on layer, and a broken one is refused whole

The graph SHALL be typed by one registry loaded from layers in order, mia-ontologies first and the application ontology on top. A later layer MAY use and extend the types of an earlier one, and SHALL NOT define a type or a field that is already defined, by an earlier layer or by itself. A registry SHALL be refused whole, and nothing of it loaded, when a type or a field is defined twice, when a relation names a type or a field the registry does not hold, or when a field a type has carries no value type.

**Example:** the application ontology loaded on top of mia-ontologies holds `app:Message:v1` and `mee:PetMedicationRecord:v1` side by side. The application ontology loaded on top of itself is refused with "type 'app:text-content:v1' is defined twice", its first type.

#### Scenario: The application ontology loads on top of mia-ontologies

- **WHEN** the registry is loaded from mia-ontologies and the application ontology
- **THEN** it holds the application ontology's types, among them `app:UnstructuredText:v1`, `app:Message:v1`, `app:Note:v1`, `app:CanvasElement:v1`, `app:Attachment:v1`, `app:CalendarEvent:v1` and `app:Recurrence:v1`, and mia-ontologies' types beside them, and mia-ontologies loaded alone holds no `app:` type

#### Scenario: A registry that defines a type twice is refused

- **WHEN** the application ontology is loaded on top of itself
- **THEN** the registry is refused as defining a type twice

### Requirement: A type is read as each type it extends

The registry's relation of a type to the type it extends SHALL be loaded into the graph. The generalizations of a type SHALL be the type itself, then the type it extends, then the type that one extends, and so on, nearest first.

**Example:** the generalizations of `app:Message:v1` are `app:Message:v1`, then `app:UnstructuredText:v1`, so a reader that knows only text reads a message as text.

#### Scenario: A message is read as text

- **WHEN** a reader asks for the generalizations of `app:Message:v1`
- **THEN** it gets `app:Message:v1` and `app:UnstructuredText:v1`, in that order

### Requirement: A value is checked against its type's shape

The engine SHALL check a value against a type's shape for any code that asks, and SHALL refuse it, naming the field at fault, when it has a field the shape does not have, lacks a required field, holds a list where the shape holds one value or one value where it holds a list, or holds a value of the wrong primitive. A date SHALL be written `2026-11-21`; a timestamp SHALL be RFC 3339, or the same date and time with no zone, after a `T` or a space; a decimal SHALL be a finite number of at most 28 digits before the point. It SHALL coerce nothing. A type with no fields SHALL take no value.

**Example:** a pod-tool keeping medication records checks each value against `mee:PetMedicationRecord:v1` before it writes the record. `{"species": "cat"}` is refused at `value.species`, which `PetMedicationRecord` does not have, and the pod-tool writes nothing.

#### Scenario: A value with a field its type does not have is refused

- **WHEN** a pod-tool checks `{"species": "cat"}` against `mee:PetMedicationRecord:v1`
- **THEN** it is refused, the refusal names `species`, and nothing is written

#### Scenario: A value is refused for a missing field, a wrong cardinality or a wrong primitive

- **WHEN** values are checked against a type's shape that lack a required field, hold a list where one value belongs, or hold a number where text belongs
- **THEN** each is refused, naming its field, and none is coerced

#### Scenario: A time that is not ISO 8601 is refused

- **WHEN** the `starts_at` of an `app:CalendarEvent:v1` is checked as `next Tuesday`, `2026-11-21T25:00:00Z`, `21.11.2026 10:00`, `2026-11-21T10:00:00Z`, `2026-11-21T10:00:00+01:00` and `2026-11-21 10:00:00`
- **THEN** the first three are refused at `value.starts_at`, and the last three are taken as they were written

### Requirement: Types and shapes are read from the graph

A type, its shape (its fields, and theirs, down to the values), the entity types that carry fields and the subject types, which carry none, SHALL be read from the registry as it is loaded into the graph. A type MAY be looked up by its id or by its display name, and a name the registry does not hold SHALL be refused with the names of the entity types it does hold.

**Example:** the shape of `mee:PetMedicationRecord:v1` has the field `medication`, whose own shape is `Medication`. `PetMedicationRecord` is among the entity types and `Person` among the subject types; a lookup of `NoSuchType` by name is refused.

#### Scenario: Shapes, entity types and subject types come from the registry in the graph

- **WHEN** a reader asks for the shape of `mee:PetMedicationRecord:v1`, the entity types and the subject types
- **THEN** the shape's field `medication` has the shape `Medication`, the entity types hold `PetMedicationRecord`, the subject types hold `Person` and not `PetMedicationRecord`, and a lookup of `NoSuchType` by name is refused
