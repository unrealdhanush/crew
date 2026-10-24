// <CardGroup cols={2}> <Card title="…" icon="rocket" href="/getting-started/quickstart">Text</Card> </CardGroup>
// href takes a site route (not a .md path); the build still checks it for broken links.
import React from 'react';
import Link from '@docusaurus/Link';
import Icon from './Icon';

export function Card({title, icon, href, children}) {
  const body = (
    <>
      {icon && <span className="dx-card__icon"><Icon name={icon} /></span>}
      {title && <span className="dx-card__title">{title}</span>}
      {children && <div className="dx-card__body">{children}</div>}
    </>
  );
  return href
    ? <Link className="dx-card dx-card--link" to={href}>{body}</Link>
    : <div className="dx-card">{body}</div>;
}

export function CardGroup({cols = 2, children}) {
  return <div className="dx-cards" style={{'--dx-cols': cols}}>{children}</div>;
}
