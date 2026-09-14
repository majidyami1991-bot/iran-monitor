# Security

`.env` contains local generated credentials and must stay ignored and untracked. `.env.example` contains placeholders only.
Never print environment values, UUIDs, tokens, rendered Compose configuration, healthcheck URLs or credential-bearing diagnostics. Limit access to the workstation account and do not share `.env`.
Secrets use cryptographic randomness; connector IDs and the admin token use unique UUIDv4. This pinned sample requires no encryption-key variable. OpenSearch credentials are generated for sample parity but unused by the canonical Elasticsearch stack.
The canonical upstream Elasticsearch disables authentication; that is unchanged, so internal network isolation is required. No database/search/broker/object-storage host ports are published. The only web binding is loopback HTTP; remote use requires a separately reviewed TLS and access-control plan.
No host networking, privileged services, fixed container names or Docker socket mounts are permitted. The XTM manager is removed rather than granted host Docker access.
Future deployment needs least-privilege users, separate connector service accounts, audited access and retention policies. X API credentials require separate authorization and secret storage; do not put them in source records.
Back up named database/object-storage volumes consistently and keep encrypted credential backups separately; test restoration before relying on backups. No backup or runtime data directories are created now.
Runtime sysctl is not persistent. Preflight must fail below 1048575, print the approved corrective command, never apply it silently, and be rerun immediately before any approved startup.
Image tags are versioned but not immutable digests. Their registry availability and security status must be reviewed before Phase 2; no image layers have been downloaded.

Phase 2R supersedes historical deployment instructions: canonical file is deployment/opencti/compose.pinned.yml; schema 18fdf8512f69e63d0856a7a4f5633ef7e482e5c0; target 7.260910.0. See deployment README for Silo compatibility fix and excluded services.
