# 트러블슈팅 보고서

실습 및 배포 과정에서 발생한 문제에 대해 **증상 → 원인 가설 → 검증 방법 → 조치 내용 → 결과 → 재발 방지** 순서로 기록합니다.

## 외부 접속 장애 점검 체크리스트 (공통 점검 순서)

외부에서 웹 서비스 접속이 실패할 때는 아래 순서대로 좁혀가며 원인을 파악합니다:

1. **라우팅(Route Table & IGW)**: Public Subnet의 Route Table에 `0.0.0.0/0 → Internet Gateway` 경로가 연결되어 있는지 확인
2. **보안 그룹(Security Group)**: 인바운드에 `HTTP(80)`, `HTTPS(443)` (`0.0.0.0/0`) 및 `SSH(22)` (`내 공인 IP/32`)가 허용되어 있는지 확인
3. **퍼블릭 IP / DNS**: EC2에 퍼블릭 IP(또는 Elastic IP `13.124.71.205`)가 할당되어 있고, DuckDNS(`cds-smh.duckdns.org`)가 해당 IP를 정상 반환(`nslookup`)하는지 확인
4. **서버 프로세스 & 컨테이너**: EC2 내부에서 `docker ps`로 `nginx`, `fastapi` 컨테이너가 `Up` 상태인지, `curl -i http://localhost/health`가 `200 OK`를 반환하는지 확인

---

## 사례 1. Docker Compose 실행 후 `curl: (52) Empty reply from server` 발생

| 항목 | 내용 |
| :--- | :--- |
| **증상(문제 상황)** | `docker compose up -d --build` 후 `docker ps`에서는 `nginx`와 `fastapi`가 모두 `Up` 상태였으나, `curl -i http://localhost/` 및 `curl -i http://localhost/health` 요청 시 `curl: (52) Empty reply from server` 오류 발생 |
| **원인 가설** | 1) FastAPI 컨테이너가 `8000` 포트로 뜨지 않았거나,<br>2) Nginx 컨테이너에 마운트된 `nginx/default.conf`가 비어 있거나 잘못된 경로를 참조해 `80` 포트 `server` 블록이 로드되지 않음 |
| **검증 방법** | `nginx/default.conf` 파일 내용 확인 결과 비어 있었고, 프로젝트 내 `*.conf` 파일을 검색하자 오타 폴더인 `ngnix/default.conf`에 설정이 작성되어 있음을 확인 (`docker compose logs` 확인 시에도 `ngnix` 오타로 서비스명 불일치 확인) |
| **조치 내용** | 오타 폴더(`ngnix/default.conf`)의 설정을 정상 경로인 `nginx/default.conf`로 이동하고 `docker compose restart nginx` 실행 |
| **결과** | `curl -i http://localhost/` 및 `curl -i http://localhost/health` 요청 모두 `HTTP/1.1 200 OK`와 `{"status":"OK"}` 정상 응답 확인 |
| **재발 방지** | 볼륨 마운트 대상 파일 경로와 폴더 스펠링(`nginx`)을 `docker-compose.yml`과 대조 검증한 뒤 실행하고, `docker compose exec nginx nginx -t`로 설정 로드 여부를 함께 점검 |

---

## 사례 2. Nginx `default.conf` 볼륨 마운트 전 디렉토리 생성 이슈

| 항목 | 내용 |
| :--- | :--- |
| **증상(문제 상황)** | `nginx/default.conf`를 편집하려 했으나 파일이 아니라 빈 디렉토리(`nginx/default.conf/`)로 생성되어 있었음 |
| **원인 가설** | 파일 생성 시 디렉토리 생성 명령/동작이 잘못 실행되어 `default.conf`가 폴더로 만들어짐 (이 상태로 `docker compose up` 시 파일 경로에 디렉토리를 마운트하려는 오류 발생) |
| **검증 방법** | `ls -la nginx/ nginx/default.conf/`로 파일 타입이 디렉토리(`d`)임을 확인 |
| **조치 내용** | 빈 디렉토리 `nginx/default.conf/`를 제거(`rmdir`)하고 일반 파일(`touch nginx/default.conf`)로 재생성한 뒤 설정 작성 |
| **결과** | Nginx 컨테이너에 `:ro` 파일 마운트가 정상적으로 적용됨 |
| **재발 방지** | 호스트 파일을 컨테이너에 단일 파일 마운트할 때는 실행 전 `ls -l`로 파일 여부와 내용 존재 여부를 먼저 확인 |

---

## 사례 3. HTTPS 설정(`default-ssl.conf`) 내 Nginx 리다이렉트 변수명 오타

| 항목 | 내용 |
| :--- | :--- |
| **증상(문제 상황)** | HTTP → HTTPS 301 리다이렉트 설정 작성 시 `return 301 https://$host$request_url;`로 기재하여 Nginx 설정 오류 위험 발생 |
| **원인 가설** | Nginx 내장 변수명을 `$request_uri` 대신 `$request_url`로 잘못 표기하여, 리로드 시 `unknown "request_url" variable` 에러가 발생할 수 있음 |
| **검증 방법** | 설정 파일 검토 및 EC2에서 `docker compose exec nginx nginx -t` 문법 검사 수행 |
| **조치 내용** | `nginx/default-ssl.conf` 9번 줄을 `return 301 https://$host$request_uri;`로 수정 |
| **결과** | `nginx -t`에서 `syntax is ok` / `test is successful` 확인 후 `nginx -s reload`로 무중단 HTTPS 전환 성공 |
| **재발 방지** | Nginx 설정을 교체한 뒤에는 바로 `reload`하지 않고 반드시 `nginx -t`로 문법 및 변수 검사를 선행 |
