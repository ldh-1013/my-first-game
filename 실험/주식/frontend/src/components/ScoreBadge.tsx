export default function ScoreBadge({ score, label = "종합 점수" }: { score: number; label?: string }) {
  const tone = score >= 65 ? "good" : score < 45 ? "warn" : "neutral";
  return <div className={`score-badge ${tone}`}><span>{label}</span><strong>{score.toFixed(1)}</strong></div>;
}
