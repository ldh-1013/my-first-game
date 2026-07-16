import { useState } from "react";

import Layout, { type PageKey } from "./components/Layout";
import Analytics from "./pages/Analytics";
import DailyReports from "./pages/DailyReports";
import Dashboard from "./pages/Dashboard";
import Holdings from "./pages/Holdings";
import NewsMonitor from "./pages/NewsMonitor";
import Portfolio from "./pages/Portfolio";
import Settings from "./pages/Settings";
import StockDetail from "./pages/StockDetail";
import TopFive from "./pages/TopFive";

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [selectedTicker, setSelectedTicker] = useState("");
  const openStock = (ticker: string) => {
    setSelectedTicker(ticker);
    setPage("detail");
  };
  const renderPage = () => {
    switch (page) {
      case "dashboard":
        return <Dashboard onOpenStock={openStock} />;
      case "holdings":
        return <Holdings />;
      case "portfolio":
        return <Portfolio onOpenStock={openStock} />;
      case "detail":
        return <StockDetail initialTicker={selectedTicker} />;
      case "reports":
        return <DailyReports onOpenStock={openStock} />;
      case "top5":
        return <TopFive onOpenStock={openStock} />;
      case "news":
        return <NewsMonitor />;
      case "analytics":
        return <Analytics />;
      case "settings":
        return <Settings />;
    }
  };
  return (
    <Layout
      page={page}
      onNavigate={setPage}
      contextTicker={page === "detail" ? selectedTicker : ""}
      onOpenStock={openStock}
    >
      {renderPage()}
    </Layout>
  );
}
