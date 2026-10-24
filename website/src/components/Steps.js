// <Steps> <Step title="Install">…markdown…</Step> </Steps>  (numbered, with a line connecting the steps)
// Leave blank lines around markdown inside a Step so it renders as markdown.
import React from 'react';

export function Steps({children}) {
  return <div className="dx-steps">{children}</div>;
}

export function Step({title, children}) {
  return (
    <div className="dx-step">
      <div className="dx-step__title">{title}</div>
      <div className="dx-step__body">{children}</div>
    </div>
  );
}
