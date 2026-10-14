'use client';
import { useApi } from './useApi';

export const AI_OFF_FA = 'قابلیت هوش مصنوعی محلی برای کاهش مصرف منابع و آماده‌سازی انتقال به سرور، موقتاً غیرفعال است.';

/** Operator switch on the server (LOCAL_AI_DISABLED_REASON). Read once per page; the 3003 API answers
 *  without contacting Ollama. off=null while unknown. */
export function useAiState(): { off: boolean | null; message: string } {
  const s = useApi<{ state: string; message_fa: string | null }>('local-ai/state');
  if (!s.data) return { off: s.error ? false : null, message: AI_OFF_FA };
  return { off: s.data.state !== 'enabled', message: s.data.message_fa || AI_OFF_FA };
}
