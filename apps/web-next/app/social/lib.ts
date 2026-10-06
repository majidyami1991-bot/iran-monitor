// Shared X-FREE client helpers. Writes always fetch a fresh CSRF token from
// the same origin and send JSON; the token is never stored or bundled.
export const IMPORTANCE_FA: Record<string, string> = { high: 'اهمیت زیاد', medium: 'اهمیت متوسط', low: 'اهمیت کم' };
export const VERIFICATION_FA: Record<string, string> = {
  unverified: 'راستی‌آزمایی‌نشده', verified: 'تأییدشده', disputed: 'مورد مناقشه', false: 'نادرست',
};
export const VERIFICATION_TONE: Record<string, 'uncertain' | 'ok' | 'warn' | 'error'> = {
  unverified: 'uncertain', verified: 'ok', disputed: 'warn', false: 'error',
};
export const AVAILABILITY_FA: Record<string, string> = {
  link_only: 'فقط پیوند · متن محلی ثبت نشده', text_recorded: 'متن ثبت‌شده توسط تحلیلگر',
  withdrawn: 'کنار گذاشته‌شده', unavailable: 'در X در دسترس نیست',
};
export const ERROR_FA: Record<string, string> = {
  manual_ingest_disabled: 'ثبت دستی در این محیط غیرفعال است.',
  origin_not_allowed: 'درخواست از مبدأ مجاز ارسال نشده است.',
  csrf_token_invalid: 'توکن امنیتی نامعتبر یا منقضی است؛ دوباره تلاش کنید.',
  url_missing_or_too_long: 'نشانی پست وارد نشده یا بیش از حد بلند است.',
  url_not_https: 'فقط نشانی HTTPS پذیرفته می‌شود.',
  url_host_not_x: 'فقط نشانی‌های x.com یا twitter.com پذیرفته می‌شوند (نشانی کوتاه یا دامنه مشابه رد می‌شود).',
  url_has_credentials_or_port: 'نشانی نباید نام کاربری، گذرواژه یا درگاه داشته باشد.',
  url_not_a_status_link: 'نشانی باید به یک پست مشخص اشاره کند: x.com/{حساب}/status/{شناسه}',
  handle_not_in_registry: 'این حساب در فهرست ۳۶ حساب ثبت‌شده منابع نیست.',
  duplicate_post: 'این پست قبلاً ثبت شده است.',
  published_at_invalid: 'تاریخ انتشار نامعتبر است.',
  published_at_out_of_range: 'تاریخ انتشار خارج از بازه مجاز است.',
  original_text_too_long: 'متن بیش از ۴۰۰۰ نویسه است.',
  original_text_control_characters: 'متن نویسه‌های کنترلی نامعتبر دارد.',
  analyst_note_too_long: 'توضیح تحلیلگر بیش از ۲۰۰۰ نویسه است.',
  analyst_name_invalid: 'نام تحلیلگر را وارد کنید (۲ تا ۶۰ نویسه).',
  unknown_topic: 'موضوع انتخاب‌شده در طبقه‌بندی وجود ندارد.',
  event_not_found: 'رویداد انتخاب‌شده پیدا نشد.',
  news_item_not_found: 'شناسه خبر پیدا نشد.',
  no_analyst_text_recorded: 'برای این پست متنی ثبت نشده است؛ اقدام هوش مصنوعی روی متن ساختگی اجرا نمی‌شود.',
  translation_is_local_batch_only: 'ترجمه پست‌های X فقط با پردازش دسته‌ای مدل محلی انجام می‌شود.',
  json_required: 'درخواست نامعتبر.',
};

export async function writeSocial<T>(path: string, method: 'POST' | 'PATCH', body: unknown): Promise<{ ok: boolean; status: number; data: T | { detail?: unknown } }> {
  const t = await fetch('/api/v1/social/csrf', { cache: 'no-store' });
  if (!t.ok) {
    const d = await t.json().catch(() => ({}));
    return { ok: false, status: t.status, data: d };
  }
  const { token } = await t.json();
  const r = await fetch('/api/v1/' + path, {
    method, cache: 'no-store',
    headers: { 'content-type': 'application/json', 'x-im-csrf': token },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export function errorText(detail: unknown): string {
  if (typeof detail === 'string') return ERROR_FA[detail] ?? detail;
  if (Array.isArray(detail)) return 'ورودی نامعتبر: ' + detail.map((d: { loc?: string[] }) => (d.loc || []).slice(-1)[0]).join('، ');
  return 'خطای نامشخص؛ هیچ داده‌ای ثبت نشد.';
}

export interface XAccount {
  source_id: string; handle: string; display_name: string | null; profile_url: string; description: string | null;
  category: string | null; monitoring_mode: string; status: string; last_manual_post_at: string | null; post_count: number;
  provenance_json: { table_index: number; row_index: number; raw_value: string }[];
}

export interface XPost {
  post_id: string; source_id: string; post_url: string; author_handle: string; original_text: string | null;
  translated_text_fa: string | null; summary_fa: string | null; published_at: string | null; manually_registered_at: string;
  topic_id: string | null; event_id: string | null; related_item_id: string | null; analyst_note: string | null;
  importance: string; verification_status: string; availability_status: string;
  provenance_json: Record<string, unknown> & { registered_by?: string; text_source?: string; note_fa?: string; ai?: Record<string, Record<string, unknown>> };
  profile_url: string; display_name: string | null; event_title: string | null; related_item_title: string | null;
  translation?: XTranslation | null;
  media?: { media_type: string; external_url: string; alt_text: string | null }[];
  history?: { action: string; previous_value_json: unknown; new_value_json: unknown; actor: string; created_at: string }[];
}

/** Local (Ollama) translation state; translated_text is present only when status is 'available'. */
export interface XTranslation {
  status: 'pending' | 'processing' | 'available' | 'needs_review' | 'failed' | 'not_required' | 'stale';
  source_language: string | null; provider: string | null; model: string | null; prompt_version: string | null;
  quality_score: number | null; quality_flags: string[]; latency_ms: number | null; translated_at: string | null;
  reviewed_at: string | null; reviewed_by: string | null; updated_at: string; translated_text: string | null;
}

export interface SocialStatus {
  mode: string; official_api: boolean; scraping: boolean; scheduler: boolean; manual_ingest_enabled: boolean;
  manifest_version: string; manifest_summary: { raw_occurrences: number; unique_accounts: number; duplicate_handles: string[] };
  accounts: number; posts: number; integration: { status: string; reason_fa: string } | null;
}
