import { useState, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import ImageExtension from '@tiptap/extension-image';
import LinkExtension from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bold,
  Italic,
  Heading1,
  Link,
  ImageIcon,
  Save,
  X,
} from 'lucide-react';
import { contentsApi } from '@/api/contents';
import type { Content, ContentCreate, ContentType } from '@/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common/PageHeader';
import { cn } from '@/utils/cn';

const PLATFORM_OPTIONS = [
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'youtube', label: 'YouTube' },
] as const;

const CONTENT_TYPE_OPTIONS: { value: ContentType; label: string }[] = [
  { value: 'feed', label: 'Feed Post' },
  { value: 'reel', label: 'Reel / Short' },
  { value: 'story', label: 'Story' },
  { value: 'short', label: 'YouTube Short' },
  { value: 'card_news', label: 'Card News' },
];

interface ToolbarButtonProps {
  onClick: () => void;
  active?: boolean;
  title: string;
  children: React.ReactNode;
}

function ToolbarButton({ onClick, active, title, children }: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded transition-colors',
        active
          ? 'bg-primary text-primary-foreground'
          : 'text-foreground hover:bg-accent'
      )}
    >
      {children}
    </button>
  );
}

interface ContentEditorProps {
  initialContent?: Content;
  clientId: string;
  onSaved?: (content: Content) => void;
  onCancel?: () => void;
}

export function ContentEditor({
  initialContent,
  clientId,
  onSaved,
  onCancel,
}: ContentEditorProps) {
  const queryClient = useQueryClient();

  const [title, setTitle] = useState(initialContent?.title ?? '');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(
    initialContent?.target_platforms ?? []
  );
  const [contentType, setContentType] = useState<ContentType>(
    initialContent?.content_type ?? 'feed'
  );
  const [linkUrl, setLinkUrl] = useState('');
  const [showLinkInput, setShowLinkInput] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      ImageExtension,
      LinkExtension.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder: 'Write your content here...' }),
    ],
    content: initialContent?.body ?? '',
    editorProps: {
      attributes: {
        class:
          'prose prose-sm dark:prose-invert max-w-none min-h-[200px] p-4 focus:outline-none',
      },
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (data: ContentCreate) => {
      if (initialContent) {
        return contentsApi.update(initialContent.id, data);
      }
      return contentsApi.create(data);
    },
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ['contents'] });
      onSaved?.(res.data.data);
    },
  });

  const handleSave = () => {
    if (!title.trim()) return;
    saveMutation.mutate({
      client_id: clientId,
      title: title.trim(),
      body: editor?.getHTML() ?? '',
      content_type: contentType,
      target_platforms: selectedPlatforms,
    });
  };

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const handleSetLink = useCallback(() => {
    if (!editor) return;
    if (linkUrl) {
      editor
        .chain()
        .focus()
        .extendMarkRange('link')
        .setLink({ href: linkUrl })
        .run();
    }
    setLinkUrl('');
    setShowLinkInput(false);
  }, [editor, linkUrl]);

  const handleInsertImage = () => {
    if (!editor) return;
    const url = window.prompt('Enter image URL');
    if (url) {
      editor.chain().focus().setImage({ src: url }).run();
    }
  };

  if (!editor) return null;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={initialContent ? 'Edit Content' : 'Create Content'}
        description="Compose and configure your content"
        actions={
          <div className="flex gap-2">
            {onCancel && (
              <Button variant="outline" onClick={onCancel}>
                <X className="h-4 w-4" />
                Cancel
              </Button>
            )}
            <Button
              onClick={handleSave}
              disabled={saveMutation.isPending || !title.trim()}
            >
              <Save className="h-4 w-4" />
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        }
      />

      {saveMutation.isError && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          Failed to save content. Please try again.
        </div>
      )}

      <div className="rounded-lg border border-border bg-card shadow-sm">
        {/* Title */}
        <div className="border-b border-border p-4">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Content title..."
            className="text-lg font-semibold border-0 p-0 focus-visible:ring-0 focus-visible:ring-offset-0 h-auto"
          />
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-1 border-b border-border bg-muted/30 px-3 py-2">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            title="Bold"
          >
            <Bold className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            title="Italic"
          >
            <Italic className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            active={editor.isActive('heading', { level: 1 })}
            title="Heading"
          >
            <Heading1 className="h-4 w-4" />
          </ToolbarButton>
          <div className="mx-1 h-5 w-px bg-border" />
          <ToolbarButton
            onClick={() => setShowLinkInput((v) => !v)}
            active={editor.isActive('link') || showLinkInput}
            title="Insert Link"
          >
            <Link className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton onClick={handleInsertImage} title="Insert Image">
            <ImageIcon className="h-4 w-4" />
          </ToolbarButton>

          {/* Link input inline */}
          {showLinkInput && (
            <div className="ml-2 flex items-center gap-1">
              <Input
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                placeholder="https://..."
                className="h-7 w-48 text-xs"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSetLink();
                  if (e.key === 'Escape') setShowLinkInput(false);
                }}
                autoFocus
              />
              <Button size="sm" className="h-7 text-xs" onClick={handleSetLink}>
                Set
              </Button>
            </div>
          )}
        </div>

        {/* Editor area */}
        <EditorContent editor={editor} />
      </div>

      {/* Metadata */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Platform selector */}
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-2 text-sm font-medium text-foreground">Target Platforms</p>
          <div className="flex flex-wrap gap-2">
            {PLATFORM_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => togglePlatform(opt.value)}
                className={cn(
                  'rounded-full border px-3 py-1 text-sm transition-colors',
                  selectedPlatforms.includes(opt.value)
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-foreground hover:bg-accent'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {selectedPlatforms.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {selectedPlatforms.map((p) => (
                <Badge key={p} variant="secondary" className="text-xs">
                  {p}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Content type selector */}
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-2 text-sm font-medium text-foreground">Content Type</p>
          <div className="flex flex-wrap gap-2">
            {CONTENT_TYPE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setContentType(opt.value)}
                className={cn(
                  'rounded-full border px-3 py-1 text-sm transition-colors',
                  contentType === opt.value
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-foreground hover:bg-accent'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
