// Make the layout components available in every .md/.mdx file without imports.
import MDXComponents from '@theme-original/MDXComponents';
import Icon from '@site/src/components/Icon';
import {Card, CardGroup} from '@site/src/components/Cards';
import {Steps, Step} from '@site/src/components/Steps';

export default {...MDXComponents, Icon, Card, CardGroup, Steps, Step};
