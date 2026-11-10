import { redirect } from 'next/navigation';

// Retired route. v2 category ids map to their nearest v3 topic.
const V2_TO_V3: Record<string, string> = {
  politics_geopolitics: 'regional_geopolitics', technology: 'technology_cyber_ai', economy_infrastructure: 'economy_trade_sanctions',
  strategic: 'security_defense', social_humanitarian: 'society_human_rights',
};

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect('/topics/' + encodeURIComponent(V2_TO_V3[id] ?? id));
}
