import type {ReactNode} from 'react';
/** Small, hand-adapted RTL primitives inspired by VibeFarsi's documented patterns. */
export function VfCard({children,className=''}:{children:ReactNode;className?:string}){return <section className={'vf-card '+className}>{children}</section>}
export function VfBadge({children,tone='',title}:{children:ReactNode;tone?:string;title?:string}){return <span className={'vf-badge '+tone} title={title}>{children}</span>}
export function VfStat({label,value,hint}:{label:string;value:ReactNode;hint?:string}){return <VfCard className="vf-stat"><span>{label}</span><strong>{value}</strong>{hint&&<small>{hint}</small>}</VfCard>}
export function VfTabs({value,items,onChange}:{value:string;items:[string,string][];onChange:(v:string)=>void}){return <div className="vf-tabs" role="tablist">{items.map(([k,label])=><button type="button" role="tab" aria-selected={value===k} className={value===k?'selected':''} key={k} onClick={()=>onChange(k)}>{label}</button>)}</div>}
export function VfEmptyState({title,children}:{title:string;children?:ReactNode}){return <div className="vf-empty" role="status"><strong>{title}</strong>{children&&<p>{children}</p>}</div>}
export function VfAlert({children}:{children:ReactNode}){return <div className="vf-alert" role="status">{children}</div>}
export function VfAccordion({title,children}:{title:string;children:ReactNode}){return <details className="vf-accordion"><summary>{title}</summary><div>{children}</div></details>}
export function VfTable({headers,children}:{headers:string[];children:ReactNode}){return <div className="vf-table-wrap"><table className="vf-table"><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>}
export function VfSearchInput(props:React.InputHTMLAttributes<HTMLInputElement>){return <input className="vf-search" {...props}/>}
