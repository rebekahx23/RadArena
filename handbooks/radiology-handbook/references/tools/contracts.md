# Tool contracts and current status

| Interface | Input | Output | Current implementation |
| --- | --- | --- | --- |
| Handbook reader | Allowed chapter path for the active role | Exact chapter text or unavailable stub | Implemented, read-only application interface |
| Image inspection | Current study images and focused question | Observation and limitations | Implemented via configured vision model |
| RadGraph extraction | Supplied report sentences | Text entities, relations and status labels | Implemented optional local CPU preprocessing; extraction extra required |
| Private reference comparison | Original and candidate | Text/graph differences | Not exposed to Blue; graph comparison not implemented |
| Learned memory update | Training traces and feedback | Versioned strategies | Planned; not implemented |

Tool descriptions do not execute functions. Record genuine call outputs; do not invent
results for an unavailable tool. RadGraph describes report text rather than verifying
an image. Its status labels can be wrong. Keep original sentences; never treat a graph
as independent image evidence. The controller supplies only the active role's permitted
report graph. See the [official RadGraph project](https://github.com/Stanford-AIMI/radgraph)
and project `docs/RADGRAPH.md` for the actual integration and observed extraction errors.

The reader accepts only manifest-listed paths for the active role and condition. It does
not expose arbitrary local files, report manifests, private labels, or the other role's
book. Full OS/container read-only mounting is not implemented in this local prototype.
