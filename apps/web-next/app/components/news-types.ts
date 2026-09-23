// Shared shapes for /api/v1/news (list) and /api/v1/news/{id} (detail).
// One definition, consumed by every page that renders a news item, so the
// dashboard, the news stream and a source's "latest items" list can never
// drift into different card behavior again.

export interface NewsListItem {
  item_id: string;
  source_id: string;
  title: string;
  summary: string | null;
  summary_source: string | null;
  summary_available: boolean | null;
  content_language: string | null;
  canonical_url: string;
  published_at: string | null;
  fetched_at: string | null;
  first_seen_at: string | null;
  category: string | null;
  topics: string[];
  taxonomy_version: string | null;
  provenance_status: string;
  source_name: string | null;
  hostname: string | null;
  source_type: string | null;
  source_category?: string | null;
  summary_fa_status?: string;
  summary_fa?: string | null;
  title_fa_status?: string;
  title_fa?: string | null;
  lead_image_url?: string | null;
  lead_image_alt?: string | null;
  lead_image_verification?: string | null;
  content_status?: string;
  display_policy?: string;
  text_chars?: number;
}

export interface ContentField {
  extraction_status: string;
  display_policy: string;
  original_text: string | null;
  text_chars: number;
  extraction_method: string | null;
  original_text_withheld_reason?: string;
  note?: string;
}

export interface TranslationField {
  field?: string;
  status: string;
  text: string | null;
  provider: string | null;
  model: string | null;
  source_chars?: number | null;
  error?: string | null;
  updated_at?: string | null;
}

export interface MediaItem {
  media_id: string;
  kind: string;
  url: string;
  mime_type: string | null;
  declared_width: number | null;
  declared_height: number | null;
  alt_text: string | null;
  relevance: string;
  verification_status: string;
}

export interface NewsDetailItem extends Omit<NewsListItem, 'source_category'> {
  source_url?: string | null;
  feed_url?: string | null;
  content?: ContentField;
  translations?: Record<string, TranslationField>;
  media?: { images: MediaItem[]; documents: MediaItem[]; filtered_out: { url: string; relevance: string; rejection_reason: string | null }[]; note?: string };
  provenance?: { feed_url: string; execution_reference: string; evidence_status: string; evidence_json: unknown }[];
}
