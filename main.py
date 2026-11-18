import sys
import os
import time

def check_status():
    print("\n" + "="*45)
    print(" [HomeShot Core] 현재 로컬 서버 상태 점검")
    print("="*45)
    print(" - 실행 런타임: WSL2 Ubuntu 26.04 LTS")
    print(" - 관리 대상 포트: 8080 (Local Web Server)")
    print(" - 배포 상태: 🔴 대기 중 (Offline)")
    print(" - 보안 터널: Cloudflare Ingress Tunnel Ready")
    print("="*45 + "\n")

def simulate_deploy():
    print("\n" + "="*45)
    print(" [HomeShot Core] 온프레미스 원클릭 배포 시뮬레이션")
    print("="*45)
    print("1. 로컬 프로젝트 파일(index.html) 검사 완료...")
    time.sleep(0.5)
    print("2. WSL2 백그라운드 웹 서버 구동 중...")
    time.sleep(0.5)
    print("3. 보안 터널(Ingress Tunnel) 연결 중...")
    time.sleep(0.8)
    print("\n🎉 배포 성공! 외부 접속 주소가 발급되었습니다:")
    print("👉 https://homeshot-demo.trycloudflare.com")
    print("="*45 + "\n")

def main():
    while True:
        print("\n--- 🚀 [HomeShot 에이전트 콘솔] ---")
        print("1. 현재 서버 상태 확인")
        print("2. 원클릭 배포 시동 (시뮬레이션)")
        print("0. 종료")
        choice = input("선택하세요: ").strip()

        if choice == "1":
            check_status()
        elif choice == "2":
            simulate_deploy()
        elif choice == "0":
            print("HomeShot 에이전트를 종료합니다. 안녕히 가세요!")
            break
        else:
            print("올바른 번호를 입력해 주세요. (1, 2, 0)")

if __name__ == "__main__":
    main()
