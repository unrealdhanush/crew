// @ts-check
// Docs-only Docusaurus site: docs are served at the root, there's no blog, Mermaid is on, the build fails on
// broken links, and the theme in src/ gives it a clean modern look (see src/css/custom.css).
import {themes as prismThemes} from 'prism-react-renderer';
import remarkRawMarkdown from './src/remark/raw-markdown.js';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Crew',
  tagline: 'Send four people to a conference, bring back one brain.',
  favicon: 'img/logo.svg',
  url: 'http://localhost',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  markdown: {
    mermaid: true,
    hooks: {onBrokenMarkdownLinks: 'throw'},
  },
  i18n: {defaultLocale: 'en', locales: ['en']},
  customFields: {
    // "Copy page" button beside each page title. Options, in menu order (the first is the button itself):
    // 'copy' (Markdown to clipboard), 'view' (Markdown in a new tab), 'chatgpt', 'claude' (open with the page URL).
    // Turn it off for one page with `copy_page: false` in front matter.
    copyPage: {enabled: true, options: ['copy', 'view', 'chatgpt', 'claude']},
  },
  stylesheets: [
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',
  ],
  themes: [
    '@docusaurus/theme-mermaid',
    [
      '@easyops-cn/docusaurus-search-local',
      /** @type {import('@easyops-cn/docusaurus-search-local').PluginOptions} */
      ({hashed: true, indexBlog: false, docsRouteBasePath: '/', searchBarShortcutHint: true}),
    ],
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          remarkPlugins: [remarkRawMarkdown],  // feeds the "Copy page" button
        },
        blog: false,
        theme: {customCss: './src/css/custom.css'},
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {respectPrefersColorScheme: true},
      navbar: {
        title: 'Crew',
        logo: {alt: 'Crew', src: 'img/logo.svg'},
        items: [],
      },
      footer: {style: 'light', copyright: 'Crew documentation'},
      docs: {sidebar: {hideable: true}},
      tableOfContents: {minHeadingLevel: 2, maxHeadingLevel: 3},
      mermaid: {theme: {light: 'neutral', dark: 'dark'}, options: {fontFamily: 'Inter, sans-serif'}},
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.oneDark,
        additionalLanguages: ['bash', 'json', 'python', 'toml', 'yaml'],
      },
    }),
};

export default config;
