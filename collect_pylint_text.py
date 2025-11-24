"""Collect pylint issues in text format."""
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
import re

def run_pylint_text():
    """Run pylint in text format and parse results."""
    cmd = [
        sys.executable,
        '-m', 'pylint',
        'src/anivault',
        '--recursive=y',
        '--disable=too-few-public-methods,duplicate-code,c-extension-no-member,no-name-in-module',
        '--msg-template={path}:{line}: [{msg_id}] {msg}'
    ]

    issues_by_code = defaultdict(list)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        # Parse text output
        pattern = re.compile(r'([^:]+):(\d+):\s+\[(\w+)\]\s+(.+)')

        for line in result.stdout.splitlines():
            match = pattern.match(line.strip())
            if match:
                file_path, line_num, msg_id, message = match.groups()
                # Normalize path
                file_path = file_path.replace('\\', '/')
                if 'src/anivault/' in file_path:
                    file_path = file_path.split('src/anivault/')[-1]

                issues_by_code[msg_id].append({
                    'file': file_path,
                    'line': int(line_num),
                    'message': message[:80]
                })

        # Print summary
        total = sum(len(v) for v in issues_by_code.values())
        print(f"Total issues found: {total}\n")

        if total == 0:
            print("No issues found! Check if pylint ran successfully.")
            print("\nPylint stderr:")
            print(result.stderr[:500])
            return 0

        print("Top issues by count:")
        print("=" * 80)

        for code, issues in sorted(issues_by_code.items(), key=lambda x: len(x[1]), reverse=True)[:25]:
            print(f"\n{code}: {len(issues)} occurrences")
            for issue in issues[:5]:
                print(f"  - {issue['file']}:{issue['line']} - {issue['message']}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")

        # Focus on key issues
        focus_codes = ['W0613', 'W0404', 'W0612', 'E1206', 'W0718', 'C0301', 'C0415', 'W0621']
        print("\n" + "=" * 80)
        print("Focus Issues:")
        print("=" * 80)

        for code in focus_codes:
            if code in issues_by_code:
                issues = issues_by_code[code]
                print(f"\n{code}: {len(issues)} occurrences")
                for issue in issues[:15]:
                    print(f"  - {issue['file']}:{issue['line']}")
                if len(issues) > 15:
                    print(f"  ... and {len(issues) - 15} more")

    except Exception as e:
        print(f"Error running pylint: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(run_pylint_text())
