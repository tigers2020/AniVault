#!/usr/bin/env python3
"""의존성 체크 및 자동 설치 스크립트."""

import json
import subprocess
import sys
from pathlib import Path


def check_package(python_cmd: str, package_name: str, import_name: str | None = None) -> tuple[bool, str]:
    """패키지 설치 여부 확인."""
    if import_name is None:
        import_name = package_name

    try:
        # Use shell=True on Windows for better compatibility
        # Increase timeout for packages that may take longer to import (e.g., scikit-learn)
        import platform

        use_shell = platform.system() == "Windows"
        timeout_value = 30 if package_name in ("scikit-learn", "datasketch") else 10

        result = subprocess.run(
            [python_cmd, "-c", f"import {import_name}"],
            capture_output=True,
            text=True,
            timeout=timeout_value,
            shell=use_shell,
            check=False,
        )

        is_installed = result.returncode == 0
        return is_installed, result.stderr if result.stderr else ""
    except subprocess.TimeoutExpired:
        # Timeout doesn't necessarily mean package is missing - it might just be slow
        # Try a simpler check using pip list
        try:
            result = subprocess.run(
                [python_cmd, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=use_shell,
                check=False,
            )
            if result.returncode == 0:
                installed_packages = json.loads(result.stdout)
                package_found = any(pkg["name"].lower() == package_name.lower() for pkg in installed_packages)
                if package_found:
                    # Package is installed but import is slow - consider it OK
                    return True, "Installed but slow import"
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def install_requirements(python_cmd: str, requirements_file: str) -> tuple[bool, str]:
    """requirements.txt 설치."""
    try:
        result = subprocess.run(
            [python_cmd, "-m", "pip", "install", "-r", requirements_file],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )

        success = result.returncode == 0
        return success, result.stderr if result.stderr else result.stdout
    except subprocess.TimeoutExpired:
        return False, "Installation timeout"
    except Exception as e:
        return False, str(e)


def main() -> int:
    """메인 함수."""
    # Python 명령어 결정
    python_cmd = sys.executable
    if len(sys.argv) > 1:
        python_cmd = sys.argv[1]

    # 필수 패키지 목록
    required_packages = [
        ("PySide6", "PySide6"),
        ("pydantic", "pydantic"),
        ("dependency-injector", "dependency_injector"),
        ("datasketch", "datasketch"),
        ("scikit-learn", "sklearn"),
    ]

    missing_packages = []

    # 각 패키지 체크
    for package_name, import_name in required_packages:
        is_installed, _ = check_package(python_cmd, package_name, import_name)
        if not is_installed:
            missing_packages.append(package_name)
            print(f"[MISSING] {package_name}")
        else:
            print(f"[OK] {package_name}")

    # 누락된 패키지가 있으면 설치
    if missing_packages:
        requirements_file = Path(__file__).parent / "requirements.txt"
        if not requirements_file.exists():
            print(f"[ERROR] requirements.txt not found at {requirements_file}")
            return 1

        print(f"\n[INSTALL] Installing {len(missing_packages)} missing package(s)...")
        success, output = install_requirements(python_cmd, str(requirements_file))

        if not success:
            print(f"[ERROR] Installation failed:\n{output[:500]}")
            return 1

        # 설치 후 다시 체크
        print("\n[VERIFY] Verifying installation...")
        all_ok = True
        for package_name, import_name in required_packages:
            is_installed, _ = check_package(python_cmd, package_name, import_name)
            if not is_installed:
                print(f"[FAIL] {package_name} still missing after installation")
                all_ok = False
            else:
                print(f"[OK] {package_name}")

        if not all_ok:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
