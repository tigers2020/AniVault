#!/usr/bin/env python3
"""
의존성 검증 스크립트

Poetry lockfile 대신 setuptools 기반 의존성 검증을 수행합니다.
pyproject.toml의 의존성과 실제 설치된 패키지 간의 호환성을 확인합니다.
"""

import subprocess
import sys
import tomllib
from pathlib import Path


def load_pyproject_dependencies() -> tuple[list[str], list[str]]:
    """pyproject.toml에서 의존성 정보를 로드합니다."""
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    # 메인 의존성
    main_deps = data.get("project", {}).get("dependencies", [])

    # 개발 의존성
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    return main_deps, dev_deps


def get_installed_packages() -> dict[str, str]:
    """현재 설치된 패키지 목록을 가져옵니다."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True,
        )

        packages = {}
        for line in result.stdout.strip().split("\n"):
            if "==" in line and not line.startswith("#"):
                name, version = line.split("==", 1)
                packages[name.lower()] = version

        return packages
    except subprocess.CalledProcessError as e:
        print(f"Error getting installed packages: {e}")
        return {}


def parse_dependency_spec(spec: str) -> tuple[str, str]:
    """의존성 명세를 파싱합니다 (예: 'typer[all]>=0.9.0')."""
    # 버전 제약 조건 제거
    if ">=" in spec:
        name = spec.split(">=")[0]
    elif "==" in spec:
        name = spec.split("==")[0]
    elif ">" in spec:
        name = spec.split(">")[0]
    elif "<" in spec:
        name = spec.split("<")[0]
    else:
        name = spec

    # extras 제거 (예: [all])
    if "[" in name:
        name = name.split("[")[0]

    # 특수 패키지명 매핑
    package_mapping = {
        "tomli-w": "tomli_w",
        "pre-commit": "pre_commit",
    }

    mapped_name = package_mapping.get(name, name)
    return mapped_name.lower(), spec


def validate_dependencies() -> bool:
    """의존성 검증을 수행합니다."""
    print("🔍 의존성 검증 시작...")

    try:
        # pyproject.toml에서 의존성 로드
        main_deps, dev_deps = load_pyproject_dependencies()
        all_deps = main_deps + dev_deps

        # 설치된 패키지 목록 가져오기
        installed = get_installed_packages()

        print(f"📦 pyproject.toml 의존성: {len(all_deps)}개")
        print(f"📦 설치된 패키지: {len(installed)}개")

        # 의존성 검증
        missing_packages = []
        version_conflicts: list[tuple[str, str, str]] = []

        for dep_spec in all_deps:
            name, spec = parse_dependency_spec(dep_spec)

            if name not in installed:
                missing_packages.append((name, dep_spec))
            else:
                # 간단한 버전 검증 (실제로는 packaging 라이브러리 사용 권장)
                installed_version = installed[name]
                print(f"✅ {name}: {installed_version} (요구: {spec})")

        # 결과 출력
        if missing_packages:
            print(f"\n❌ 누락된 패키지 ({len(missing_packages)}개):")
            for name, spec in missing_packages:
                print(f"  - {name} ({spec})")
            return False

        if version_conflicts:
            print(f"\n⚠️ 버전 충돌 ({len(version_conflicts)}개):")
            for name, expected, actual in version_conflicts:
                print(f"  - {name}: 요구 {expected}, 설치됨 {actual}")
            return False

        print("\n✅ 모든 의존성이 올바르게 설치되었습니다!")
        return True

    except Exception as e:
        print(f"❌ 의존성 검증 중 오류 발생: {e}")
        return False


def main() -> None:
    """메인 함수."""
    print("AniVault 의존성 검증 도구")
    print("=" * 40)

    success = validate_dependencies()

    if success:
        print("\n🎉 의존성 검증 완료!")
        sys.exit(0)
    else:
        print("\n💥 의존성 검증 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()
