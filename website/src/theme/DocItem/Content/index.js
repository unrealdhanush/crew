// The stock DocItem/Content from @docusaurus/theme-classic 3.10, plus the page's front matter `description`
// shown as a subtitle under the title, and the "Copy page" button beside it.
import React from 'react';
import clsx from 'clsx';
import {ThemeClassNames} from '@docusaurus/theme-common';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import Heading from '@theme/Heading';
import MDXContent from '@theme/MDXContent';
import CopyPage from '@site/src/components/CopyPage';

export default function DocItemContent({children}) {
  const {metadata, frontMatter, contentTitle} = useDoc();
  const syntheticTitle = !frontMatter.hide_title && typeof contentTitle === 'undefined' ? metadata.title : null;
  return (
    <div className={clsx(ThemeClassNames.docs.docMarkdown, 'markdown')}>
      {syntheticTitle && (
        <header className="dx-doc-header">
          <div className="dx-doc-title">
            <Heading as="h1">{syntheticTitle}</Heading>
            <CopyPage />
          </div>
          {frontMatter.description && <p className="dx-subtitle">{frontMatter.description}</p>}
        </header>
      )}
      <MDXContent>{children}</MDXContent>
    </div>
  );
}
