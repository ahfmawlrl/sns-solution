# 03. 프론트엔드 아키텍처

## 기술 스택

- **React 18** + TypeScript (strict mode)
- **Vite** — 빌드/개발 서버
- **Tailwind CSS** + **shadcn/ui** (Radix UI 기반) — 유틸리티 퍼스트 + 접근성 내장
- **Zustand** — 클라이언트 전역 상태
- **TanStack Query v5** (React Query) — 서버 상태 캐싱/동기화
- **React Router v6** — 라우팅
- **Axios** — HTTP 클라이언트 + Interceptor
- **Recharts** — 기본 차트 시각화 (KPI, 트렌드, 성과 비교)
- **@dnd-kit** — 드래그 앤 드롭 (캘린더, 칸반)
- **TipTap** — 리치 텍스트 에디터
- **react-dropzone** — 파일 업로드
- **date-fns** — 날짜 처리
- **Zod** — 스키마 검증 (폼 + API 응답)
- **React Hook Form** — 폼 상태 관리

---

## 1. 페이지 라우팅 (12 routes)

```tsx
// Router.tsx — React Router v6
const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,          // Sidebar + Header + Outlet
    children: [
      { index: true,          element: <DashboardPage /> },
      { path: "content",      element: <ContentPage /> },
      { path: "content/create", element: <ContentEditor /> },
      { path: "content/:id",  element: <ContentDetail /> },
      { path: "publishing",   element: <PublishingPage /> },
      { path: "community",    element: <CommunityPage /> },
      { path: "analytics",    element: <AnalyticsPage /> },
      { path: "clients",      element: <ClientsPage /> },
      { path: "clients/:id",  element: <ClientDetail /> },
      { path: "ai-tools",     element: <AIToolsPage /> },
      { path: "settings",     element: <SettingsPage /> },
      { path: "settings/users", element: <UserManagementPage /> },
    ],
  },
  { path: "/login",  element: <LoginPage /> },
  { path: "*",       element: <NotFoundPage /> },
]);
```

**화면 설계서 메뉴 매핑**:
| 사이드바 메뉴 | 라우트 | 2차 메뉴 구현 |
|-------------|-------|-------------|
| 📊 대시보드 | `/` | 탭: 전체현황 / 클라이언트별 / AI인사이트 |
| ✏️ 콘텐츠 관리 | `/content` | 탭: 캘린더 / 칸반보드 / 라이브러리 |
| 🚀 게시 운영 | `/publishing` | 탭: 전체 / 예약대기 / 게시완료 / 실패 |
| 💬 커뮤니티 관리 | `/community` | 탭: 통합인박스 / 감성분석 / 필터규칙 / 가이드라인 |
| 📈 성과 분석 | `/analytics` | 탭: 대시보드 / AI리포트 / 경쟁사 / 예측 |
| 👤 클라이언트 | `/clients` | 목록→상세 드릴다운 |
| 🤖 AI 도구 | `/ai-tools` | 탭: 카피라이터 / 이미지생성 / 영상편집 |
| ⚙️ 설정 | `/settings` | 탭: 플랫폼연동 / 워크플로우 / 알림설정 / 사용자관리 |

---

## 2. 전역 상태 관리 (Zustand 5개 Store)

```typescript
// stores/authStore.ts
interface AuthStore {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  permissions: string[];
  login: (token: string, user: User) => void;
  logout: () => void;
  updateProfile: (user: Partial<User>) => void;
}

// stores/clientStore.ts
interface ClientStore {
  selectedClient: Client | null;      // 상단 헤더 클라이언트 전환
  clientList: Client[];
  setSelectedClient: (client: Client) => void;
  fetchClients: () => Promise<void>;
}

// stores/uiStore.ts
interface UIStore {
  sidebarCollapsed: boolean;          // 사이드바 접힘/펼침
  theme: "light" | "dark";
  toggleSidebar: () => void;
  setTheme: (theme: string) => void;
}

// stores/chatStore.ts
interface ChatStore {
  messages: ChatMessage[];
  isOpen: boolean;                    // 플로팅 패널 열림/닫힘
  isStreaming: boolean;               // SSE 스트리밍 중
  conversationId: string | null;
  sendMessage: (msg: string) => void;
  toggleChat: () => void;
}

// stores/notificationStore.ts
interface NotificationStore {
  unreadCount: number;
  notifications: Notification[];
  wsConnection: WebSocket | null;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (id: string) => void;
  markAllRead: () => void;
  connectWebSocket: () => void;
}
```

---

## 3. React Query 전략

```typescript
// api/client.ts — Axios 인스턴스
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
});

// Interceptor: 401 → 자동 토큰 갱신 → 실패 시 /login 리다이렉트
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const newToken = await refreshToken();
      if (newToken) {
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(error.config);
      }
      authStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

| 설정 | 값 | 적용 대상 |
|------|-----|---------|
| staleTime | 30초 | 대시보드 데이터 |
| staleTime | 5분 | 플랫폼/AI 데이터 |
| staleTime | 10분 | 사용자/설정 데이터 |
| refetchOnWindowFocus | true | 대시보드, 커뮤니티 |
| refetchOnWindowFocus | false | 그 외 |
| Optimistic Updates | ✅ | 콘텐츠 상태 변경, 댓글 응답 |
| Infinite Query | ✅ | 댓글 목록, 콘텐츠 라이브러리 |
| Error Retry | 3회 (exponential backoff) | 네트워크 오류 전체 |

---

## 4. 주요 컴포넌트 설계 (9종)

| 컴포넌트 | 책임 | 핵심 라이브러리 |
|---------|------|---------------|
| **ContentCalendar** | 월/주간 캘린더 뷰 + D&D 일정 변경 | @dnd-kit/core, date-fns |
| **KanbanBoard** | 콘텐츠 워크플로우 칸반 (4컬럼) | @dnd-kit/sortable |
| **UnifiedInbox** | 다채널 댓글 통합 인박스 | WebSocket 실시간 |
| **AnalyticsDashboard** | KPI 카드 + 트렌드 차트 + AI 요약 | Recharts |
| **ContentEditor** | 콘텐츠 생성/수정 + 미디어 업로드 | TipTap, react-dropzone |
| **AIChatPanel** | 플로팅 AI 챗봇 패널 (SSE 스트리밍) | SSE/WebSocket |
| **PlatformPreview** | 플랫폼별 게시 미리보기 모킹 | 커스텀 CSS |
| **NotificationCenter** | 알림 드롭다운 + 읽음/필터 | WebSocket, Zustand |
| **ApprovalTimeline** | 승인 이력 타임라인 UI | 커스텀 타임라인 |

### 레이아웃 컴포넌트

```tsx
// MainLayout.tsx — 3단 레이아웃
<div className="flex h-screen">
  <Sidebar collapsed={sidebarCollapsed} />        {/* 240px / 64px */}
  <div className="flex flex-col flex-1 overflow-hidden">
    <Header>
      <ClientSwitcher />                           {/* 중앙: 클라이언트 전환 */}
      <SearchBar />                                {/* Quick Search */}
      <NotificationCenter />                       {/* 종 아이콘 + 드롭다운 */}
      <UserMenu />                                 {/* 프로필 + 로그아웃 */}
    </Header>
    <main className="flex-1 overflow-y-auto p-6">
      <Outlet />                                   {/* 라우터 하위 페이지 */}
    </main>
  </div>
  <AIChatPanel />                                  {/* 플로팅 패널 */}
</div>
```

### 상태 표시 컬러 시스템 (화면 설계서 기준)

```typescript
const STATUS_COLORS = {
  draft:          "#9E9E9E",  // 회색
  review:         "#F39C12",  // 노란
  client_review:  "#E67E22",  // 주황
  approved:       "#27AE60",  // 초록
  published:      "#2E86AB",  // 파란
  rejected:       "#E74C3C",  // 빨간
} as const;

const SENTIMENT_COLORS = {
  positive: "#27AE60",
  neutral:  "#9E9E9E",
  negative: "#E74C3C",
  crisis:   "#8B0000",
} as const;
```

---

## 5. 에러 처리 전략 (5단계)

| 레벨 | 처리 방식 | 구현 |
|------|---------|------|
| **컴포넌트** | React Error Boundary | 각 feature 모듈 최상위 배치, fallback UI 표시 |
| **API** | Axios Interceptor + React Query onError | 4xx → 토스트, 401 → 자동 갱신/리다이렉트 |
| **네트워크** | React Query retry + 오프라인 감지 | 3회 재시도, 오프라인 배너 |
| **폼 검증** | React Hook Form + Zod | 실시간 필드 검증, 서버 에러 필드 매핑 |
| **전역 예외** | Sentry Error Tracking | 미처리 예외 자동 수집, 소스맵 연동 |

```tsx
// ErrorBoundary 예시
<ErrorBoundary fallback={<ErrorFallback onReset={handleReset} />}>
  <ContentPage />
</ErrorBoundary>

// Toast 알림 (shadcn/ui 기반)
const { toast } = useToast();
toast({ title: "저장 완료", description: "콘텐츠가 저장되었습니다.", variant: "success" });
toast({ title: "오류 발생", description: error.message, variant: "destructive" });
```

---

## 6. 반응형 디자인 전략

| 브레이크포인트 | 레이아웃 | 동작 |
|-------------|---------|------|
| **Desktop** (≥1280px) | 사이드바 + 메인 + 우측 패널 | 전체 기능, 3단 레이아웃 |
| **Tablet** (768–1279px) | 사이드바 축소 + 메인 | 아이콘 모드, 우측 패널 오버레이 |
| **Mobile** (<768px) | 바텀 네비 + 메인 | 사이드바 → 하단 탭바, 주요 기능 우선 |

```typescript
// Tailwind mobile-first 예시
<div className="
  grid grid-cols-1           /* Mobile: 1단 */
  md:grid-cols-2             /* Tablet: 2단 */
  xl:grid-cols-3             /* Desktop: 3단 */
  gap-4
">
```

- **사이드바 토글**: `uiStore.sidebarCollapsed` 상태 관리
- **테이블 → 카드**: 768px 이하에서 반응형 카드 자동 전환
- **최소 해상도**: 1280 × 800px (13인치 노트북 기준)
- **최적 해상도**: 1920 × 1080px
- **사이드바**: 펼침 240px / 접힘 64px

---

## 7. 접근성 기준 (WCAG 2.1 AA)

- **shadcn/ui 내장 ARIA**: Radix UI 기반 자동 제공
- **키보드 네비게이션**: 모든 인터랙티브 요소 Tab/Enter/Escape
- **스크린 리더**: `aria-label`, `aria-describedby`, `role` 적용
- **색상 대비**: Tailwind 팔레트 4.5:1 이상 대비비
- **포커스 표시**: `ring-2 ring-offset-2` 가시적 포커스 링
- **이미지 대체 텍스트**: 모든 `<img>`에 `alt` 필수

---

## 8. API 클라이언트 계층 구조

```
src/api/
├── client.ts          # Axios 인스턴스 + interceptors + 기본 설정
├── auth.ts            # login, refresh, logout, me
├── users.ts           # useUsers, useCreateUser, useUpdateRole...
├── clients.ts         # useClients, useClient, useCreateClient, useFaqGuidelines...
├── contents.ts        # useContents, useContent, useCreateContent...
├── publishing.ts      # useSchedulePublish, usePublishNow...
├── community.ts       # useInbox, useReply, useSentiment, useFilterRules...
├── analytics.ts       # useDashboardKPI, useTrends, useReport...
├── ai.ts              # useCopyGenerate, useReplyDraft, useChat...
├── notifications.ts   # useNotifications, useUnreadCount, useMarkRead...
└── settings.ts        # usePlatformConnections, useWorkflows, useNotifPrefs...
```

각 파일은 React Query hook을 export:
```typescript
// contents.ts 예시
export const useContents = (filter: ContentFilter) =>
  useQuery({
    queryKey: ["contents", filter],
    queryFn: () => apiClient.get("/api/v1/contents", { params: filter }),
    staleTime: 30_000,
  });

export const useCreateContent = () =>
  useMutation({
    mutationFn: (data: ContentCreate) => apiClient.post("/api/v1/contents", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contents"] }),
  });
```
