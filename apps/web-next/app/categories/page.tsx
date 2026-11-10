import { redirect } from 'next/navigation';

// Retired route: categories are now topics (taxonomy v3).
export default function Page() {
  redirect('/topics');
}
