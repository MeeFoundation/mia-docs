## 1. Author the greeting page

- [ ] 1.1 Create `hello.html` at the project root with a `<!doctype html>` document
- [ ] 1.2 Include the literal text `Hello, OpenSpec` inside the document body
- [ ] 1.3 Set a `<title>` so the page is identifiable when opened in a browser

## 2. Verify against the spec

- [ ] 2.1 Open `hello.html` in a browser and confirm the greeting text is visible (spec scenario: "Page is served at the canonical path")
- [ ] 2.2 Compute a hash of the file twice and confirm they match (spec scenario: "Page content is stable across requests")

## 3. Wrap up

- [ ] 3.1 Run `openspec status --change test-feature` and confirm all artifacts report `done`
- [ ] 3.2 Stage the new file alongside the OpenSpec change directory for review
