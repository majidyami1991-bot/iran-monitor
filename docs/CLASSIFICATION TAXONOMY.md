# Rule-based classification taxonomy

Taxonomy version 1.0.0 is defined in `config/sources/classification-taxonomy-v1.json`. It applies deterministic keyword rules to stored titles and summaries only. A record may match multiple categories; one ordered primary category is stored with the matched topics. The fallback category is “other”. There is no model score, confidence claim, causal interpretation or human-review claim.

Historical records are backfilled from their already stored text. The taxonomy does not fetch pages or enrich records from outside the database. New RSS items are classified in the same transaction as the item, provenance and source run result. Each classification stores the taxonomy version and method so future taxonomy revisions remain auditable.
