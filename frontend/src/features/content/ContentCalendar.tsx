import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  format,
  isSameDay,
  addMonths,
  subMonths,
  startOfWeek,
  endOfWeek,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  useDraggable,
  useDroppable,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { contentsApi } from '@/api/contents';
import type { Content, ContentStatus } from '@/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common/PageHeader';
import { cn } from '@/utils/cn';

const STATUS_STYLES: Record<ContentStatus, string> = {
  draft: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  review: 'bg-yellow-200 text-yellow-800 dark:bg-yellow-800/40 dark:text-yellow-300',
  client_review: 'bg-orange-200 text-orange-800 dark:bg-orange-800/40 dark:text-orange-300',
  approved: 'bg-green-200 text-green-800 dark:bg-green-800/40 dark:text-green-300',
  published: 'bg-blue-200 text-blue-800 dark:bg-blue-800/40 dark:text-blue-300',
  rejected: 'bg-red-200 text-red-800 dark:bg-red-800/40 dark:text-red-300',
};

const STATUS_LABELS: Record<ContentStatus, string> = {
  draft: 'Draft',
  review: 'Review',
  client_review: 'Client',
  approved: 'Approved',
  published: 'Published',
  rejected: 'Rejected',
};

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function DraggableContentChip({ content }: { content: Content }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: content.id,
    data: { content },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        'truncate rounded px-1 py-0.5 text-xs font-medium cursor-grab active:cursor-grabbing',
        STATUS_STYLES[content.status],
        isDragging && 'opacity-50'
      )}
      title={content.title}
    >
      {content.title}
    </div>
  );
}

function DroppableDayCell({
  day,
  isCurrentMonth,
  isToday,
  dayContents,
  isLastCol,
  onDateClick,
}: {
  day: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  dayContents: Content[];
  isLastCol: boolean;
  onDateClick?: (date: Date, contents: Content[]) => void;
}) {
  const dateStr = format(day, 'yyyy-MM-dd');
  const { setNodeRef, isOver } = useDroppable({ id: dateStr });

  return (
    <div
      ref={setNodeRef}
      onClick={() => onDateClick?.(day, dayContents)}
      className={cn(
        'min-h-[100px] border-b border-r border-border p-1 transition-colors',
        isCurrentMonth ? 'bg-card' : 'bg-muted/30',
        onDateClick && 'cursor-pointer hover:bg-accent/50',
        isLastCol && 'border-r-0',
        isOver && 'bg-accent/70 ring-2 ring-primary ring-inset'
      )}
    >
      <div
        className={cn(
          'mb-1 flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium',
          isToday
            ? 'bg-primary text-primary-foreground'
            : isCurrentMonth
            ? 'text-foreground'
            : 'text-muted-foreground'
        )}
      >
        {format(day, 'd')}
      </div>
      <div className="flex flex-col gap-0.5 overflow-hidden">
        {dayContents.slice(0, 3).map((content) => (
          <DraggableContentChip key={content.id} content={content} />
        ))}
        {dayContents.length > 3 && (
          <div className="px-1 text-xs text-muted-foreground">
            +{dayContents.length - 3} more
          </div>
        )}
      </div>
    </div>
  );
}

interface ContentCalendarProps {
  clientId?: string;
  onDateClick?: (date: Date, contents: Content[]) => void;
}

export function ContentCalendar({ clientId, onDateClick }: ContentCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const calStart = startOfWeek(monthStart);
  const calEnd = endOfWeek(monthEnd);

  const { data, isLoading } = useQuery({
    queryKey: ['calendar', format(monthStart, 'yyyy-MM'), clientId],
    queryFn: async () => {
      const res = await contentsApi.calendar(
        format(calStart, 'yyyy-MM-dd'),
        format(calEnd, 'yyyy-MM-dd'),
        clientId
      );
      return res.data.data;
    },
  });

  const queryClient = useQueryClient();
  const allDays = eachDayOfInterval({ start: calStart, end: calEnd });
  const [activeContent, setActiveContent] = useState<Content | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const rescheduleMutation = useMutation({
    mutationFn: ({ contentId, newDate }: { contentId: string; newDate: string }) =>
      contentsApi.update(contentId, { scheduled_at: newDate } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
    },
  });

  const getContentsForDay = (day: Date): Content[] => {
    if (!data) return [];
    return data.filter((c) => {
      const dateStr = c.scheduled_at ?? c.published_at ?? c.created_at;
      return isSameDay(new Date(dateStr), day);
    });
  };

  const handleDragStart = (event: any) => {
    const content = event.active.data.current?.content;
    if (content) setActiveContent(content);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveContent(null);
    const { active, over } = event;
    if (!over) return;

    const content = active.data.current?.content as Content | undefined;
    if (!content) return;

    const newDateStr = over.id as string; // 'yyyy-MM-dd'
    const currentDateStr = content.scheduled_at ?? content.published_at ?? content.created_at;
    const currentDay = format(new Date(currentDateStr), 'yyyy-MM-dd');

    if (currentDay !== newDateStr) {
      rescheduleMutation.mutate({
        contentId: content.id,
        newDate: `${newDateStr}T${format(new Date(currentDateStr), 'HH:mm:ss')}`,
      });
    }
  };

  const handlePrevMonth = () => setCurrentMonth((d) => subMonths(d, 1));
  const handleNextMonth = () => setCurrentMonth((d) => addMonths(d, 1));
  const handleToday = () => setCurrentMonth(new Date());

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Content Calendar"
        description="View and manage scheduled content by date"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleToday}>
              Today
            </Button>
            <Button variant="outline" size="icon" onClick={handlePrevMonth} aria-label="Previous month">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-[160px] text-center text-sm font-semibold">
              {format(currentMonth, 'MMMM yyyy')}
            </span>
            <Button variant="outline" size="icon" onClick={handleNextMonth} aria-label="Next month">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {(Object.keys(STATUS_STYLES) as ContentStatus[]).map((status) => (
          <Badge key={status} className={cn('text-xs', STATUS_STYLES[status])}>
            {STATUS_LABELS[status]}
          </Badge>
        ))}
      </div>

      {/* Calendar grid */}
      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="rounded-lg border border-border bg-card shadow-sm">
          {/* Day headers */}
          <div className="grid grid-cols-7 border-b border-border">
            {DAY_NAMES.map((day) => (
              <div
                key={day}
                className="py-2 text-center text-xs font-medium text-muted-foreground"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar cells */}
          {isLoading ? (
            <div className="flex h-96 items-center justify-center text-muted-foreground text-sm">
              Loading calendar...
            </div>
          ) : (
            <div className="grid grid-cols-7">
              {allDays.map((day, idx) => {
                const dayContents = getContentsForDay(day);
                const isCurrentMonth = format(day, 'MM') === format(currentMonth, 'MM');
                const isToday = isSameDay(day, new Date());

                return (
                  <DroppableDayCell
                    key={idx}
                    day={day}
                    isCurrentMonth={isCurrentMonth}
                    isToday={isToday}
                    dayContents={dayContents}
                    isLastCol={idx % 7 === 6}
                    onDateClick={onDateClick}
                  />
                );
              })}
            </div>
          )}
        </div>

        <DragOverlay>
          {activeContent && (
            <div
              className={cn(
                'truncate rounded px-1 py-0.5 text-xs font-medium shadow-lg',
                STATUS_STYLES[activeContent.status]
              )}
            >
              {activeContent.title}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
