# 리소스 정리 체크리스트 (과금 방지)

실습 종료 후 생성한 모든 AWS 리소스를 의존성 역순으로 삭제/해제하고 결과를 기록합니다.

- **대상 리전**: `ap-northeast-2` (서울)
- **확인 일시**: YYYY-MM-DD HH:MM

## 정리 항목
- [ ] **EC2 인스턴스** (`i-0d39ea950ff667b27`): 상태가 `Terminated(종료됨)`인지 확인
- [ ] **EBS 볼륨**: EC2 종료 후 남아있는 미사용(`available`) 볼륨이 없는지 확인 및 삭제
- [ ] **Elastic IP** (`13.124.71.205` / `eipalloc-08de446ae85be6e46`): 연결 해제(Disassociate) 후 **릴리스(Release)** 완료 확인
- [ ] **Internet Gateway**: VPC에서 분리(Detach) 후 삭제 확인
- [ ] **Subnet / Route Table / Security Group**: 사용자 생성 리소스 삭제 확인
- [ ] **VPC**: 생성한 VPC 삭제 완료 확인
- [ ] *(해당 시)* NAT Gateway / ELB·ALB / RDS: 생성한 적이 없거나 모두 삭제됨을 확인
- [ ] **Billing Dashboard**: AWS Billing 화면에서 예상 요금 / 활성 리소스가 남아있지 않은지 최종 확인
