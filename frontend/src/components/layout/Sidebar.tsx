import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  FileText,
  Home,
  MessageSquare,
  Send,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useUIStore } from '@/stores/uiStore';

const navItems = [
  { to: '/', icon: Home, label: '대시보드' },
  { to: '/content', icon: FileText, label: '콘텐츠' },
  { to: '/publishing', icon: Send, label: '게시 관리' },
  { to: '/community', icon: MessageSquare, label: '커뮤니티' },
  { to: '/analytics', icon: BarChart3, label: '성과 분석' },
  { to: '/clients', icon: Users, label: '클라이언트' },
  { to: '/ai-tools', icon: Sparkles, label: 'AI 도구' },
  { to: '/settings', icon: Settings, label: '설정' },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-30 flex h-screen flex-col border-r bg-card transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!sidebarCollapsed && (
          <span className="text-lg font-bold text-primary">SNS Solution</span>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded p-1 hover:bg-accent"
          aria-label="Toggle sidebar"
        >
          <FileText className="h-5 w-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            {!sidebarCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
