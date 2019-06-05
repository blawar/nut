# Nut
이것은 CDN에서 모든 게임을 자동으로 다운로드하고 파일 시스템에 백업으로 구성하는 프로그램입니다. 합법적으로 구입했거나 타이틀 키가 있는 게임만 플레이 할 수 있습니다. Nut은 또한 당신의 컬렉션을 검색할 수있는 웹 인터페이스를 제공합니다.

nut.default.conf를 nut.conf에 복사하고 nut.conf에 로컬 편집을 모두 수행해야 합니다.

**파일의 이름을 바꾸기 / 파일을 정리, 아무것도 다운로드하지 않으려면 `nut.conf`를 편집하고 모든 다운로드 옵션을 false로 설정하십시오.** NSP 파일의 제목은 대괄호 안에 파일 이름의 일부로 포함되어야 합니다.

`nut.conf`에서`sansTitleKey`를 활성화시킴으로써 (아카이브 용) 키가 없는 모든 타이틀을 다운로드 할 수 있습니다. 이 타이틀은 `.nsx` 파일 확장명으로 저장되며 나중에 타이틀 키가 발견되면 잠금 해제 될 수 있습니다.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/ss.jpg)

---------

## 사용볍
 - 다운로드 [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - CDN에서 다운로드하려면 이미 구성된 CDNSP 디렉토리에 모든 것을 넣으십시오. 구체적으로 다음이 필요합니다:
	- `Certificate.cert`
	- `nx_tls_client_cert.pem`
	- `keys.txt`
 - 파이썬 3.6 이상 설치
 - `pip`를 통해 다음 모듈을 설치하십시오:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode image bs4 urllib3 flask pyqt5`
 - `nut.conf` 구성 (아래 참조)
 - `python3 nut.py --help`를 실행하여 옵션을 이해합니다.
 
## Tinfoil USB 설치
server.py를 실행하거나 윈도우 사용자는 릴리즈 섹션에서 미리 컴파일 된 nut.exe를 사용할 수 있습니다.

릴리스 페이지의 지침에 따라 USB 드라이버를 설치하십시오.

서버를 실행한 후 목록에 NSP가 표시되는지 확인하십시오. 일치하지 않으면 경로를 변경하고 "검색" 버튼을 클릭하십시오.

스위치에서 PC로 USB 케이블을 연결하십시오.

Tinfoil을 시작하면 Nuts 서버에 나열된 모든 NSP가 Tinfoil에 설치할 수 있습니다.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)

## Tinfoil NUT 서버 설치
server.py를 실행하거나 윈도우 사용자는 릴리즈 섹션에서 미리 컴파일 된 nut.exe를 사용할 수 있습니다.

서버를 실행한 후 목록에 NSP가 표시되는지 확인하십시오. 일치하지 않으면 경로를 변경하고 "검색" 버튼을 클릭하십시오.

Tinfoil을 시작한 다음 위치로 이동한 다음 "새 위치 추가"를 선택하십시오. nut 서버 응용 프로그램에 표시된 ip, 포트, 사용자 이름, 암호를 입력한 다음 저장을 누릅니다.

nut 서버에 나열된 모든 NSP를 이제 Tinfoil에 설치할 수 있습니다.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)
 
## 서버 GUI
서버 GUI를 실행하려면 먼저 닌텐도에서 이미지를 다운로드 해야합니다. 다음 명령을 사용하여 그렇게 할 수 있습니다:
nut.py -s --scrape

이것은 약간의 시간이 걸릴 것입니다. 완료되면 다음을 사용하여 웹 서버를 시작할 수 있습니다:
server.py

그런 다음 웹 브라우저에서 localhost:9000을 가리킵니다.

---------

## 구성
모든 설정은`nut.conf`를 통해 이루어집니다.

### 경로
`nut`가 파일을 저장 (정리)하는 방법을 설정합니다. 기본적으로:
```
베이스 게임:		titles/{name}[{id}][v{version}].nsp
DLC:			titles/DLC/{name}[{id}][v{version}].nsp
업데이트:		titles/updates/{name}[{id}][v{version}].nsp
데모: 			titles/demos/{name}[{id}][v{version}].nsp
데모 업데이트:		titles/demos/updates/{name}[{id}][v{version}].nsp

nspOut			_NSPOUT
검색 (폴더)		.
```

### 타이틀 목록
`nut`는`titleUrls`과`titledb\*.txt`에 정의 된 URL에 대한 titlekey 목록을 다운로드하고 구문 분석하고 결합합니다. 우선적으로 로드됩니다. 첫 번째 지역 목록 (알파벳순), 원격 목록. 이것은 커스텀 타이틀 네이밍 (예: `titledb\z.titlekeys.txt`)을 유지하고자 할 때 유용합니다.

허용되는 형식:
```
Rights ID|Title Key|Title Name
01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|1-2-Switch

또는

id|rightsId|key|isUpdate|isDLC|isDemo|name|version|region|retailOnly
01000320000cc000|01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|0|0|0|1-2-Switch™|0|US|0

또는

id|name
01000320000cc000|1-2-Switch™

등.
```

### 화이트리스트
`whitelist.txt`에 다운로드하고자 하는 타이틀 id를 개행 문자로 구분하여 넣으십시오.

*모든 게임을 다운로드하려면 파일을 비워 두십시오.*

### 블랙리스트
`blacklist.txt`에 다운로드 **하고 싶지 않은** 타이틀 아이디를 개행 문자로 구분하여 넣으십시오.

# 도움말
```
nut.py -h
사용법: nut.py [-h] [--base {0,1}] [--demo {0,1}] [--update {0,1}]
              [--dlc {0,1}] [--nsx {0,1}] [-D] [-d DOWNLOAD [DOWNLOAD ...]]
              [-i INFO] [-u UNLOCK] [--unlock-all]
              [--set-masterkey1 SET_MASTERKEY1]
              [--set-masterkey2 SET_MASTERKEY2]
              [--set-masterkey3 SET_MASTERKEY3]
              [--set-masterkey4 SET_MASTERKEY4]
              [--set-masterkey5 SET_MASTERKEY5]
              [--remove-title-rights REMOVE_TITLE_RIGHTS] [-s] [-Z] [-z] [-V]
              [-o] [-U] [-r] [-x EXTRACT [EXTRACT ...]] [-c CREATE]
              [--export-missing EXPORT_MISSING] [-M MISSING]
              [--nca-deltas NCA_DELTAS] [--silent] [--json] [-S] [-m] [-p]
              [--scrape] [--scrape-delta] [--scrape-title SCRAPE_TITLE]
              [file [file ...]]

고정 인수:
  file

옵션 인수:
  -h, --help            이 도움말 메시지를 표시하고 종료
  --base {0,1}          기본 타이틀 다운로드
  --demo {0,1}          데모 타이틀 다운로드
  --update {0,1}        다운로드 타이틀 업데이트
  --dlc {0,1}           DLC 타이틀 다운로드
  --nsx {0,1}           타이틀 키 없이 타이틀 다운로드
  -D, --download-all    모든 타이틀 다운로드
  -d DOWNLOAD [DOWNLOAD ...], --download DOWNLOAD [DOWNLOAD ...]
                        타이틀 다운로드
  -i INFO, --info INFO  제목 또는 파일 정보 표시
  -u UNLOCK, --unlock UNLOCK
                        NSX / NSP에 사용 가능한 타이틀 키 설치
  --unlock-all          모든 NSX 파일에 사용 가능한 타이틀 키 설치
  --set-masterkey1 SET_MASTERKEY1
                        NSP의 마스터 키 암호화를 변경.
  --set-masterkey2 SET_MASTERKEY2
                        NSP의 마스터 키 암호화를 변경.
  --set-masterkey3 SET_MASTERKEY3
                        NSP의 마스터 키 암호화를 변경.
  --set-masterkey4 SET_MASTERKEY4
                        NSP의 마스터 키 암호화를 변경.
  --set-masterkey5 SET_MASTERKEY5
                        NSP의 마스터 키 암호화를 변경.
  --remove-title-rights REMOVE_TITLE_RIGHTS
                        RNSP의 모든 NCA에서 타이틀 권한 암호화를 제거
  -s, --scan            새 NSP 파일을 검색
  -Z                    닌텐도에서 모든 타이틀 버전 업데이트
  -z                    닌텐도에서 최신 타이틀 버전 업데이트
  -V                    닌텐도에서 최신 타이틀 업데이트 검색
  -o, --organize        NSP 파일의 이름 바꾸기 및 이동
  -U, --update-titles   url에서 타이틀 DB를 업데이트
  -r, --refresh         NSP 파일에서 모든 메타를 읽고 CDN에 최신 버전 정보 쿼리
  -x EXTRACT [EXTRACT ...], --extract EXTRACT [EXTRACT ...]
                        NSP 생성 / 압축
  -c CREATE, --create CREATE
                        
  --export-missing EXPORT_MISSING
                        csv 형식으로 타이틀 데이터베이스 내보내기
  -M MISSING, --missing MISSING
                        csv 형식으로 다운로드하지 않은 타이틀의 타이틀
                        데이터베이스 내보내기
  --nca-deltas NCA_DELTAS
                        델타 업데이트가 포함된 NSP 내보내기 목록
  --silent              stdout/stderr 출력을 억제
  --json                JSON 출력
  -m, --hostname        서버 호스트 이름 설정
  -p, --port            서버 포트 설정
  --scrape              닌텐도 서버에서 모든 타이틀 스크랩
  --scrape-delta        아직 스크랩 안된 닌텐도 서버의 모든 타이틀을
                        스크랩
  --scrape-title SCRAPE_TITLE
                        닌텐도 서버에서 스크랩 한 타이틀
```

# 크레딧
- 오리지널 CDNSP
- SciresM (https://github.com/SciresM/) 의한 Hactool
- Simon (https://github.com/simontime/) 은 끝없는 CDN 지식과 도움을 제공.
- SplatGamer
