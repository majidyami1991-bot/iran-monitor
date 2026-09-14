# Architecture

Sources (news sites, think tanks, feeds, selected X handles)
-> separately authorized collection connectors
-> OpenCTI Community Edition
-> analysis, provenance, entities and relationships
-> future custom Persian RTL homepage.

OpenCTI is the intelligence backend, not the future public homepage. Translation, summaries, maps, charts, timelines and alerts require later integrations.
X data access requires a separately authorized connector and credentials; it is not solved by installing OpenCTI.
No collection, source import or application UI is implemented in Phase 1.
The Compose project is iran-monitor-opencti with its own network and named volumes. Only 127.0.0.1:8080 is published.
The upstream socket-based XTM manager and its RSA helper are removed by the local override; connectors remain ordinary explicitly declared services.
