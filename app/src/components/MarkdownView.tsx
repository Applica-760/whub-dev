import ReactMarkdown from 'react-markdown';
import remarkFrontmatter from 'remark-frontmatter';

type MarkdownViewProps = {
  content: string;
};

export function MarkdownView({ content }: MarkdownViewProps) {
  return (
    <div className="md-view">
      <ReactMarkdown remarkPlugins={[remarkFrontmatter]} skipHtml>{content}</ReactMarkdown>
    </div>
  );
}
