// Remark plugin: exports each doc's Markdown source, minus its front matter, as `rawMarkdown`,
// so the "Copy page" button can copy the page exactly as written. Each page only carries its own source.
export default function remarkRawMarkdown() {
  return (tree, file) => {
    const source = String(file.value ?? '').replace(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(\r?\n|$)/, '').trimStart();
    tree.children.unshift({
      type: 'mdxjsEsm',
      value: '',
      data: {
        estree: {
          type: 'Program',
          sourceType: 'module',
          body: [{
            type: 'ExportNamedDeclaration',
            specifiers: [],
            source: null,
            declaration: {
              type: 'VariableDeclaration',
              kind: 'const',
              declarations: [{
                type: 'VariableDeclarator',
                id: {type: 'Identifier', name: 'rawMarkdown'},
                init: {type: 'Literal', value: source, raw: JSON.stringify(source)},
              }],
            },
          }],
        },
      },
    });
  };
}
