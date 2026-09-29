// Shapes of the experience APIs (apps/api/experience.py). Optional fields are
// genuinely optional in the API; null means "not recorded", never zero.
export type Importance = 'high' | 'medium' | 'low';

export interface FeedItem {
  item_id: string;
  title: string;
  summary: string | null;
  summary_available: boolean | null;
  content_language: string | null;
  canonical_url: string | null;
  published_at: string | null;
  fetched_at: string | null;
  provenance_status: string | null;
  source_id: string;
  source_name: string;
  hostname: string | null;
  source_type: string | null;
  category_id: string | null;
  category_label: string | null;
  secondary: { id: string; label: string; score: number }[] | null;
  subtopics: { id: string; label: string; parent: string }[] | null;
  confidence: number | null;
  other_reason_code: string | null;
  title_fa: string | null;
  title_fa_status: string;
  title_fa_review: string | null;
  summary_fa: string | null;
  summary_fa_status: string;
  summary_fa_review: string | null;
  translation_provider: string | null;
  translation_model: string | null;
  translation_served_by: string | null;
  image_url: string | null;
  image_alt: string | null;
  image_verification: string | null;
  event_id: string | null;
  event_sources: number;
  event_members: number;
  importance: number;
  importance_level: Importance;
  machine_translated: boolean;
  breaking: boolean;
  primary_media: PrimaryMedia | null;
  media_count: number;
  media_status: 'available' | 'missing' | 'rejected' | 'blocked' | 'unreachable' | 'pending';
}

export interface PrimaryMedia {
  id: string | null; type: 'image'; url: string; thumbnail_url: string | null; width: number | null; height: number | null;
  alt_text: string | null; caption: string | null; credit: string | null; source_method: string | null; validation_status: string;
}

export interface FeedResponse { items: FeedItem[]; total: number; page: number; page_size: number; has_next: boolean; taxonomy_version: string; }

export interface Frame {
  kind: 'item' | 'event' | 'source' | 'term';
  href: string;
  headline: string;
  headline_lang: 'fa' | 'en';
  subline?: string | null;
  subline_lang?: 'fa' | 'en';
  source_name?: string | null;
  published_at?: string | null;
  image_url?: string | null;
  category_id?: string | null;
  category_label?: string | null;
  importance_level?: Importance;
}

export interface StorySummary {
  story_id: string; kind: string; position: number; title_fa: string; subtitle_fa: string | null;
  collection_label: string; target_type: string; target_href: string;
  visual: { image_url: string | null; category_id: string | null; monogram: string };
  frame_count: number; content_updated_at: string | null; generated_at: string; rule_version: string;
}
export interface Story extends StorySummary { frames: Frame[]; evidence: Record<string, unknown>; }

export interface Integration {
  integration_id: string; kind: string; name_fa: string; status: string; enabled: boolean;
  reason_fa: string | null; contract: Record<string, unknown>; updated_at: string;
  live_status: string; live_detail?: Record<string, unknown> | null;
}

export interface EventRow {
  event_id: string; title: string; first_published_at: string | null; last_updated_at: string | null;
  source_count: number; member_count: number; clustering_method: string; algorithm_version: string;
  primary_category: string | null; primary_category_label: string | null; confidence: number | null;
  confidence_level: 'high' | 'medium' | 'low' | null;
  sources: { source_id: string; name: string }[] | null;
  pulses: { t: string | null; item_id: string }[] | null;
  image_url: string | null;
}
