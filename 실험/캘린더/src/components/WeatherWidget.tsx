import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Factory,
  MapPin,
  Moon,
  RefreshCw,
  Search,
  Sun,
  Wind,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useWeather } from '../hooks/useWeather';
import {
  AQI_LABELS,
  WIND_GRADE_LABELS,
  describeRainChance,
  describeWeather,
  formatTemp,
  formatWindSpeed,
  pm10Grade,
  pm25Grade,
  roundWindSpeed,
  windGrade,
  worseGrade,
  type AqiGrade,
  type WeatherIconKey,
  type WeatherLocation,
} from '../utils/weather';
import { searchLocations } from '../utils/weatherApi';
import styles from './WeatherWidget.module.css';

const DAY_ICONS: Record<WeatherIconKey, LucideIcon> = {
  clear: Sun,
  partly: CloudSun,
  cloud: Cloud,
  fog: CloudFog,
  drizzle: CloudDrizzle,
  rain: CloudRain,
  snow: CloudSnow,
  thunder: CloudLightning,
};

/** 등급별 배지 클래스 — tokens.css의 --color-aqi-* 와 짝을 이룬다 */
const GRADE_CLASS: Record<AqiGrade, string> = {
  good: styles.gradeGood,
  moderate: styles.gradeModerate,
  bad: styles.gradeBad,
  verybad: styles.gradeVerybad,
};

function GradeBadge({ grade }: { grade: AqiGrade | null }) {
  if (!grade) return <span className={styles.badgeEmpty}>–</span>;
  return <span className={`${styles.badge} ${GRADE_CLASS[grade]}`}>{AQI_LABELS[grade]}</span>;
}

function DustRow({
  label,
  value,
  grade,
}: {
  label: string;
  value: number | null;
  grade: AqiGrade | null;
}) {
  return (
    <div className={styles.dustRow}>
      <span className={styles.dustLabel}>{label}</span>
      <span className={styles.dustValue}>
        {value === null ? '–' : Math.round(value)}
        <em className={styles.dustUnit}>㎍/㎥</em>
      </span>
      <GradeBadge grade={grade} />
    </div>
  );
}

/** 값이 오기 전 자리를 잡아 두는 스켈레톤 — 카드 높이가 갑자기 늘어나지 않게 한다 */
function Skeleton() {
  return (
    <div className={styles.skeleton} aria-hidden>
      <div className={styles.skelMain}>
        <div className={styles.skelCircle} />
        <div className={styles.skelLines}>
          <div className={`${styles.skelBar} ${styles.skelBarWide}`} />
          <div className={styles.skelBar} />
        </div>
      </div>
      <div className={styles.skelBar} />
      <div className={styles.skelBar} />
    </div>
  );
}

interface LocationSearchProps {
  onPick: (location: WeatherLocation) => void;
  onClose: () => void;
}

function LocationSearch({ onPick, onClose }: LocationSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<WeatherLocation[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // 타이핑마다 찌르지 않고 잠시 멈췄을 때만 조회한다 (공개 API 예의 + 깜빡임 방지)
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const timer = window.setTimeout(() => {
      searchLocations(trimmed)
        .then((found) => {
          if (cancelled) return;
          setResults(found);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        })
        .finally(() => {
          if (cancelled) return;
          setSearching(false);
          setSearched(true);
        });
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  return (
    <div className={styles.search}>
      <div className={styles.searchInputWrap}>
        <Search size={14} className={styles.searchIcon} aria-hidden />
        <input
          ref={inputRef}
          className={styles.searchInput}
          value={query}
          placeholder="지역 검색 (서울, Tokyo …)"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation();
              onClose();
            }
          }}
          aria-label="지역 검색"
        />
      </div>
      {searching && <p className={styles.searchHint}>찾는 중…</p>}
      {!searching && searched && results.length === 0 && (
        <p className={styles.searchHint}>검색 결과가 없어요</p>
      )}
      {results.length > 0 && (
        <div className={styles.searchResults}>
          {results.map((item) => (
            <button
              type="button"
              key={`${item.lat},${item.lon}`}
              className={styles.searchResult}
              onClick={() => onPick(item)}
            >
              {item.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function WeatherWidget() {
  const { snapshot, location, loading, failed, refresh, changeLocation } = useWeather();
  const [searchOpen, setSearchOpen] = useState(false);

  const look = snapshot ? describeWeather(snapshot.weatherCode) : null;
  // 밤에는 맑음을 해가 아니라 달로 보여준다 — 데스크톱에서 밤에 켜 두는 시간이 길다
  const Icon = look ? (!snapshot?.isDay && look.icon === 'clear' ? Moon : DAY_ICONS[look.icon]) : Cloud;

  const pm10 = snapshot?.pm10 ?? null;
  const pm25 = snapshot?.pm25 ?? null;
  const overall = worseGrade(pm10Grade(pm10), pm25Grade(pm25));

  // 바람과 비 소식은 좋고 나쁨을 매기는 값이 아니라 상태 서술이라, 등급 배지 없이 한 줄씩 적는다.
  // 등급도 표시용으로 줄인 값에서 뽑아, 화면의 숫자와 라벨이 어긋나지 않게 한다.
  const windSpeed = snapshot?.windSpeed != null ? roundWindSpeed(snapshot.windSpeed) : null;
  const wind = windGrade(windSpeed);
  const rainNote = describeRainChance(snapshot?.rainChancePercent ?? null);

  // 갱신에 실패했는데 보여줄 캐시가 있으면, 옛날 값이라는 걸 흐릿하게 티 낸다
  const showStale = failed && snapshot !== null;

  return (
    <section className={styles.widget} aria-label="오늘 날씨와 미세먼지">
      <h2 className={styles.widgetTitle}>
        {/* 다른 사이드바 위젯처럼 카드 성격을 알리는 고정 아이콘 — 위치 변경은 옆의 핀 버튼이 맡는다 */}
        <CloudSun size={16} aria-hidden />
        <span className={styles.locationName}>
          {location?.name ?? snapshot?.location.name ?? '위치 확인 중'}
        </span>
        <button
          type="button"
          className={`${styles.iconButton} ${searchOpen ? styles.iconButtonActive : ''}`}
          onClick={() => setSearchOpen((open) => !open)}
          aria-label="위치 변경"
          aria-expanded={searchOpen}
        >
          <MapPin size={14} />
        </button>
        <button
          type="button"
          className={styles.iconButton}
          onClick={refresh}
          disabled={loading}
          aria-label="날씨 새로고침"
        >
          <RefreshCw size={14} className={loading ? styles.spinning : undefined} />
        </button>
      </h2>

      {searchOpen && (
        <LocationSearch
          onPick={(picked) => {
            changeLocation(picked);
            setSearchOpen(false);
          }}
          onClose={() => setSearchOpen(false)}
        />
      )}

      {!snapshot && loading && <Skeleton />}

      {!snapshot && !loading && (
        <div className={styles.errorBox}>
          <p className={styles.errorText}>날씨 정보를 불러올 수 없어요</p>
          <button type="button" className={styles.retryButton} onClick={refresh}>
            다시 시도
          </button>
        </div>
      )}

      {snapshot && (
        <div className={`${styles.body} ${showStale ? styles.bodyStale : ''}`}>
          <div className={styles.current}>
            <Icon size={44} className={styles.weatherIcon} aria-hidden />
            <div className={styles.readings}>
              <p className={styles.temp}>{formatTemp(snapshot.temperature)}</p>
              <p className={styles.sub}>
                체감 {formatTemp(snapshot.apparentTemperature)} · {look?.label}
              </p>
            </div>
          </div>

          {(wind || rainNote) && (
            <div className={styles.outlook}>
              {wind && windSpeed !== null && (
                <p className={styles.outlookRow}>
                  <Wind size={13} aria-hidden />
                  바람 {WIND_GRADE_LABELS[wind]}
                  <em className={styles.outlookValue}>{formatWindSpeed(windSpeed)}</em>
                </p>
              )}
              {rainNote && (
                <p className={styles.outlookRow}>
                  <CloudRain size={13} aria-hidden />
                  {rainNote}
                </p>
              )}
            </div>
          )}

          <div className={styles.dust}>
            <p className={styles.dustTitle}>
              {/* 바람 세기 줄의 Wind와 겹치지 않게, 발생원을 연상시키는 아이콘으로 */}
              <Factory size={13} aria-hidden /> 미세먼지
              <GradeBadge grade={overall} />
            </p>
            <DustRow label="미세" value={pm10} grade={pm10Grade(pm10)} />
            <DustRow label="초미세" value={pm25} grade={pm25Grade(pm25)} />
          </div>

          {showStale && (
            <p className={styles.staleNote}>
              최신 정보를 못 받아 이전 값을 보여주고 있어요
              <button type="button" className={styles.staleRetry} onClick={refresh}>
                다시 시도
              </button>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
