#!/usr/bin/env python3
"""
TMDB API 테스트 스크립트

이 스크립트는 AniVault 프로젝트의 TMDB API 연동을 테스트하기 위한 일회성 스크립트입니다.
실제 TMDB API를 호출하여 검색 기능, 응답 데이터 구조, 그리고 API 속도 제한을 검증합니다.

사용법:
    python scripts/test_tmdb_api.py

필수 환경 변수:
    TMDB_API_KEY: TMDB API 키 (https://www.themoviedb.org/settings/api에서 발급)
"""

import os
import sys
import time
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from tmdbv3api import TMDb, Search
    from tmdbv3api.exceptions import TMDbException
    from rich import print as rich_print
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ 필요한 라이브러리가 설치되지 않았습니다: {e}")
    print("다음 명령으로 의존성을 설치하세요: pip install tmdbv3api rich python-dotenv")
    sys.exit(1)

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 로드
TMDB_API_KEY = os.getenv("TMDB_API_KEY")


def initialize_tmdb() -> Optional[TMDb]:
    """TMDB API 클라이언트를 초기화합니다."""
    if not TMDB_API_KEY:
        rich_print("[red]❌ TMDB_API_KEY 환경 변수가 설정되지 않았습니다.[/red]")
        rich_print("[yellow]다음 단계를 따라 API 키를 설정하세요:[/yellow]")
        rich_print("1. https://www.themoviedb.org/settings/api 에서 API 키 발급")
        rich_print("2. .env 파일에 TMDB_API_KEY='your_api_key' 추가")
        rich_print("3. 또는 환경 변수로 설정: set TMDB_API_KEY=your_api_key")
        return None

    try:
        tmdb = TMDb()
        tmdb.api_key = TMDB_API_KEY
        tmdb.language = "ko"  # 한국어 결과 요청
        rich_print(f"[green]✅ TMDB API 클라이언트 초기화 완료[/green]")
        rich_print(f"[blue]API 키: {TMDB_API_KEY[:8]}...[/blue]")
        rich_print(f"[blue]언어 설정: {tmdb.language}[/blue]")
        return tmdb
    except Exception as e:
        rich_print(f"[red]❌ TMDB API 클라이언트 초기화 실패: {e}[/red]")
        return None


def test_multi_search(tmdb: TMDb) -> bool:
    """다중 검색 API를 테스트합니다."""
    rich_print("\n[bold cyan]🔍 다중 검색(Multi-Search) API 테스트[/bold cyan]")

    try:
        search = Search()
        query = "진격의 거인"

        rich_print(f"[yellow]검색어: '{query}'[/yellow]")
        rich_print("[yellow]API 호출 중...[/yellow]")

        # 다중 검색 실행
        results = search.multi(query)

        if not results:
            rich_print("[red]❌ 검색 결과가 없습니다.[/red]")
            return False

        rich_print(
            f"[green]✅ 검색 완료! {len(results)}개의 결과를 찾았습니다.[/green]"
        )

        # 결과를 테이블로 표시
        table = Table(title="TMDB 검색 결과")
        table.add_column("ID", style="cyan")
        table.add_column("제목", style="magenta")
        table.add_column("타입", style="green")
        table.add_column("개요", style="white", max_width=50)

        for i, result in enumerate(list(results)[:10]):  # 상위 10개만 표시
            title = getattr(result, "title", None) or getattr(result, "name", "N/A")
            media_type = getattr(result, "media_type", "N/A")
            overview = getattr(result, "overview", "N/A")
            if len(overview) > 100:
                overview = overview[:100] + "..."

            table.add_row(
                str(getattr(result, "id", "N/A")), title, media_type, overview
            )

        rich_print(table)
        return True

    except TMDbException as e:
        rich_print(f"[red]❌ TMDB API 오류: {e}[/red]")
        return False
    except Exception as e:
        rich_print(f"[red]❌ 예상치 못한 오류: {e}[/red]")
        return False


def test_rate_limit(tmdb: TMDb) -> bool:
    """API 속도 제한을 테스트합니다."""
    rich_print("\n[bold cyan]⚡ API 속도 제한(Rate Limit) 테스트[/bold cyan]")

    try:
        search = Search()
        test_queries = ["test", "anime", "movie", "tv", "drama"]

        rich_print("[yellow]연속 API 호출을 시작합니다...[/yellow]")
        rich_print(
            "[yellow]속도 제한에 도달하면 HTTP 429 오류가 발생할 것입니다.[/yellow]"
        )

        success_count = 0
        error_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=Console(),
        ) as progress:
            task = progress.add_task("API 호출 중...", total=50)

            for i in range(50):
                try:
                    query = test_queries[i % len(test_queries)]
                    results = search.multi(query)
                    success_count += 1
                    progress.update(
                        task, description=f"성공: {success_count}, 실패: {error_count}"
                    )
                    time.sleep(0.1)  # 100ms 대기

                except TMDbException as e:
                    error_count += 1
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        rich_print(f"\n[green]✅ 속도 제한 감지됨! (HTTP 429)[/green]")
                        rich_print(f"[blue]성공한 요청: {success_count}개[/blue]")
                        rich_print(f"[blue]실패한 요청: {error_count}개[/blue]")
                        rich_print(f"[blue]오류 메시지: {e}[/blue]")
                        return True
                    else:
                        rich_print(f"[yellow]⚠️ 다른 API 오류: {e}[/yellow]")

                except Exception as e:
                    rich_print(f"[red]❌ 예상치 못한 오류: {e}[/red]")
                    return False

                progress.advance(task)

        rich_print(
            f"\n[yellow]⚠️ 50회 요청 완료했지만 속도 제한에 도달하지 않았습니다.[/yellow]"
        )
        rich_print(f"[blue]성공한 요청: {success_count}개[/blue]")
        rich_print(f"[blue]실패한 요청: {error_count}개[/blue]")
        return True

    except Exception as e:
        rich_print(f"[red]❌ 속도 제한 테스트 중 오류: {e}[/red]")
        return False


def main():
    """메인 테스트 함수"""
    console = Console()

    # 시작 메시지
    console.print(
        Panel.fit(
            "[bold blue]TMDB API 테스트 스크립트[/bold blue]\n"
            "AniVault 프로젝트의 TMDB API 연동을 검증합니다.",
            title="🚀 시작",
            border_style="blue",
        )
    )

    # 1. TMDB API 클라이언트 초기화
    rich_print("\n[bold cyan]1️⃣ TMDB API 클라이언트 초기화[/bold cyan]")
    tmdb = initialize_tmdb()
    if not tmdb:
        return False

    # 2. 다중 검색 테스트
    rich_print("\n[bold cyan]2️⃣ 다중 검색 API 테스트[/bold cyan]")
    search_success = test_multi_search(tmdb)

    # 3. 속도 제한 테스트
    rich_print("\n[bold cyan]3️⃣ API 속도 제한 테스트[/bold cyan]")
    rate_limit_success = test_rate_limit(tmdb)

    # 결과 요약
    rich_print("\n[bold cyan]📊 테스트 결과 요약[/bold cyan]")

    results_table = Table(title="테스트 결과")
    results_table.add_column("테스트", style="cyan")
    results_table.add_column("결과", style="white")

    results_table.add_row("TMDB API 초기화", "✅ 성공" if tmdb else "❌ 실패")
    results_table.add_row("다중 검색 API", "✅ 성공" if search_success else "❌ 실패")
    results_table.add_row(
        "속도 제한 테스트", "✅ 성공" if rate_limit_success else "❌ 실패"
    )

    rich_print(results_table)

    # 전체 성공 여부
    all_success = tmdb and search_success and rate_limit_success

    if all_success:
        console.print(
            Panel.fit(
                "[bold green]🎉 모든 테스트가 성공적으로 완료되었습니다![/bold green]\n"
                "TMDB API가 AniVault 프로젝트에서 정상적으로 작동할 준비가 되었습니다.",
                title="✅ 성공",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold red]❌ 일부 테스트가 실패했습니다.[/bold red]\n"
                "위의 오류 메시지를 확인하고 문제를 해결하세요.",
                title="⚠️ 실패",
                border_style="red",
            )
        )

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
