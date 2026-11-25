// Central taxonomy and thematic classification definitions with bilingual support.
// Covers categories, subtopics, reason codes for 'other', and story collection labels.

export interface TaxonomyItem {
  id: string;
  label_fa: string;
  label_en: string;
}

export const CATEGORIES: Record<string, TaxonomyItem> = {
  security_defense: { id: 'security_defense', label_fa: 'امنیت و دفاع', label_en: 'Security & Defense' },
  defense_industry: { id: 'defense_industry', label_fa: 'صنایع دفاعی و تسلیحات', label_en: 'Defense Industry & Arms' },
  regional_geopolitics: { id: 'regional_geopolitics', label_fa: 'منطقه و تحولات ژئوپلیتیکی', label_en: 'Regional Geopolitics' },
  politics_governance: { id: 'politics_governance', label_fa: 'سیاست و حکمرانی', label_en: 'Politics & Governance' },
  diplomacy_international: { id: 'diplomacy_international', label_fa: 'دیپلماسی و روابط بین‌الملل', label_en: 'Diplomacy & Foreign Relations' },
  economy_trade_sanctions: { id: 'economy_trade_sanctions', label_fa: 'اقتصاد، تجارت و تحریم', label_en: 'Economy, Trade & Sanctions' },
  energy_infrastructure: { id: 'energy_infrastructure', label_fa: 'انرژی و زیرساخت', label_en: 'Energy & Infrastructure' },
  technology_cyber_ai: { id: 'technology_cyber_ai', label_fa: 'فناوری، سایبری و هوش مصنوعی', label_en: 'Technology, Cyber & AI' },
  aerospace_maritime: { id: 'aerospace_maritime', label_fa: 'حمل‌ونقل، هوافضا و دریایی', label_en: 'Aerospace & Maritime' },
  society_human_rights: { id: 'society_human_rights', label_fa: 'جامعه و حقوق بشر', label_en: 'Society & Human Rights' },
  environment_crisis: { id: 'environment_crisis', label_fa: 'محیط زیست و بحران', label_en: 'Environment & Crisis' },
  other: { id: 'other', label_fa: 'سایر', label_en: 'Other' },

  // Taxonomy v2 / Legacy compatibility
  politics_geopolitics: { id: 'politics_geopolitics', label_fa: 'سیاست و ژئوپلیتیک', label_en: 'Politics & Geopolitics' },
  technology: { id: 'technology', label_fa: 'فناوری', label_en: 'Technology' },
  economy_infrastructure: { id: 'economy_infrastructure', label_fa: 'اقتصاد و زیرساخت', label_en: 'Economy & Infrastructure' },
  strategic: { id: 'strategic', label_fa: 'راهبردی', label_en: 'Strategic' },
  social_humanitarian: { id: 'social_humanitarian', label_fa: 'اجتماعی و انسانی مرتبط', label_en: 'Social & Humanitarian' },
};

export const SUBTOPICS: Record<string, TaxonomyItem> = {
  air_defense: { id: 'air_defense', label_fa: 'پدافند هوایی', label_en: 'Air Defense' },
  missile: { id: 'missile', label_fa: 'موشکی', label_en: 'Missile Systems' },
  drone: { id: 'drone', label_fa: 'پهپادی', label_en: 'Drones & UAVs' },
  air_force: { id: 'air_force', label_fa: 'نیروی هوایی', label_en: 'Air Force' },
  navy: { id: 'navy', label_fa: 'نیروی دریایی', label_en: 'Navy & Maritime Forces' },
  ground_forces: { id: 'ground_forces', label_fa: 'نیروی زمینی', label_en: 'Ground Forces' },
  exercises_operations: { id: 'exercises_operations', label_fa: 'رزمایش و عملیات', label_en: 'Exercises & Operations' },
  intelligence_security: { id: 'intelligence_security', label_fa: 'اطلاعاتی و امنیتی', label_en: 'Intelligence & Security' },
  nuclear_deterrence: { id: 'nuclear_deterrence', label_fa: 'هسته‌ای و بازدارندگی', label_en: 'Nuclear & Deterrence' },
  arms_exports: { id: 'arms_exports', label_fa: 'صادرات و فروش تسلیحات', label_en: 'Arms Exports' },
  procurement: { id: 'procurement', label_fa: 'تدارکات و قراردادها', label_en: 'Procurement & Contracts' },
  production_capacity: { id: 'production_capacity', label_fa: 'ظرفیت تولید', label_en: 'Production Capacity' },
  iran_axis: { id: 'iran_axis', label_fa: 'ایران و محور مقاومت', label_en: 'Iran & Resistance Axis' },
  gulf_maritime: { id: 'gulf_maritime', label_fa: 'خلیج فارس و آبراه‌ها', label_en: 'Persian Gulf & Waterways' },
  great_powers: { id: 'great_powers', label_fa: 'رقابت قدرت‌های بزرگ', label_en: 'Great Power Competition' },
  russia_ukraine: { id: 'russia_ukraine', label_fa: 'جنگ روسیه و اوکراین', label_en: 'Russia-Ukraine War' },
  israel_palestine: { id: 'israel_palestine', label_fa: 'اسرائیل و فلسطین', label_en: 'Israel & Palestine' },
};

export const OTHER_REASONS: Record<string, TaxonomyItem> = {
  off_mission_lifestyle: { id: 'off_mission_lifestyle', label_fa: 'خارج از مأموریت: سبک زندگی و سرگرمی', label_en: 'Off-mission: Lifestyle & Entertainment' },
  event_listing: { id: 'event_listing', label_fa: 'اطلاعیه رویداد، پادکست یا نشست', label_en: 'Event Listing, Podcast or Webinar' },
  local_incident: { id: 'local_incident', label_fa: 'حادثه یا جرم محلی بدون پیوند امنیتی شناسایی‌شده', label_en: 'Local Incident' },
  weak_signal: { id: 'weak_signal', label_fa: 'شواهد ناکافی (فقط یک اشاره در متن)', label_en: 'Weak Signal' },
  no_keyword_match: { id: 'no_keyword_match', label_fa: 'هیچ قاعده‌ای منطبق نشد', label_en: 'No Keyword Match' },
};

export const STORY_COLLECTIONS: Record<string, TaxonomyItem> = {
  'گزارش': { id: 'briefing', label_fa: 'گزارش', label_en: 'Report' },
  'briefing': { id: 'briefing', label_fa: 'گزارش', label_en: 'Report' },
  'تحول روز': { id: 'today', label_fa: 'تحول روز', label_en: 'Daily Focus' },
  'today': { id: 'today', label_fa: 'تحول روز', label_en: 'Daily Focus' },
  'فوری': { id: 'breaking', label_fa: 'فوری', label_en: 'Breaking' },
  'breaking': { id: 'breaking', label_fa: 'فوری', label_en: 'Breaking' },
  'رویدادها': { id: 'events', label_fa: 'رویدادها', label_en: 'Events' },
  'events': { id: 'events', label_fa: 'رویدادها', label_en: 'Events' },
  'موضوع داغ': { id: 'topic', label_fa: 'موضوع داغ', label_en: 'Hot Topic' },
  'topic': { id: 'topic', label_fa: 'موضوع داغ', label_en: 'Hot Topic' },
  'منابع': { id: 'sources', label_fa: 'منابع', label_en: 'Sources' },
  'sources': { id: 'sources', label_fa: 'منابع', label_en: 'Sources' },
  'سیگنال': { id: 'weak_signals', label_fa: 'سیگنال', label_en: 'Signals' },
  'weak_signals': { id: 'weak_signals', label_fa: 'سیگنال', label_en: 'Signals' },
  'پرونده': { id: 'dossier', label_fa: 'پرونده', label_en: 'Dossier' },
  'dossier': { id: 'dossier', label_fa: 'پرونده', label_en: 'Dossier' },
};

const FA_TO_CATEGORY: Record<string, TaxonomyItem> = {};
for (const item of Object.values(CATEGORIES)) {
  FA_TO_CATEGORY[item.label_fa] = item;
  FA_TO_CATEGORY[item.id] = item;
}

const FA_TO_SUBTOPIC: Record<string, TaxonomyItem> = {};
for (const item of Object.values(SUBTOPICS)) {
  FA_TO_SUBTOPIC[item.label_fa] = item;
  FA_TO_SUBTOPIC[item.id] = item;
}

const FA_TO_REASON: Record<string, TaxonomyItem> = {};
for (const item of Object.values(OTHER_REASONS)) {
  FA_TO_REASON[item.label_fa] = item;
  FA_TO_REASON[item.id] = item;
}

/** Get localized Category label from either id or existing label string. */
export function getCategoryLabel(idOrLabel: string | null | undefined, isEn: boolean): string {
  if (!idOrLabel) return '';
  const item = FA_TO_CATEGORY[idOrLabel] || CATEGORIES[idOrLabel];
  if (item) return isEn ? item.label_en : item.label_fa;
  return idOrLabel;
}

/** Get localized Subtopic label from either id or existing label string. */
export function getSubtopicLabel(idOrLabel: string | null | undefined, isEn: boolean): string {
  if (!idOrLabel) return '';
  const item = FA_TO_SUBTOPIC[idOrLabel] || SUBTOPICS[idOrLabel];
  if (item) return isEn ? item.label_en : item.label_fa;
  return idOrLabel;
}

/** Get localized Reason label for 'other' from either code or existing label string. */
export function getOtherReasonLabel(codeOrLabel: string | null | undefined, isEn: boolean): string {
  if (!codeOrLabel) return '';
  const item = FA_TO_REASON[codeOrLabel] || OTHER_REASONS[codeOrLabel];
  if (item) return isEn ? item.label_en : item.label_fa;
  return codeOrLabel;
}

/** Get localized collection label for stories from either kind or label. */
export function getCollectionLabel(labelOrKind: string | null | undefined, isEn: boolean): string {
  if (!labelOrKind) return '';
  const item = STORY_COLLECTIONS[labelOrKind];
  if (item) return isEn ? item.label_en : item.label_fa;
  return labelOrKind;
}
