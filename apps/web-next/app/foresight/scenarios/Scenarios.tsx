'use client';
import { Shell } from '../../design/Shell';
import { useApi } from '../../design/useApi';
import { Empty, Failure, PageHead, AiTag, Bone } from '../../design/ui';
import { AI_STATUS } from '../../components/Briefing';
import { ForesightNote } from '../ForesightNote';

interface Resp { scenarios: unknown[]; status: string; ai: { status: string }; scope_fa: string }

export function Scenarios() {
  const q = useApi<Resp>('foresight/scenarios');
  return (
    <Shell>
      <PageHead eyebrow="آینده‌پژوهی" title="سناریوها" />
      <ForesightNote>{q.data?.scope_fa ?? 'سناریوها.'}</ForesightNote>
      {q.error && <Failure onRetry={q.reload} />}
      {!q.data && !q.error && <Bone h={120} />}
      {q.data && (
        <>
          <Empty title="هیچ سناریویی ثبت نشده است">
            سناریو فقط بر پایه پیشران‌های تأییدشده تحلیلگر و شواهد قابل پیگیری ساخته می‌شود. تا آن زمان این صفحه خالی می‌ماند و سناریوی نمونه یا نمایشی تولید نمی‌شود.
          </Empty>
          <div className="note note-ai"><AiTag>پشتیبانی هوش مصنوعی</AiTag> {AI_STATUS[q.data.ai.status] ?? q.data.ai.status}</div>
        </>
      )}
    </Shell>
  );
}
