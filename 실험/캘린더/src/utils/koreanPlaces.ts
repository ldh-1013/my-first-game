/**
 * 한글 지명 → 영문 지명 표.
 *
 * Open-Meteo Geocoding은 language=ko를 주면 결과를 한국어로 돌려주지만,
 * 검색어 자체는 한글로 잘 못 찾는다. 실제로 확인해 보면
 *   '서울' → 결과 없음
 *   '부산' → 경상북도의 작은 마을 'Pusan'이 잡힘 (부산광역시가 아님)
 *   '대전' → 전라남도의 마을 '대전'이 잡힘 (대전광역시가 아님)
 * 처럼 실패하거나 엉뚱한 곳을 준다. 반면 'Seoul', 'Busan'으로 찾으면 정확히 나온다.
 *
 * 그래서 한글이 섞인 검색어는 이 표로 영문명을 먼저 찾아 조회한다.
 * 표에 없는 지명은 입력한 그대로 한 번 더 시도한다.
 */
export const KOREAN_TO_ENGLISH: Record<string, string> = {
  // 특별시·광역시·특별자치시
  서울: 'Seoul',
  부산: 'Busan',
  인천: 'Incheon',
  대구: 'Daegu',
  대전: 'Daejeon',
  광주: 'Gwangju',
  울산: 'Ulsan',
  세종: 'Sejong',
  // 경기
  수원: 'Suwon',
  용인: 'Yongin',
  고양: 'Goyang',
  성남: 'Seongnam',
  화성: 'Hwaseong',
  부천: 'Bucheon',
  남양주: 'Namyangju',
  안산: 'Ansan',
  평택: 'Pyeongtaek',
  안양: 'Anyang',
  시흥: 'Siheung',
  파주: 'Paju',
  김포: 'Gimpo',
  의정부: 'Uijeongbu',
  광명: 'Gwangmyeong',
  하남: 'Hanam',
  군포: 'Gunpo',
  양주: 'Yangju',
  이천: 'Icheon',
  오산: 'Osan',
  구리: 'Guri',
  안성: 'Anseong',
  포천: 'Pocheon',
  의왕: 'Uiwang',
  여주: 'Yeoju',
  동두천: 'Dongducheon',
  과천: 'Gwacheon',
  // 강원
  춘천: 'Chuncheon',
  원주: 'Wonju',
  강릉: 'Gangneung',
  동해: 'Donghae',
  속초: 'Sokcho',
  삼척: 'Samcheok',
  태백: 'Taebaek',
  // 충북·충남
  청주: 'Cheongju',
  충주: 'Chungju',
  제천: 'Jecheon',
  천안: 'Cheonan',
  아산: 'Asan',
  서산: 'Seosan',
  당진: 'Dangjin',
  공주: 'Gongju',
  논산: 'Nonsan',
  보령: 'Boryeong',
  계룡: 'Gyeryong',
  // 전북·전남
  전주: 'Jeonju',
  익산: 'Iksan',
  군산: 'Gunsan',
  정읍: 'Jeongeup',
  남원: 'Namwon',
  김제: 'Gimje',
  목포: 'Mokpo',
  여수: 'Yeosu',
  순천: 'Suncheon',
  나주: 'Naju',
  광양: 'Gwangyang',
  // 경북·경남
  포항: 'Pohang',
  경주: 'Gyeongju',
  구미: 'Gumi',
  안동: 'Andong',
  김천: 'Gimcheon',
  경산: 'Gyeongsan',
  영주: 'Yeongju',
  영천: 'Yeongcheon',
  상주: 'Sangju',
  문경: 'Mungyeong',
  창원: 'Changwon',
  진주: 'Jinju',
  김해: 'Gimhae',
  양산: 'Yangsan',
  거제: 'Geoje',
  통영: 'Tongyeong',
  사천: 'Sacheon',
  밀양: 'Miryang',
  // 제주
  제주: 'Jeju',
  서귀포: 'Seogwipo',
};

/** 영문 → 한글 (IP로 감지한 영문 도시명을 한글로 되돌릴 때 쓴다) */
const ENGLISH_TO_KOREAN: Record<string, string> = Object.fromEntries(
  Object.entries(KOREAN_TO_ENGLISH).map(([ko, en]) => [en.toLowerCase(), ko]),
);

const SUFFIX = /(특별자치시|특별자치도|광역시|특별시|시|도|군|구)$/;

/** 한글 지명이면 영문명을, 아니면 null. '수원시'처럼 접미사가 붙어도 찾는다. */
export function toEnglishPlace(query: string): string | null {
  const trimmed = query.trim();
  if (!/[가-힣]/.test(trimmed)) return null;
  return KOREAN_TO_ENGLISH[trimmed] ?? KOREAN_TO_ENGLISH[trimmed.replace(SUFFIX, '')] ?? null;
}

/** 영문 도시명에 대응하는 한글 지명. 표에 없으면 null. */
export function toKoreanPlace(name: string): string | null {
  return ENGLISH_TO_KOREAN[name.trim().toLowerCase()] ?? null;
}
