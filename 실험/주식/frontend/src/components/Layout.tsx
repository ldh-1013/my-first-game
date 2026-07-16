import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BookOpenText,
  CandlestickChart,
  Gauge,
  LayoutDashboard,
  Newspaper,
  Settings,
  Trophy,
  WalletCards,
} from "lucide-react";
import StockChatWidget from "./StockChatWidget";

export type PageKey =
  | "dashboard"
  | "holdings"
  | "portfolio"
  | "detail"
  | "reports"
  | "top5"
  | "news"
  | "analytics"
  | "settings";

const NAV_ITEMS: Array<{ key: PageKey; label: string; icon: LucideIcon }> = [
  { key: "dashboard", label: "대시보드", icon: LayoutDashboard },
  { key: "holdings", label: "보유·관심 종목", icon: CandlestickChart },
  { key: "portfolio", label: "포트폴리오", icon: WalletCards },
  { key: "detail", label: "종목 분석", icon: BarChart3 },
  { key: "reports", label: "일일 리포트", icon: BookOpenText },
  { key: "top5", label: "TOP 5", icon: Trophy },
  { key: "news", label: "뉴스 모니터", icon: Newspaper },
  { key: "analytics", label: "예측 검증", icon: Gauge },
  { key: "settings", label: "자동화·설정", icon: Settings },
];

interface LayoutProps {
  page: PageKey;
  onNavigate: (page: PageKey) => void;
  children: React.ReactNode;
  contextTicker?: string;
  onOpenStock?: (ticker: string) => void;
}

export default function Layout({
  page,
  onNavigate,
  children,
  contextTicker,
  onOpenStock,
}: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SI</div>
          <div>
            <strong>Stock Insight</strong>
            <span>Local research desk</span>
          </div>
        </div>
        <nav>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={page === item.key ? "active" : ""}
                key={item.key}
                onClick={() => onNavigate(item.key)}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-note">
          <span>FREE DATA MODE</span>
          <p>가격·뉴스·재무·공시를 한곳에서 검토하는 로컬 분석 도구</p>
        </div>
      </aside>
      <main>
        <div className="mobile-brand">
          <strong>Stock Insight</strong>
          <select value={page} onChange={(event) => onNavigate(event.target.value as PageKey)}>
            {NAV_ITEMS.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        {children}
        <footer className="global-disclaimer">
          본 프로그램은 투자 수익을 보장하지 않으며 매수·매도 판단을 대신하지 않습니다. 무료
          데이터는 지연되거나 누락될 수 있으므로 공시와 원문을 함께 확인하세요.
        </footer>
      </main>
      <StockChatWidget
        contextTicker={contextTicker}
        onOpenStock={onOpenStock}
      />
    </div>
  );
}
