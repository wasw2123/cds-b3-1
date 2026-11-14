# AWS 웹 서비스 인프라 구축 및 배포 (CDS Cloud Mission)

## 1. 프로젝트 개요
AWS 서울 리전(`ap-northeast-2`)에 직접 VPC 네트워크를 설계하고, 최소권한 IAM과 보안 그룹을 적용한 뒤 Docker Compose(Nginx + FastAPI + Let's Encrypt HTTPS)로 웹 서비스를 배포한 프로젝트입니다.

## 2. 아키텍처
- 아키텍처 다이어그램: [docs/architecture.png](docs/architecture.png) *(작성 후 추가)*
- 트래픽 흐름: `Client (HTTPS 443 / HTTP 80)` → `Internet Gateway` → `Public Subnet` → `Security Group` → `EC2 (Nginx 컨테이너)` → `FastAPI 컨테이너 (8000)`

## 3. 외부 접속 검증 정보
- **도메인**: `https://cds-smh.duckdns.org`
- **퍼블릭 IP (Elastic IP)**: `13.124.71.205`
- **검증 방식 (A & B)**:
  - (A) 브라우저 접속: `https://cds-smh.duckdns.org` → 메인 페이지(`Hello Cloud!`) 정상 출력
  - (B) 헬스체크 호출: `GET https://cds-smh.duckdns.org/health` → `200 OK` / `OK`
- **접속 결과 스크린샷**: *(여기에 스크린샷 이미지 링크 추가)*

## 4. Docker 컨테이너 구성 (보너스 과제)
- **FastAPI (`fastapi-app`)**: `./app/Dockerfile` (`python:3.12-slim` 기반 빌드)
  - 내부 포트: `8000` (외부 직접 노출 없이 Docker 내부 네트워크로만 통신)
- **Nginx (`nginx-proxy`)**: `nginx:1.27-alpine`
  - 포트 매핑: `80:80`, `443:443`
- **실행 명령**:
  ```bash
  docker compose up -d --build
  ```
- **컨테이너 상태(`docker ps`) 및 외부 접속 스크린샷**: *(여기에 스크린샷 2장 이상 추가)*

## 5. 문서 목록
- 트러블슈팅 보고서: [docs/troubleshooting.md](docs/troubleshooting.md)
- 리소스 정리 체크리스트: [docs/cleanup-checklist.md](docs/cleanup-checklist.md)
- 구축 과정 스크린샷: [docs/screenshots/](docs/screenshots/)
