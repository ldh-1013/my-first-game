import { ShieldAlert } from "lucide-react";

export default function RiskAlert({ children }: { children: React.ReactNode }) {
  return (
    <div className="risk-alert">
      <ShieldAlert size={18} />
      <p>{children}</p>
    </div>
  );
}

