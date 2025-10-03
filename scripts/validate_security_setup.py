#!/usr/bin/env python3
"""Security Setup Validation Script.

This script validates that all security measures are properly configured
and working correctly in the AniVault project.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class SecurityValidator:
    """Validates security configuration and setup."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {"passed": [], "failed": [], "warnings": []}

    def validate_all(self) -> Dict[str, Any]:
        """Run all security validations."""
        print("🔍 Starting AniVault Security Validation...")
        print("=" * 50)

        # Core security validations
        self._validate_cursor_rules()
        self._validate_pre_commit_hooks()
        self._validate_ci_pipeline()
        self._validate_gitignore()
        self._validate_environment_security()
        self._validate_dependencies()
        self._validate_secrets_baseline()

        # Generate summary
        self._generate_summary()

        return self.results

    def _validate_cursor_rules(self) -> None:
        """Validate Cursor security rules."""
        print("\n📋 Validating Cursor Security Rules...")

        rules_file = self.project_root / ".cursor" / "rules" / "ai_security.mdc"

        if rules_file.exists():
            content = rules_file.read_text(encoding="utf-8")

            # Check for key security patterns
            required_patterns = [
                "프롬프트 인젝션 방어",
                "매직 값 금지",
                "중복 정의 금지",
                "시크릿/민감 정보 보호",
                "테스트 없는 변경 금지",
            ]

            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)

            if missing_patterns:
                self.results["failed"].append(
                    f"Cursor rules missing patterns: {missing_patterns}"
                )
            else:
                self.results["passed"].append(
                    "Cursor security rules properly configured"
                )
        else:
            self.results["failed"].append("AI security rules file not found")

    def _validate_pre_commit_hooks(self) -> None:
        """Validate pre-commit hooks configuration."""
        print("\n🔧 Validating Pre-commit Hooks...")

        precommit_file = self.project_root / ".pre-commit-config.yaml"

        if precommit_file.exists():
            content = precommit_file.read_text(encoding="utf-8")

            # Check for security tools
            security_tools = [
                "bandit",
                "safety",
                "detect-secrets",
                "security_check.py",
                "detect_magic_values.py",
                "check_duplicates.py",
                "check_secrets.py",
            ]

            missing_tools = []
            for tool in security_tools:
                if tool not in content:
                    missing_tools.append(tool)

            if missing_tools:
                self.results["warnings"].append(
                    f"Pre-commit missing security tools: {missing_tools}"
                )
            else:
                self.results["passed"].append("Pre-commit hooks properly configured")
        else:
            self.results["failed"].append("Pre-commit configuration not found")

    def _validate_ci_pipeline(self) -> None:
        """Validate CI/CD security pipeline."""
        print("\n🚀 Validating CI/CD Security Pipeline...")

        ci_file = self.project_root / ".github" / "workflows" / "security-ci.yml"

        if ci_file.exists():
            content = ci_file.read_text(encoding="utf-8")

            # Check for security jobs
            security_jobs = [
                "security-scan",
                "code-quality",
                "dependency-check",
                "pre-commit",
            ]

            missing_jobs = []
            for job in security_jobs:
                if job not in content:
                    missing_jobs.append(job)

            if missing_jobs:
                self.results["warnings"].append(
                    f"CI pipeline missing security jobs: {missing_jobs}"
                )
            else:
                self.results["passed"].append(
                    "CI/CD security pipeline properly configured"
                )
        else:
            self.results["failed"].append("Security CI pipeline not found")

    def _validate_gitignore(self) -> None:
        """Validate .gitignore security patterns."""
        print("\n📁 Validating .gitignore Security Patterns...")

        gitignore_file = self.project_root / ".gitignore"

        if gitignore_file.exists():
            content = gitignore_file.read_text(encoding="utf-8")

            # Check for security-sensitive patterns
            security_patterns = [
                ".env",
                "secrets.json",
                ".secrets.baseline",
                "security-report.json",
                "*.pem",
                "*.key",
                "*.crt",
            ]

            missing_patterns = []
            for pattern in security_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)

            if missing_patterns:
                self.results["warnings"].append(
                    f".gitignore missing security patterns: {missing_patterns}"
                )
            else:
                self.results["passed"].append(
                    ".gitignore properly configured for security"
                )
        else:
            self.results["failed"].append(".gitignore file not found")

    def _validate_environment_security(self) -> None:
        """Validate environment variable security."""
        print("\n🔐 Validating Environment Security...")

        # Check for .env template
        env_template = self.project_root / "env.template"
        if env_template.exists():
            self.results["passed"].append("Environment template file exists")
        else:
            self.results["warnings"].append("Environment template file not found")

        # Check for actual .env file (should not exist in repo)
        env_file = self.project_root / ".env"
        if env_file.exists():
            self.results["warnings"].append(
                ".env file found in repository (should be in .gitignore)"
            )
        else:
            self.results["passed"].append("No .env file in repository")

        # Check MCP configuration
        mcp_file = self.project_root / ".cursor" / "mcp.json"
        if mcp_file.exists():
            content = mcp_file.read_text(encoding="utf-8")
            if "YOUR_" in content and "${" not in content:
                self.results["warnings"].append(
                    "MCP configuration may contain placeholder API keys"
                )
            else:
                self.results["passed"].append(
                    "MCP configuration uses environment variables"
                )

    def _validate_dependencies(self) -> None:
        """Validate dependency security."""
        print("\n📦 Validating Dependency Security...")

        # Check requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text(encoding="utf-8")

            # Check for known vulnerable packages
            vulnerable_packages = ["pickle", "marshal", "eval", "exec"]

            found_vulnerable = []
            for package in vulnerable_packages:
                if package in content:
                    found_vulnerable.append(package)

            if found_vulnerable:
                self.results["warnings"].append(
                    f"Potentially vulnerable packages found: {found_vulnerable}"
                )
            else:
                self.results["passed"].append("No obviously vulnerable packages found")

        # Check pyproject.toml security config
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text(encoding="utf-8")
            if "[tool.anivault.security]" in content:
                self.results["passed"].append(
                    "Security configuration found in pyproject.toml"
                )
            else:
                self.results["warnings"].append(
                    "Security configuration missing in pyproject.toml"
                )

    def _validate_secrets_baseline(self) -> None:
        """Validate secrets baseline configuration."""
        print("\n🔍 Validating Secrets Baseline...")

        baseline_file = self.project_root / ".secrets.baseline"

        if baseline_file.exists():
            self.results["passed"].append("Secrets baseline file exists")
        else:
            self.results["warnings"].append(
                "Secrets baseline file not found - run 'detect-secrets scan --baseline .secrets.baseline'"
            )

    def _validate_security_scripts(self) -> None:
        """Validate security scripts exist and are executable."""
        print("\n🛠️ Validating Security Scripts...")

        scripts_dir = self.project_root / "scripts"
        required_scripts = [
            "security_check.py",
            "detect_magic_values.py",
            "check_duplicates.py",
            "check_secrets.py",
        ]

        missing_scripts = []
        for script in required_scripts:
            script_path = scripts_dir / script
            if not script_path.exists():
                missing_scripts.append(script)
            elif not os.access(script_path, os.X_OK):
                self.results["warnings"].append(
                    f"Security script not executable: {script}"
                )

        if missing_scripts:
            self.results["failed"].append(
                f"Missing security scripts: {missing_scripts}"
            )
        else:
            self.results["passed"].append("All required security scripts present")

    def _generate_summary(self) -> None:
        """Generate validation summary."""
        print("\n" + "=" * 50)
        print("📊 Security Validation Summary")
        print("=" * 50)

        total_checks = (
            len(self.results["passed"])
            + len(self.results["failed"])
            + len(self.results["warnings"])
        )

        print(f"✅ Passed: {len(self.results['passed'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"📊 Total: {total_checks}")

        if self.results["failed"]:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in self.results["failed"]:
                print(f"   ❌ {issue}")

        if self.results["warnings"]:
            print("\n⚠️  WARNINGS:")
            for warning in self.results["warnings"]:
                print(f"   ⚠️  {warning}")

        if self.results["passed"]:
            print("\n✅ PASSED CHECKS:")
            for passed in self.results["passed"]:
                print(f"   ✅ {passed}")

        # Overall status
        if not self.results["failed"]:
            print("\n🎉 Security validation PASSED!")
            print("   All critical security measures are in place.")
        else:
            print("\n🚨 Security validation FAILED!")
            print("   Please fix critical issues before proceeding.")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("   1. Run 'pre-commit install' to activate hooks")
        print("   2. Run 'detect-secrets scan --baseline .secrets.baseline'")
        print("   3. Review and fix any warnings")
        print("   4. Test security pipeline with 'pre-commit run --all-files'")


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent

    validator = SecurityValidator(project_root)
    results = validator.validate_all()

    # Exit with error code if critical issues found
    if results["failed"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
