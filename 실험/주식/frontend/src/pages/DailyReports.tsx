import { Download, Printer } from "lucide-react";
import { useEffect, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import ReportCard from "../components/ReportCard";
import type { DailyReport } from "../types/report";

export default function DailyReports({ onOpenStock }: { onOpenStock: (ticker: string) => void }) {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    stockApi
      .reports()
      .then(setReports)
      .catch((err) => setError(getApiError(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page printable-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">DAILY ARCHIVE</p>
          <h1>일일 리포트</h1>
          <p>종목별 핵심 신호와 한국어 뉴스 요약을 한눈에 확인하세요.</p>
        </div>
        <div className="inline-actions no-print">
          <a className="ghost-button" href={stockApi.reportsCsvUrl}>
            <Download size={16} /> CSV
          </a>
          <button className="ghost-button" type="button" onClick={() => window.print()}>
            <Printer size={16} /> PDF 인쇄
          </button>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div className="report-list report-list-v2">
        {reports.map((report) => (
          <button
            className="report-button"
            key={report.id}
            type="button"
            onClick={() => onOpenStock(report.ticker)}
          >
            <ReportCard report={report} />
          </button>
        ))}
        {loading && <div className="empty-state large">리포트를 불러오는 중입니다.</div>}
        {!loading && !reports.length && (
          <div className="empty-state large">오늘 생성된 리포트가 없습니다.</div>
        )}
      </div>
    </div>
  );
}
