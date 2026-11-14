# AWS 웹 서비스 인프라 구축 및 배포 (CDS Cloud Mission)

AWS 서울 리전(`ap-northeast-2`)에 VPC 격리 네트워크와 최소권한 IAM·보안 그룹을 직접 설계하고, **Docker Compose(Nginx + FastAPI + Let's Encrypt HTTPS)** 기반 웹 서비스를 배포·운영·정리한 프로젝트입니다.

---

## 1. 아키텍처 다이어그램

![AWS Architecture](docs/architecture.png)

- **트래픽 흐름**: `외부 사용자 (HTTPS 443 / HTTP 80)` → `DuckDNS (cds-smh.duckdns.org)` → `Internet Gateway` → `Route Table (0.0.0.0/0 → IGW)` → `Public Subnet` → `Security Group` → `EC2 (Nginx 컨테이너)` → `FastAPI 컨테이너 (8000)`

---

## 2. 인프라 및 보안 구성 요약

| 구분 | 구성 내용 |
| :--- | :--- |
| **리전** | `ap-northeast-2` (서울) |
| **IAM** | Root 계정 미사용 · 실습용 IAM 사용자에 EC2 / VPC / Security Group 권한만 최소 부여 (`AdministratorAccess` 미부여) |
| **네트워크** | VPC `cds-b3-1-vpc` (`10.0.0.0/16`), Public Subnet (`ap-northeast-2a`), Internet Gateway, Route Table (`0.0.0.0/0 → IGW`) |
| **컴퓨트** | EC2 `cds-b3-1` (`t3.micro`, Ubuntu 26.04.1 LTS, Elastic IP `13.124.71.205`, Private IP `10.0.13.48`) |
| **보안 그룹** | Inbound: `HTTPS(443)` `0.0.0.0/0`, `HTTP(80)` `0.0.0.0/0`, `SSH(22)` `학습자 공인 IP/32` |

### 2-1. 표준 리소스 네이밍 및 태그 정책
- **네이밍 규칙**: `<프로젝트>-<리소스유형>` (예: `cds-b3-1-vpc`, `cds-b3-1`)으로 통일해 리소스 식별과 정리 대상 추적을 용이하게 합니다.
- **표준 태그 정책**:
  - `Name`: 리소스 식별 이름 (예: `cds-b3-1`, `cds-b3-1-vpc`)
  - `Project`: `cds-b3-1` (과제/서비스 단위 구분)
  - `Env`: `dev` (실습·개발 환경 구분)
  - `Owner`: `smh` (리소스 소유자 및 과금 책임 주체 명시)

### 2-2. 아웃바운드 통신 필요성 (Route Table & Security Group)
- Public Subnet의 Route Table(`0.0.0.0/0 → IGW`)과 아웃바운드 허용 설정은 외부 요청 응답뿐만 아니라, EC2 내부에서 **OS 보안 패치(`apt-get update`), Docker 이미지 Pull(`nginx`, `python`, `uv`, `certbot`), Let's Encrypt ACME 서버 통신을 통한 SSL 인증서 발급**을 수행하기 위해 반드시 필요합니다.

### 2-3. 보안 그룹 허용·차단 기준 및 `0.0.0.0/0` 위험과 대안 비교
- **규칙별 허용/차단 기준**:
  - `HTTPS(443)` / `HTTP(80)` (`0.0.0.0/0` 허용): 불특정 다수 사용자의 웹 서비스 접속 및 Let's Encrypt HTTP-01 인증서 발급·HTTPS 리다이렉트를 위해 허용합니다.
  - `SSH(22)` (`학습자 공인 IP/32`만 허용): 서버 관리 목적의 포트이므로 학습자 개인 IP만 허용하고, 그 외 IP와 불필요한 포트(애플리케이션 내부 포트 `8000` 및 전체 포트 `0-65535`)는 모두 차단(최소 포트 원칙)합니다.
- **`0.0.0.0/0` 개방 위험 및 대안 비교**:
  - 관리 포트(`22`)나 전체 포트(`0-65535`)를 `0.0.0.0/0`으로 개방하면 자동화된 포트 스캐닝, SSH 무차별 대입 공격(Brute Force), 미패치 서비스 취약점 악용에 직접 노출됩니다.
  - 이를 방지하기 위해 본 실습에서는 **단일 공인 IP(`/32`) 제한**을 적용했으며, 운영 환경으로 확장 시에는 **VPN / Bastion Host / AWS SSM Session Manager**를 통해 SSH 포트를 아예 닫고, 웹 트래픽(`80/443`)은 EC2 앞단에 **ALB(Application Load Balancer)**를 두어 EC2 보안 그룹이 ALB 보안 그룹만 허용하도록 격리하는 것이 더 안전합니다.

### 2-4. IAM 최소권한 및 점진적 권한 확대·감사 절차
- 초기에는 EC2, VPC, Security Group 생성·조회·연결에 필요한 최소 권한만 부여하고, S3·RDS 등 실습과 무관한 서비스 및 `AdministratorAccess`는 배제합니다.
- **권한 확장 및 감사 절차**: 작업 중 추가 권한이 필요한 경우 ① **요청**(필요 서비스·액션·사유 명시) → ② **검토 및 승인**(관리자가 리소스 범위와 최소 권한 여부 확인 후 정책 추가) → ③ **사후 감사**(CloudTrail / IAM Access Analyzer로 실제 사용 이력 점검 및 임시 권한 회수) 단계를 거쳐 점진적으로 관리합니다.

---

## 3. 외부 접속 및 SSH 검증 (필수 과제 & 보너스 1: HTTPS)

- **선택한 검증 방식**: **(A) 브라우저 접속** + **(B) 헬스체크(`/health`) 병행 검증**
- **접속 주소**:
  - 도메인 (HTTPS): `https://cds-smh.duckdns.org`
  - 헬스체크: `https://cds-smh.duckdns.org/health` (내부 `http://localhost/health` 포함)
  - 퍼블릭 IP (Elastic IP): `13.124.71.205`
- **방식 선택 장단점 및 구성 단계별 체크포인트**:
  - *장단점*: Nginx + FastAPI를 Docker Compose로 함께 컨테이너화하면 설정(IaC) 재현성과 서비스 격리가 뛰어나고, Certbot과 볼륨(`/etc/letsencrypt`, `/var/www/certbot`)을 공유해 무료 HTTPS까지 자동화할 수 있습니다. 반면 초기 인증서 발급 전에는 Nginx가 SSL 설정을 읽지 못하므로 1단계(HTTP) → 인증서 발급 → 2단계(HTTPS) 순서로 분리해야 합니다.
  - *체크포인트*: ① Elastic IP·DuckDNS DNS 매핑 확인 → ② Docker Compose 빌드 및 `curl http://localhost/health` 200 확인 → ③ Certbot `--webroot` 인증서 발급 → ④ `nginx -t` 문법 검사 후 `nginx -s reload` → ⑤ 외부 HTTPS 접속 확인.
- **HTTPS 적용 방식 (보너스 1)**:
  - DuckDNS 무료 서브도메인(`cds-smh.duckdns.org`)을 Elastic IP(`13.124.71.205`)에 연결
  - `certbot/certbot` 컨테이너(`--webroot`)로 Let's Encrypt SSL 인증서 발급
  - Nginx에서 HTTP(`80`) 요청을 HTTPS(`443`)로 `301` 리다이렉트 및 TLS 종료 처리

### 검증 스크린샷

- **EC2 SSH 접속 성공 증빙** (`2026-11-14 07:05:47 UTC` / KST `16:05:47`, `ubuntu@13.124.71.205`, Private IP `10.0.13.48`)
  ![ssh login](docs/screenshots/7-server/07-server-1.png)

- **EC2 내부 `http://localhost` & `http://localhost/health` (`200 OK`)**
  ![localhost health](docs/screenshots/7-server/07-server-9.png)

- **외부 브라우저 HTTPS 접속 결과 (`https://cds-smh.duckdns.org`)**
  ![HTTPS Browser](docs/screenshots/7-server/07-server-13.png)

---

## 4. Docker 컨테이너 구성 (보너스 2)

| 서비스 | 이미지 / 빌드 | 포트 매핑 | 역할 |
| :--- | :--- | :--- | :--- |
| `fastapi` (`cds-b3-1-fastapi-1`) | `./Dockerfile` (`python:3.14-slim` + `uv`) | `expose: 8000` (내부망 전용) | FastAPI 웹 서버 (`GET /`, `GET /health` → `{"status":"OK"}`) |
| `nginx` (`cds-b3-1-nginx-1`) | `nginx:1.27-alpine` | `80:80`, `443:443` | TLS 종료, HTTP→HTTPS 리다이렉트, `http://fastapi:8000` 리버스 프록시 |
| `certbot` | `certbot/certbot` (`profiles: ["certbot"]`) | - | Let's Encrypt 인증서 발급/갱신 (`/etc/letsencrypt`, `/var/www/certbot` 볼륨 공유) |

- **실행 방식**:
  ```bash
  # 1) HTTP 모드로 컨테이너 빌드 및 실행
  docker compose up -d --build

  # 2) Let's Encrypt SSL 인증서 발급
  docker compose run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email <email> --agree-tos --no-eff-email \
    -d cds-smh.duckdns.org

  # 3) HTTPS 설정 적용 및 무중단 리로드
  cp nginx/default-ssl.conf nginx/default.conf
  docker compose exec nginx nginx -t
  docker compose exec nginx nginx -s reload
  ```

- **컨테이너 실행 상태 (`docker ps`)**
  ![docker ps](docs/screenshots/7-server/07-server-7.png)

- **SSL 인증서 발급 및 Nginx 리로드**
  ![certbot and reload](docs/screenshots/7-server/07-server-12.png)

---

## 5. 단계별 구축 진행 과정 및 스크린샷

### Step 1. 리전 설정 (`ap-northeast-2` 서울)
- 모든 AWS 리소스를 서울 리전(`ap-northeast-2`)에 생성하도록 콘솔 리전을 설정했습니다.

<details>
<summary>스크린샷 보기 (1-region: 3장)</summary>

![01-region-1](docs/screenshots/1-region/01-region-1.png)
![01-region-2](docs/screenshots/1-region/01-region-2.png)
![01-region-3](docs/screenshots/1-region/01-region-3.png)

</details>

### Step 2. IAM 최소권한 사용자 구성
- Root 계정을 사용하지 않고, 실습에 필요한 EC2·VPC·Security Group 권한만 부여한 IAM 사용자를 생성해 접속했습니다. (`AdministratorAccess` 미부여)

<details>
<summary>스크린샷 보기 (2-iam: 10장)</summary>

![02-iam-1](docs/screenshots/2-iam/02-iam-1.png)
![02-iam-2](docs/screenshots/2-iam/02-iam-2.png)
![02-iam-3](docs/screenshots/2-iam/02-iam-3.png)
![02-iam-4](docs/screenshots/2-iam/02-iam-4.png)
![02-iam-5](docs/screenshots/2-iam/02-iam-5.png)
![02-iam-6](docs/screenshots/2-iam/02-iam-6.png)
![02-iam-7](docs/screenshots/2-iam/02-iam-7.png)
![02-iam-8](docs/screenshots/2-iam/02-iam-8.png)
![02-iam-9](docs/screenshots/2-iam/02-iam-9.png)
![02-iam-10](docs/screenshots/2-iam/02-iam-10.png)

</details>

### Step 3. VPC 네트워크 구성
- VPC(`cds-b3-1-vpc`, `10.0.0.0/16`), Public Subnet, Internet Gateway(IGW)를 생성하고 Route Table에 `0.0.0.0/0 → IGW` 경로를 연결했습니다.

<details>
<summary>스크린샷 보기 (3-vpc: 7장)</summary>

![03-vpc-1](docs/screenshots/3-vpc/03-vpc-1.png)
![03-vpc-2](docs/screenshots/3-vpc/03-vpc-2.png)
![03-vpc-3](docs/screenshots/3-vpc/03-vpc-3.png)
![03-vpc-4](docs/screenshots/3-vpc/03-vpc-4.png)
![03-vpc-5](docs/screenshots/3-vpc/03-vpc-5.png)
![03-vpc-6](docs/screenshots/3-vpc/03-vpc-6.png)
![03-vpc-7](docs/screenshots/3-vpc/03-vpc-7.png)

</details>

### Step 4. 보안 그룹(Security Group) 설정
- 인바운드는 필요한 포트만 허용했습니다: `HTTPS(443)` `0.0.0.0/0`, `HTTP(80)` `0.0.0.0/0`, `SSH(22)` `학습자 공인 IP/32`.

<details>
<summary>스크린샷 보기 (4-SG: 4장)</summary>

![04-SG-1](docs/screenshots/4-SG/04-SG-1.png)
![04-SG-2](docs/screenshots/4-SG/04-SG-2.png)
![04-SG-3](docs/screenshots/4-SG/04-SG-3.png)
![04-SG-4](docs/screenshots/4-SG/04-SG-4.png)

</details>

### Step 5. EC2 인스턴스 생성
- Public Subnet(`ap-northeast-2a`)에 `t3.micro` Ubuntu 인스턴스(`cds-b3-1`)를 생성했습니다.

<details>
<summary>스크린샷 보기 (5-ec2: 10장)</summary>

![05-ec2-1](docs/screenshots/5-ec2/05-ec2-1.png)
![05-ec2-2](docs/screenshots/5-ec2/05-ec2-2.png)
![05-ec2-3](docs/screenshots/5-ec2/05-ec2-3.png)
![05-ec2-4](docs/screenshots/5-ec2/05-ec2-4.png)
![05-ec2-5](docs/screenshots/5-ec2/05-ec2-5.png)
![05-ec2-6](docs/screenshots/5-ec2/05-ec2-6.png)
![05-ec2-7](docs/screenshots/5-ec2/05-ec2-7.png)
![05-ec2-8](docs/screenshots/5-ec2/05-ec2-8.png)
![05-ec2-9](docs/screenshots/5-ec2/05-ec2-9.png)
![05-ec2-10](docs/screenshots/5-ec2/05-ec2-10.png)

</details>

### Step 6. Elastic IP 할당 및 DuckDNS 도메인 연결
- Elastic IP(`13.124.71.205`)를 EC2에 연결하고, DuckDNS(`cds-smh.duckdns.org`)에 해당 IP를 매핑했습니다.

<details>
<summary>스크린샷 보기 (6-domain_n_elastic_ip: 8장)</summary>

![03-domain_n_elastic_ip-1](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-1.png)
![03-domain_n_elastic_ip-2](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-2.png)
![03-domain_n_elastic_ip-3](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-3.png)
![03-domain_n_elastic_ip-4](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-4.png)
![03-domain_n_elastic_ip-5](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-5.png)
![03-domain_n_elastic_ip-6](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-6.png)
![03-domain_n_elastic_ip-7](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-7.png)
![03-domain_n_elastic_ip-8](docs/screenshots/6-domain_n_elastic_ip/03-domain_n_elastic_ip-8.png)

</details>

### Step 7. Docker Compose 배포 & Certbot HTTPS 적용
- EC2에 Git 레포지토리를 클론한 뒤 Docker Compose로 FastAPI·Nginx를 실행하고, Certbot으로 SSL 인증서를 발급받아 HTTPS를 적용했습니다.

<details>
<summary>스크린샷 보기 (7-server: 13장)</summary>

![07-server-1](docs/screenshots/7-server/07-server-1.png)
![07-server-2](docs/screenshots/7-server/07-server-2.png)
![07-server-3](docs/screenshots/7-server/07-server-3.png)
![07-server-4](docs/screenshots/7-server/07-server-4.png)
![07-server-5](docs/screenshots/7-server/07-server-5.png)
![07-server-6](docs/screenshots/7-server/07-server-6.png)
![07-server-7](docs/screenshots/7-server/07-server-7.png)
![07-server-8](docs/screenshots/7-server/07-server-8.png)
![07-server-9](docs/screenshots/7-server/07-server-9.png)
![07-server-10](docs/screenshots/7-server/07-server-10.png)
![07-server-11](docs/screenshots/7-server/07-server-11.png)
![07-server-12](docs/screenshots/7-server/07-server-12.png)
![07-server-13](docs/screenshots/7-server/07-server-13.png)

</details>

### Step 8. 리소스 정리 (과금 방지)
- 실습 종료 후 EC2, Elastic IP, VPC 및 종속 네트워크 리소스를 순서대로 삭제/릴리스했습니다.

<details>
<summary>스크린샷 보기 (8-end: 12장)</summary>

![08-end-1](docs/screenshots/8-end/08-end-1.png)
![08-end-2](docs/screenshots/8-end/08-end-2.png)
![08-end-3](docs/screenshots/8-end/08-end-3.png)
![08-end-4](docs/screenshots/8-end/08-end-4.png)
![08-end-5](docs/screenshots/8-end/08-end-5.png)
![08-end-6](docs/screenshots/8-end/08-end-6.png)
![08-end-7](docs/screenshots/8-end/08-end-7.png)
![08-end-8](docs/screenshots/8-end/08-end-8.png)
![08-end-9](docs/screenshots/8-end/08-end-9.png)
![08-end-10](docs/screenshots/8-end/08-end-10.png)
![08-end-11](docs/screenshots/8-end/08-end-11.png)
![08-end-12](docs/screenshots/8-end/08-end-12.png)

</details>

---

## 6. 문서 및 증빙 목록

- 아키텍처 다이어그램: [docs/architecture.png](docs/architecture.png)
- 트러블슈팅 보고서: [docs/troubleshooting.md](docs/troubleshooting.md)
- 리소스 정리 체크리스트: [docs/cleanup-checklist.md](docs/cleanup-checklist.md)
- 단계별 전체 스크린샷: [docs/screenshots/](docs/screenshots/) (`1-region` ~ `8-end`)
