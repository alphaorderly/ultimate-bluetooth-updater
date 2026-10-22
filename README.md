# Ultimate Bluetooth Updater

[![Build updater](https://github.com/alphaorderly/ultimate-bluetooth-updater/actions/workflows/build.yml/badge.svg)](https://github.com/alphaorderly/ultimate-bluetooth-updater/actions/workflows/build.yml)

**8BitDo Ultimate Bluetooth 전용 비공식 업데이트 앱.**
백버튼 리매핑과 Switch 2 신호 학습·흔들어 깨우기를 설치합니다.
macOS Apple Silicon / Intel 및 Windows x64 앱을 GitHub Actions로 빌드합니다.

**사용법 바로가기:** [백버튼 할당](#백버튼-할당) · [Switch 2 깨우기](#switch-2-깨우기-학습)

> **macOS·Windows 실기기 설치 확인 완료:** 2026-10-23 사용자가 두 운영체제에서 GUI 업데이트 앱의 설치 검증을 완료했다고 보고했습니다.
> 수정 펌웨어의 실제 Switch 2 깨우기 성공도 사용자 확인을 마쳤습니다.
> GitHub Actions의 앱 빌드·시뮬레이터·화면 실행 검사와 별도로 확인한 실기기 결과입니다. 현재 배포는 베타입니다.

## 다운로드 및 실행

[Releases](https://github.com/alphaorderly/ultimate-bluetooth-updater/releases)에서 운영체제에 맞는 ZIP을 받습니다.

- **macOS 12 이상:** `macOS-arm64`(Apple Silicon), `macOS-x64`(Intel). ZIP 안의 `.app`을 실행합니다.
- **Windows 10/11 x64:** `Windows-x64`. ZIP 전체를 풀고 폴더 안의 `UltimateBluetoothUpdater.exe`를 실행합니다. 실행 파일만 옮기지 마세요.
- 초기 베타에는 Apple notarization / Windows Authenticode 서명이 없습니다. 운영체제가 실행을 차단할 수 있습니다.
  내려받은 파일의 SHA-256을 릴리스의 `.sha256` 파일과 비교하고 출처를 확인하세요.
  macOS에서는 Apple이 안내하는 [신뢰하는 앱 열기](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac) 절차를 사용할 수 있습니다.

다운로드한 앱에는 Python 설치가 필요하지 않습니다. 첫 설치는 공식 펌웨어를 받기 위해 인터넷 연결이 필요합니다.

## 지원 대상

| 항목 | 범위 |
|---|---|
| 모델 | Ultimate **Bluetooth** Controller, 분석한 `2AOWF-ULTIMATEN` 계열 |
| 부트모드 USB | `2dc8:3208`; 펌웨어 PID `0x6007` 추가 확인 |
| 인식하는 기존 이미지 | 고정 해시의 공식 1.09 / 1.10 / 1.11 및 이 프로젝트의 기존 시험 이미지 |
| 설치 결과 | 1.11 기반 + 백버튼 리매핑 + Switch 2 학습 깨우기 |
| 실기기 확인 | GUI 앱으로 macOS·Windows 설치 검증 완료 및 Switch 2 깨우기 성공 — 사용자 보고 |
| 제외 | Ultimate 2, 2C, C, 2.4G 전용 모델, 알 수 없는 하드웨어/이미지 |

기존 앱의 일부를 버전별로 고치는 대신 검증된 전체 앱으로 교체합니다. 그러나 **모든 펌웨어 버전·하드웨어 리비전의 호환성을 보장하지 않습니다.** 알 수 없는 기존 이미지는 백업 후 설치를 중단합니다. 기존 1.09/1.10 이미지 인식은 구현됐지만 해당 버전에서의 실제 설치 전환은 별도 미검증입니다.

## 설치

1. 다른 펌웨어 업데이트 프로그램을 닫고 컨트롤러 한 대만 연결합니다.
2. 컨트롤러 전원을 끄고 **L + R을 누른 채 USB**로 연결합니다. 빨간 LED가 깜박이는 부트모드여야 합니다.
3. 앱에서 모델 확인 항목을 선택하고 **펌웨어 업데이트**를 누릅니다.
4. 공식 파일 다운로드·해시 확인 → 기존 앱 및 peer 섹터 백업 → 설치 → 전체 재읽기·버전·peer 보존 확인 → 리셋 순서로 진행합니다.
5. 완료가 표시되면 USB를 분리합니다.

쓰기 시작 후에는 취소와 앱 닫기를 막습니다. 통신 실패 시 자동 재시도·리셋을 하지 않습니다. USB 연결을 유지하고 기존 백업으로 복구하세요.

공식 다운로드가 안 되면 **공식 파일 가져오기**에서 고정된 Ultimate 1.11/build2752 및 Ultimate 2 v2.00/build2870 `.dat`를 선택할 수 있습니다. 이름이 같아도 해시가 다르면 거절합니다. 원본·무선부 펌웨어는 이 저장소에 포함하지 않습니다.

## 백버튼 할당

컨트롤러에서 버튼 조합으로 백버튼에 원하는 입력을 할당할 수 있습니다.

> **백버튼 하나 + 원하는 버튼을 누른 채 → 프로필 변경 버튼을 눌러 확정**

1. 설정할 **백버튼 하나**를 누르고 유지합니다.
2. 할당할 **대상 버튼**도 함께 누릅니다. 여러 버튼을 동시에 할당할 수도 있습니다.
3. 두 입력을 유지한 채 **프로필 변경 버튼**을 누릅니다. 저장 시 **짧은 진동 1회**로 알립니다.

| 하고 싶은 작업 | 버튼 조작 | 저장 알림 |
|---|---|---|
| 새 버튼 또는 버튼 조합 할당 | 백버튼 하나 + 대상 버튼을 누른 채 **프로필 변경 버튼** | 짧은 진동 **1회** |
| 기존 할당 해제 | 백버튼 하나만 누른 채 **프로필 변경 버튼** | 짧은 진동 **2회** |

**확정할 때는 프로필 변경 버튼을 사용하세요. 별(★) 버튼이 아닙니다.** 두 백버튼을 동시에 누르면 할당되지 않습니다.
스틱 방향·프로필 변경 버튼·Mode·페어링 버튼은 할당 대상에서 제외됩니다.

## Switch 2 깨우기 학습

1. Ultimate를 Switch 2에 먼저 페어링합니다.
2. 본체를 절전시키고 Ultimate를 켜 연결 대기시킵니다.
3. 같은 본체의 **오른쪽 Joy-Con 2 HOME**으로 본체를 깨웁니다.
4. Ultimate에서 학습 진동이 오면 본체를 다시 절전시킵니다.
5. Ultimate를 켜서 연결 대기 중 흔들어 깨웁니다.

첫 유효 오른쪽 조이콘 신호를 학습하므로 주변 다른 조이콘의 조작을 피하세요. 짧은 송신 진동은 명령 ACK를 뜻하며 콘솔 깨우기 성공을 보장하는 표시는 아닙니다. 전원 재시작 후 학습 유지·반복 성공률·여러 컨트롤러 공존은 추가 검증이 필요합니다. 이 베타에는 수동 학습 초기화 UI가 없습니다.

## 백업과 복구

앱의 **백업 폴더** 버튼으로 로컬 백업을 엽니다. `backup.json`, `app.bin`, `peer.bin`, `version.bin`이 한 세트입니다.

- **이전 펌웨어로 복구**에서 원래 설치 전에 만들어진 `backup.json`을 선택합니다.
- 파일 해시와 이미지 인식을 다시 검사하고 현재 내용을 새로 백업한 뒤 복구합니다.
- 복구는 앱/버전 영역을 되돌립니다. 페어링 섹터는 덮어쓰지 않습니다.
- peer 백업에는 페어링 정보가 있으므로 GitHub 이슈나 공개 저장소에 올리지 마세요.
- 전원 차단으로 부트모드 자체가 동작하지 않는 상황의 복구는 검증되지 않았습니다.

앱은 계정·분석 서비스·원격 로그 전송 기능이 없습니다. 공식 입력 다운로드에만 네트워크를 사용합니다.

## 개발 및 빌드

Python 3.12 권장. 프로젝트 전용 가상환경에서:

```sh
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python main.py --self-test
python main.py
python tools/build.py
```

`tools/build.py`는 실행 중인 운영체제용 앱과 ZIP·SHA-256을 만듭니다. Windows 빌드는 Windows에서, macOS 빌드는 macOS에서 실행합니다.
`python tools/verify_firmware.py`는 공식 원본을 다운로드해 실기기 검증 이미지와 정확히 같은 결과가 생성되는지 검사합니다.

Actions는 main push / PR / 수동 실행마다 테스트와 세 플랫폼 빌드를 수행합니다. `v*` 태그를 push하면 모든 플랫폼 빌드가 성공한 뒤 사전 릴리스를 게시합니다. 개인 코드서명 인증서는 포함하지 않습니다.

## 펌웨어 출처와 검증 경계

`firmware-src/`는 우리가 작성한 C/어셈블리 수정 코드입니다. 앱에 포함된 `resources/patch.json`은 이 코드의 고정된 기계어와 짧은 수정 지점이며, 제조사 무선부는 공식 파일에서 사용자 컴퓨터에서만 추출합니다.

최종 앱 이미지 SHA-256:
`f8edd30b192b9faa5d29039328b0882b79d0094f7d1c2597d8c018117e6bf552`

펌웨어 단계에서 22개 오프라인 검사 묶음(학습 Thumb 호출222회, 백버튼 호출1,096회)과 한 대의 사용자 깨우기 시험을 통과했습니다. 업데이터 검사에는 백업 실패·미지원 이미지·CRC 오류·쓰기 실패·재읽기 불일치·복구 경로가 포함됩니다. 시뮬레이션은 실제 USB 하드웨어 검증을 대신하지 않습니다.

[MIT 라이선스](LICENSE) · [제3자 소프트웨어 고지](THIRD_PARTY.md)

8BitDo / Nintendo와 무관한 커뮤니티 프로젝트입니다.
