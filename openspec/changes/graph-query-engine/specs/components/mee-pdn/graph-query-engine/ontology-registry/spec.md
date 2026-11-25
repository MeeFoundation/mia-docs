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

### Requirement: Types and shapes are read from the graph

A type, its shape (its fields, and theirs, down to the values), the entity types that carry fields and the subject types, which carry none, SHALL be read from the registry as it is loaded into the graph. A type MAY be looked up by its id or by its display name, and a name the registry does not hold SHALL be refused with the names of the entity types it does hold.

**Example:** the shape of `mee:PetMedicationRecord:v1` has the field `medication`, whose own shape is `Medication`. `PetMedicationRecord` is among the entity types and `Person` among the subject types; a lookup of `NoSuchType` by name is refused.

#### Scenario: Shapes, entity types and subject types come from the registry in the graph

- **WHEN** a reader asks for the shape of `mee:PetMedicationRecord:v1`, the entity types and the subject types
- **THEN** the shape's field `medication` has the shape `Medication`, the entity types hold `PetMedicationRecord`, the subject types hold `Person` and not `PetMedicationRecord`, and a lookup of `NoSuchType` by name is refused
