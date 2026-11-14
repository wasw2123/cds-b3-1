# 리소스 정리 체크리스트 (과금 방지)

실습 종료 후 생성한 모든 AWS 리소스를 의존성 역순으로 삭제/해제하고, 콘솔 스크린샷(`docs/screenshots/8-end/`)을 기준으로 정리 결과를 기록합니다.

- **대상 리전**: `ap-northeast-2` (서울)
- **정리 일시**: 2026-11-14 20:40 ~ 20:47

## 정리 항목

- [x] **EC2 인스턴스** (`cds-b3-1` / `i-0d39ea950ff667b27`): 종료(삭제) 요청 및 종료 진행 확인 ([08-end-1.png](screenshots/8-end/08-end-1.png) ~ [08-end-3.png](screenshots/8-end/08-end-3.png))
- [x] **Elastic IP** (`cds-b3-1` / `13.124.71.205` / `eipalloc-08de446ae85be6e46`): 릴리스(Release) 완료 확인 ([08-end-4.png](screenshots/8-end/08-end-4.png) ~ [08-end-6.png](screenshots/8-end/08-end-6.png))
- [x] **VPC 및 종속 네트워크 리소스** (`cds-b3-1-vpc` / `vpc-023017cc4642f1cc1`, `10.0.0.0/16`): VPC 및 기타 리소스 4개(Subnet, Route Table, Internet Gateway, Security Group) 일괄 삭제 완료 ([08-end-7.png](screenshots/8-end/08-end-7.png) ~ [08-end-9.png](screenshots/8-end/08-end-9.png))
- [x] **Route Table / Internet Gateway / Security Group 잔여 여부**: 각 콘솔 목록에서 실습용 리소스가 남아있지 않음을 확인 ([08-end-10.png](screenshots/8-end/08-end-10.png) ~ [08-end-12.png](screenshots/8-end/08-end-12.png))
- [x] **EBS 볼륨**: EC2 인스턴스 완전히 `Terminated` 전환 후 미사용(`available`) 볼륨이 남지 않았는지 콘솔에서 최종 확인
- [x] **NAT Gateway / ELB·ALB / RDS**: 실습 중 미생성 (비용 발생 대상 없음)
- [x] **Billing Dashboard**: AWS Billing Dashboard에서 과금 예정 항목이 남지 않는지 최종 확인

---

## 참고: 확장 및 병목 대응 기준 (ALB 적용 트리거)
본 실습은 단일 `t3.micro` EC2 구성으로 ELB/ALB를 생성하지 않았으나, 실제 서비스 확장 시에는 아래 병목 지표를 기준으로 모니터링하고 ALB(및 Auto Scaling) 도입을 검토합니다:
- **병목 확인 지표**:
  - **CPU 사용률**: 평균 70~80% 이상이 5분 이상 지속될 때
  - **메모리 사용률**: 가용 메모리 15% 이하 또는 OOM/스왑 급증 시
  - **응답 시간 / 에러율**: 평균 응답 시간(Latency) `> 500ms` 증가 또는 `5xx` 에러율 `> 1%` 발생 시
- **ALB 적용 트리거**: 위 지표가 임계치를 초과하거나 무중단 배포·고가용성(다중 AZ 분산)이 필요해질 때, EC2 앞단에 **ALB**를 배치하고 대상 그룹(Target Group) 헬스체크(`/health`)를 연동합니다.
