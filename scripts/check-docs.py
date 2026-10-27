#!/usr/bin/env -S python3 -I
"""Checks the rules of the spec tree that `openspec validate` leaves alone.

- A scenario heading has exactly four hashes: at another level the validator drops the scenario in silence.
- The spec tree names no line number (`sync.rs:622`): a number is right until the next edit.
- The spec tree and its ADRs carry no decision number (D1..Dn): those live in a change's design.
- A relative link resolves. A change's deltas are skipped, since their links are written for their place in
  the main tree, and so is a link leaving this repository: the workspace beside it is not checked out here.

Prints `path:line: rule` per finding and exits 1 if there is any.
"""

import sys

# Before any other import: without -I a module file beside the script shadows the standard library.
if not sys.flags.isolated:
    sys.exit(f'{sys.argv[0]}: run in isolated mode, python3 -I')

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENSPEC = ROOT / 'openspec'

SCENARIO = re.compile(r'^(#+)\s*Scenario:')
LINE_NUMBER = re.compile(r'\b[\w./-]+\.(?:rs|md|toml|py|sh|ya?ml|ts|swift|kt):\d+')
DECISION = re.compile(r'(?<![\w-])D\d+\b')
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)]*)?\)')
SCHEME = re.compile(r'^[a-z][a-z0-9+.-]*:')


def prose_lines(path):
    """Each line outside a fenced block, with its number."""
    fenced = False
    for number, line in enumerate(path.read_text(encoding='utf-8').split('\n'), 1):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def check(path):
    rel = path.relative_to(ROOT)
    parts = rel.parts
    in_tree = parts[:2] == ('openspec', 'specs')
    is_delta = parts[:2] == ('openspec', 'changes') and 'specs' in parts[2:]
    for number, line in prose_lines(path):
        heading = SCENARIO.match(line.strip())
        if heading and len(heading.group(1)) != 4:
            yield number, 'a scenario heading takes exactly four hashes'
        if in_tree and LINE_NUMBER.search(line):
            yield number, 'the spec tree names a file and a function, never a line number'
        if in_tree and DECISION.search(line):
            yield number, 'the spec tree carries no decision number; describe the decision in words'
        if is_delta:
            continue
        for match in LINK.finditer(line):
            target = match.group(1)
            if SCHEME.match(target):
                continue
            resolved = (path.parent / target).resolve()
            if resolved.is_relative_to(ROOT) and not resolved.exists():
                yield number, f'the link {target} resolves to nothing'


def main():
    files = sorted([*OPENSPEC.rglob('*.md'), *ROOT.glob('*.md')])
    found = 0
    for path in files:
        for number, rule in check(path):
            print(f'{path.relative_to(ROOT)}:{number}: {rule}')
            found += 1
    if found:
        sys.exit(1)


if __name__ == '__main__':
    main()
