// "Copy page" button with a menu: copy as Markdown, view as Markdown, open in ChatGPT / Claude.
// Configured in docusaurus.config.js under customFields.copyPage:
//   {enabled: true, options: ['copy', 'view', 'chatgpt', 'claude']}
// and switched off for one page with `copy_page: false` in its front matter.
import React, {createContext, useContext, useEffect, useRef, useState} from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import Icon from './Icon';

export const RawMarkdownContext = createContext(null);

const DEFAULTS = {enabled: true, options: ['copy', 'view', 'chatgpt', 'claude']};

const ACTIONS = {
  copy: {icon: 'copy', title: 'Copy page', text: 'Copy this page as Markdown for LLMs'},
  view: {icon: 'file-text', title: 'View as Markdown', text: 'Open this page as plain text'},
  chatgpt: {icon: 'message', title: 'Open in ChatGPT', text: 'Ask questions about this page', external: true},
  claude: {icon: 'sparkles', title: 'Open in Claude', text: 'Ask questions about this page', external: true},
};

export function useCopyPageConfig() {
  const {siteConfig} = useDocusaurusContext();
  const {frontMatter} = useDoc();
  const config = {...DEFAULTS, ...(siteConfig.customFields?.copyPage ?? {})};
  const options = (config.options ?? []).filter((o) => ACTIONS[o]);
  return {enabled: Boolean(config.enabled) && frontMatter.copy_page !== false && options.length > 0, options};
}

async function writeClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  const area = Object.assign(document.createElement('textarea'), {value: text});
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  document.execCommand('copy');  // fallback for plain-http hosts, where the clipboard API is unavailable
  area.remove();
}

export default function CopyPage() {
  const raw = useContext(RawMarkdownContext);
  const {metadata, frontMatter, contentTitle} = useDoc();
  const {enabled, options} = useCopyPageConfig();
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const root = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => (e.type === 'keydown' ? e.key === 'Escape' : !root.current?.contains(e.target)) && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  if (!enabled || raw === null) return null;

  const markdown = () => {
    const header = contentTitle ? '' : `# ${metadata.title}\n\n${frontMatter.description ? `${frontMatter.description}\n\n` : ''}`;
    return `${header}${raw.trim()}\n`;
  };
  const ask = () => `Read ${window.location.href} so I can ask questions about it.`;

  const run = async (action) => {
    setOpen(false);
    if (action === 'copy') {
      await writeClipboard(markdown());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else if (action === 'view') {
      window.open(URL.createObjectURL(new Blob([markdown()], {type: 'text/plain;charset=utf-8'})), '_blank');
    } else if (action === 'chatgpt') {
      window.open(`https://chatgpt.com/?hints=search&q=${encodeURIComponent(ask())}`, '_blank', 'noopener');
    } else if (action === 'claude') {
      window.open(`https://claude.ai/new?q=${encodeURIComponent(ask())}`, '_blank', 'noopener');
    }
  };

  const [primary, ...rest] = options;
  return (
    <div className="dx-copy" ref={root}>
      <button type="button" className="dx-copy__main" onClick={() => run(primary)}>
        <Icon name={primary === 'copy' && copied ? 'check' : ACTIONS[primary].icon} size={15} />
        {primary === 'copy' && copied ? 'Copied' : ACTIONS[primary].title}
      </button>
      {rest.length > 0 && (
        <button type="button" className="dx-copy__toggle" aria-label="More page actions" aria-expanded={open}
                onClick={() => setOpen((v) => !v)}>
          <Icon name="chevron-down" size={15} />
        </button>
      )}
      {open && (
        <div className="dx-copy__menu" role="menu">
          {options.map((key) => (
            <button key={key} type="button" role="menuitem" className="dx-copy__item" onClick={() => run(key)}>
              <span className="dx-copy__icon"><Icon name={ACTIONS[key].icon} size={16} /></span>
              <span>
                <span className="dx-copy__title">
                  {ACTIONS[key].title}
                  {ACTIONS[key].external && <Icon name="external-link" size={12} />}
                </span>
                <span className="dx-copy__text">{ACTIONS[key].text}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
