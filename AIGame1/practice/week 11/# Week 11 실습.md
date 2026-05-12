# Week 11 실습

## 오늘 한 것
- PyInstaller 설치 및 빌드
- resource_path() 함수 추가
- --add-data 옵션으로 에셋 포함
- .exe 실행 확인

## 빌드 명령어
- PyInstaller
- --onefile
- --windowed
- --add-data
## AI 활용 내역
Q. PyInstaller로 Snake.py를 빌드해 dist/Snake.exe를 실행하면 모든 에셋이 작동하지 않는다.
원인은 개발 당시 resource_path()를 적용하지 않았기 때문으로 보이며, 모든 에셋 경로 코드에 resource_path()를 추가한 뒤 다른 내용은 절대 수정하지 않고 전체 코드 전문을 바로 사용할 수 있게 전달해달라는 요청.
A. 수정한 코드 전문 전달 완료

## resource_path() 를 써야 하는 이유
- PyInstaller로 exe를 만들면 에셋 파일들이 임시 폴더에 압축 해제되는데 ./assets 같은 기존 경로는 임시 폴더를 가리키지 못해서 에셋을 못 찾게 된다. resource_path()는 일반 실행이면 현재 폴더, exe 실행이면 임시 폴더를 자동으로 선택해줘서 두 환경 모두에서 경로가 올바르게 동작하도록 해준다.