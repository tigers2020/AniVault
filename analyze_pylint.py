"""Analyze pylint results and show top issues."""
import json
import sys
from collections import defaultdict
from pathlib import Path

def analyze_pylint_results(json_file: str) -> None:
    """Analyze pylint JSON output and print statistics."""
    issues_by_code = defaultdict(list)
    
    # Try different encodings
    for encoding in ('utf-8', 'utf-8-sig', 'latin-1'):
        try:
            with Path(json_file).open(encoding=encoding) as f:
                break
        except UnicodeDecodeError:
            continue
    else:
        # Fallback to binary with errors='ignore'
        with Path(json_file).open('rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            f = content.splitlines()
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                issue = json.loads(line)
                if issue.get('type') in ('warning', 'error'):
                    msg_id = issue.get('message-id', 'UNKNOWN')
                    issues_by_code[msg_id].append({
                        'file': issue.get('path', ''),
                        'line': issue.get('line', 0),
                        'message': issue.get('message', '')[:80]
                    })
            except json.JSONDecodeError:
                continue
    
    print(f"Total issues found: {sum(len(v) for v in issues_by_code.values())}\n")
    print("Top issues by count:")
    print("=" * 80)
    
    for code, issues in sorted(issues_by_code.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        print(f"\n{code}: {len(issues)} occurrences")
        for issue in issues[:5]:
            rel_path = issue['file'].replace('\\', '/')
            if 'src/anivault/' in rel_path:
                rel_path = rel_path.split('src/anivault/')[-1]
            print(f"  - {rel_path}:{issue['line']} - {issue['message']}")
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more")

if __name__ == '__main__':
    analyze_pylint_results('pylint_results.json')

