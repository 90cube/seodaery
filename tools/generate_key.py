"""shared.key 생성 도구. 오프라인 배포용."""
import sys
import os

sys.path.insert(0, ".")


def main():
    """Fernet 대칭키를 생성하여 파일로 저장한다."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("오류: cryptography 패키지가 필요합니다.")
        print("설치: pip install cryptography")
        return

    output = sys.argv[1] if len(sys.argv) > 1 else "shared.key"

    if os.path.exists(output):
        confirm = input(
            f"'{output}' 파일이 이미 존재합니다. "
            "덮어쓰시겠습니까? (y/N): "
        )
        if confirm.lower() != "y":
            print("취소됨")
            return

    key = Fernet.generate_key()
    with open(output, "wb") as f:
        f.write(key)

    print(f"키 생성 완료: {output}")
    print(f"키 값: {key.decode()}")
    print()
    print("이 파일을 안전하게 보관하세요.")
    print(
        "클라이언트에 복사: "
        "서버와 같은 키를 사용해야 통신 가능합니다."
    )


if __name__ == "__main__":
    main()
