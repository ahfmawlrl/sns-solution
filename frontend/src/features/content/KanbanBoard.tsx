import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { format } from 'date-fns';
import { GripVertical, Instagram, Facebook, Youtube } from 'lucide-react';
import { contentsApi } from '@/api/contents';
import type { Content, ContentStatus } from '@/types';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageHeader } from '@/components/common/PageHeader';
import { cn } from '@/utils/cn';

type KanbanColumn = {
  id: ContentStatus;
  label: string;
  color: string;
  headerBg: string;
};

const COLUMNS: KanbanColumn[] = [
  { id: 'draft', label: 'Draft', color: 'text-gray-600', headerBg: 'bg-gray-100 dark:bg-gray-800' },
  { id: 'review', label: 'Review', color: 'text-yellow-700', headerBg: 'bg-yellow-50 dark:bg-yellow-900/20' },
  { id: 'client_review', label: 'Client Review', color: 'text-orange-700', headerBg: 'bg-orange-50 dark:bg-orange-900/20' },
  { id: 'approved', label: 'Approved', color: 'text-green-700', headerBg: 'bg-green-50 dark:bg-green-900/20' },
];

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  instagram: <Instagram className="h-3 w-3" />,
  facebook: <Facebook className="h-3 w-3" />,
  youtube: <Youtube className="h-3 w-3" />,
};

interface KanbanCardProps {
  content: Content;
  isDragging?: boolean;
}

function KanbanCard({ content, isDragging }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: content.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Card
        className={cn(
          'mb-2 cursor-grab p-3 active:cursor-grabbing',
          isDragging && 'ring-2 ring-primary'
        )}
      >
        <div className="flex items-start gap-2">
          <button
            {...attributes}
            {...listeners}
            className="mt-0.5 text-muted-foreground hover:text-foreground"
            aria-label="Drag handle"
          >
            <GripVertical className="h-4 w-4" />
          </button>
          <div className="flex-1 overflow-hidden">
            <p className="mb-1 truncate text-sm font-medium text-foreground">
              {content.title}
            </p>
            <div className="flex flex-wrap gap-1">
              {content.target_platforms.map((platform) => (
                <span
                  key={platform}
                  className="flex items-center gap-0.5 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
                >
                  {PLATFORM_ICONS[platform] ?? null}
                  {platform}
                </span>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">
              {format(new Date(content.created_at), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

interface ColumnProps {
  column: KanbanColumn;
  contents: Content[];
  activeId: string | null;
}

function KanbanColumn({ column, contents, activeId }: ColumnProps) {
  return (
    <div className="flex min-h-[400px] w-64 flex-shrink-0 flex-col rounded-lg border border-border bg-muted/30">
      <div className={cn('rounded-t-lg px-3 py-2', column.headerBg)}>
        <div className="flex items-center justify-between">
          <span className={cn('text-sm font-semibold', column.color)}>
            {column.label}
          </span>
          <Badge variant="secondary" className="text-xs">
            {contents.length}
          </Badge>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        <SortableContext
          items={contents.map((c) => c.id)}
          strategy={verticalListSortingStrategy}
        >
          {contents.map((content) => (
            <KanbanCard
              key={content.id}
              content={content}
              isDragging={activeId === content.id}
            />
          ))}
        </SortableContext>
        {contents.length === 0 && (
          <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
            No items
          </div>
        )}
      </div>
    </div>
  );
}

interface KanbanBoardProps {
  clientId?: string;
}

export function KanbanBoard({ clientId }: KanbanBoardProps) {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const { data: contents = [], isLoading } = useQuery({
    queryKey: ['contents', 'kanban', clientId],
    queryFn: async () => {
      const params: Record<string, string> = { per_page: '200' };
      if (clientId) params.client_id = clientId;
      const res = await contentsApi.list(params);
      return res.data.data;
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ContentStatus }) =>
      contentsApi.changeStatus(id, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['contents', 'kanban'] });
    },
  });

  const getColumnContents = (status: ContentStatus) =>
    contents.filter((c) => c.status === status);

  const findActiveContent = () =>
    contents.find((c) => c.id === activeId) ?? null;

  const findColumnForContent = (contentId: string): ContentStatus | null => {
    const content = contents.find((c) => c.id === contentId);
    return content?.status ?? null;
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeContentId = String(active.id);
    const overId = String(over.id);

    // Check if dropped on a column or another card
    const targetColumn = COLUMNS.find((col) => col.id === overId);
    let targetStatus: ContentStatus | null = null;

    if (targetColumn) {
      targetStatus = targetColumn.id;
    } else {
      targetStatus = findColumnForContent(overId);
    }

    const currentStatus = findColumnForContent(activeContentId);

    if (targetStatus && currentStatus !== targetStatus) {
      updateStatusMutation.mutate({ id: activeContentId, status: targetStatus });
    }
  };

  const activeContent = findActiveContent();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        Loading board...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Content Board"
        description="Drag and drop to move content through the workflow"
      />
      <div className="overflow-x-auto pb-4">
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4">
            {COLUMNS.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                contents={getColumnContents(column.id)}
                activeId={activeId}
              />
            ))}
          </div>
          <DragOverlay>
            {activeContent ? (
              <Card className="w-64 cursor-grabbing p-3 shadow-lg">
                <p className="truncate text-sm font-medium">{activeContent.title}</p>
              </Card>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  );
}
