"""Collect and analyze pylint issues."""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

def run_pylint():
    """Run pylint and collect results."""
    cmd = [
        sys.executable,
        '-m', 'pylint',
        'src/anivault',
        '--recursive=y',
        '--disable=too-few-public-methods,duplicate-code,c-extension-no-member,no-name-in-module',
        '--output-format=json'
    ]

    issues_by_code = defaultdict(list)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        # Parse JSON output
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                issue = json.loads(line)
                if issue.get('type') in ('warning', 'error'):
                    msg_id = issue.get('message-id', 'UNKNOWN')
                    file_path = issue.get('path', '').replace('\\', '/')
                    if 'src/anivault/' in file_path:
                        file_path = file_path.split('src/anivault/')[-1]

                    issues_by_code[msg_id].append({
                        'file': file_path,
                        'line': issue.get('line', 0),
                        'message': issue.get('message', '')[:80]
                    })
            except json.JSONDecodeError:
                continue

        # Print summary
        print(f"Total issues found: {sum(len(v) for v in issues_by_code.values())}\n")
        print("Top issues by count:")
        print("=" * 80)

        for code, issues in sorted(issues_by_code.items(), key=lambda x: len(x[1]), reverse=True)[:25]:
            print(f"\n{code}: {len(issues)} occurrences")
            for issue in issues[:5]:
                print(f"  - {issue['file']}:{issue['line']} - {issue['message']}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")

        # Focus on key issues
        focus_codes = ['W0613', 'W0404', 'W0612', 'E1206', 'W0718', 'C0301', 'C0415']
        print("\n" + "=" * 80)
        print("Focus Issues (W0613, W0404, W0612, E1206, W0718, C0301, C0415):")
        print("=" * 80)

        for code in focus_codes:
            if code in issues_by_code:
                issues = issues_by_code[code]
                print(f"\n{code}: {len(issues)} occurrences")
                for issue in issues[:10]:
                    print(f"  - {issue['file']}:{issue['line']} - {issue['message']}")
                if len(issues) > 10:
                    print(f"  ... and {len(issues) - 10} more")

    except Exception as e:
        print(f"Error running pylint: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(run_pylint())
