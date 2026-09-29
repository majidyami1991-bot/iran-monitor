'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ExternalLink } from 'lucide-react';
import { Shell } from '../../../design/Shell';
import { useApi, useNow } from '../../../design/useApi';
import { fmt, fmtDateTime } from '../../../design/format';
import { Bone, Empty, Failure, PageHead, Tag } from '../../../design/ui';
import { PostCard } from '../../PostCard';
import { useTopicLabels } from '../../Social';
import type { XAccount, XPost } from '../../lib';

export default function Page() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const q = useApi<XAccount & { posts: XPost[] }>('social/accounts/' + encodeURIComponent(sourceId), [sourceId]);
  const now = useNow();
  const { label } = useTopicLabels();
  if (q.error) return <Shell><Failure onRetry={q.reload}>این حساب در فهرست منابع پیدا نشد.</Failure></Shell>;
  if (!q.data) return <Shell><Bone h={28} w="40%" /><Bone h={120} /></Shell>;
  const a = q.data;
  return (
    <Shell>
      <nav className="muted" aria-label="مسیر"><Link href="/social">شبکه‌های اجتماعی</Link></nav>
      <PageHead eyebrow="حساب X · پایش دستی" title={a.handle}>
        <a href={a.profile_url} target="_blank" rel="noopener noreferrer nofollow" className="btn-ghost">پروفایل در X<ExternalLink size={14} /></a>
      </PageHead>
      <div className="detail">
        <section className="detail-main">
          <h2 className="brief-sub">پست‌های ثبت‌شده ({fmt(a.posts.length)})</h2>
          {a.posts.length === 0
            ? <Empty title="هنوز پستی از این حساب ثبت نشده است">پست‌ها فقط با ثبت دستی نشانی پست توسط تحلیلگر اضافه می‌شوند.</Empty>
            : <div className="x-list">{a.posts.map((p) => <PostCard key={p.post_id} p={p} now={now} topicLabel={label} />)}</div>}
        </section>
        <aside className="side">
          <section className="panel">
            <div className="panel-title"><h3>شناسنامه حساب</h3></div>
            <dl className="kv">
              <dt>حساب</dt><dd dir="ltr">{a.handle}</dd>
              <dt>نام ثبت‌شده</dt><dd>{a.display_name ?? <span className="muted">ثبت نشده</span>}</dd>
              <dt>توضیح</dt><dd>{a.description ?? <span className="muted">ثبت نشده</span>}</dd>
              <dt>دسته</dt><dd>{a.category ?? <span className="muted">ثبت نشده</span>}</dd>
              <dt>روش پایش</dt><dd><Tag tone="info">دستی</Tag> <span className="muted">API رسمی و زمان‌بند خاموش</span></dd>
              <dt>پست ثبت‌شده</dt><dd>{fmt(a.post_count)}</dd>
              <dt>آخرین ثبت</dt><dd>{a.last_manual_post_at ? fmtDateTime(a.last_manual_post_at) : '—'}</dd>
              <dt>منشأ</dt><dd>{a.provenance_json.map((p, i) => <span key={i} className="muted" style={{ display: 'block' }}>sites.docx · جدول {fmt(p.table_index)} · ردیف {fmt(p.row_index)}</span>)}</dd>
            </dl>
          </section>
        </aside>
      </div>
    </Shell>
  );
}
