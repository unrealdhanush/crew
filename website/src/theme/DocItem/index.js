// Wraps the stock DocItem to hand the page's Markdown source (from src/remark/raw-markdown.js) to "Copy page".
import React from 'react';
import DocItem from '@theme-original/DocItem';
import {RawMarkdownContext} from '@site/src/components/CopyPage';

export default function DocItemWrapper(props) {
  return (
    <RawMarkdownContext.Provider value={props.content?.rawMarkdown ?? null}>
      <DocItem {...props} />
    </RawMarkdownContext.Provider>
  );
}
