# Snapshot preparation provenance

These exact source copies and selection records document how this snapshot was
prepared. They retain the original author's local paths. Use
`tools/continuation.py` at the repository root to verify, restore and resolve the
snapshot on a new device. These preparation copies are not a bootstrap command
or an execution admission.

The selection omits private credentials, chat/application stores, installed
development environments and retired QA scratch replicas. Saved Source, data,
handoffs, author/reviewer receipts, the original Git history and frozen runtime
reference bytes are retained. The manifest records exclusions and external
record mappings. Public CPython test keys are individually classified against
official CPython sources; they are not operational credentials, and their
original local bytes are preserved.
