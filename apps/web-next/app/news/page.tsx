import {Suspense} from 'react';
import Monitor from '../monitor';
export default function Page(){return <Suspense fallback={<p className="loading" role="status">در حال دریافت داده از PostgreSQL…</p>}><Monitor mode="news"/></Suspense>}
