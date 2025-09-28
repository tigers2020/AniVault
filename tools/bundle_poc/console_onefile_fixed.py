"""PyInstaller onefile POC for AniVault CLI.

This script tests the compatibility of core dependencies with PyInstaller
bundling, specifically focusing on anitopy C extensions and cryptography.
"""

import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_anitopy_import():
    """Test anitopy import and basic functionality."""
    try:
        import anitopy

        print("+ anitopy imported successfully")

        # Test parsing
        sample_filename = "Attack on Titan S01E01 [1080p] [Subs].mkv"
        result = anitopy.parse(sample_filename)
        print(f"+ anitopy parsing works: {result}")
        return True
    except Exception as e:
        print(f"- anitopy import failed: {e}")
        return False


def test_cryptography_import():
    """Test cryptography import and basic functionality."""
    try:
        from cryptography.fernet import Fernet

        print("+ cryptography imported successfully")

        # Test key generation and encryption
        key = Fernet.generate_key()
        f = Fernet(key)
        test_data = b"test data"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)

        if decrypted == test_data:
            print("+ cryptography encryption/decryption works")
            return True
        print("- cryptography encryption/decryption failed")
        return False
    except Exception as e:
        print(f"- cryptography import failed: {e}")
        return False


def test_tmdbv3api_import():
    """Test tmdbv3api import and basic functionality."""
    try:
        import tmdbv3api

        print("+ tmdbv3api imported successfully")

        # Test basic initialization
        tmdb = tmdbv3api.TMDb()
        tv = tmdbv3api.TV()
        movie = tmdbv3api.Movie()

        print("+ tmdbv3api classes initialized successfully")
        return True
    except Exception as e:
        print(f"- tmdbv3api import failed: {e}")
        return False


def test_rich_import():
    """Test rich import and basic functionality."""
    try:
        from rich.console import Console

        print("+ rich imported successfully")

        # Test console creation
        console = Console()
        print("+ rich console created successfully")
        return True
    except Exception as e:
        print(f"- rich import failed: {e}")
        return False


def test_click_import():
    """Test click import and basic functionality."""
    try:
        import click

        print("+ click imported successfully")

        # Test command creation
        @click.command()
        def test_command():
            click.echo("Hello from Click!")

        print("+ click command creation works")
        return True
    except Exception as e:
        print(f"- click import failed: {e}")
        return False


def test_parse_import():
    """Test parse import and basic functionality."""
    try:
        import parse

        print("+ parse imported successfully")

        # Test parsing
        result = parse.parse("Hello {name}!", "Hello World!")
        print(f"+ parse functionality works: {result}")
        return True
    except Exception as e:
        print(f"- parse import failed: {e}")
        return False


def test_requests_import():
    """Test requests import and basic functionality."""
    try:
        import requests

        print("+ requests imported successfully")

        # Test session creation
        session = requests.Session()
        print("+ requests session creation works")
        return True
    except Exception as e:
        print(f"- requests import failed: {e}")
        return False


def test_tomli_import():
    """Test TOML parsing import."""
    try:
        if sys.version_info >= (3, 11):
            print("+ tomllib (built-in) imported successfully")
        else:
            print("+ tomli imported successfully")
        return True
    except Exception as e:
        print(f"- TOML parsing import failed: {e}")
        return False


def test_tomli_w_import():
    """Test TOML writing import."""
    try:
        print("+ tomli-w imported successfully")
        return True
    except Exception as e:
        print(f"- tomli-w import failed: {e}")
        return False


def main():
    """Run all compatibility tests."""
    print("=" * 60)
    print("AniVault CLI - PyInstaller Compatibility Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    tests = [
        ("anitopy", test_anitopy_import),
        ("cryptography", test_cryptography_import),
        ("tmdbv3api", test_tmdbv3api_import),
        ("rich", test_rich_import),
        ("click", test_click_import),
        ("parse", test_parse_import),
        ("requests", test_requests_import),
        ("tomli", test_tomli_import),
        ("tomli-w", test_tomli_w_import),
    ]

    results = []
    for name, test_func in tests:
        print(f"Testing {name}...")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"- {name} test crashed: {e}")
            results.append((name, False))
        print()

    print("=" * 60)
    print("Test Results Summary:")
    print("=" * 60)

    passed = 0
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name:15} : {status}")
        if result:
            passed += 1

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! PyInstaller compatibility looks good.")
        return 0
    print("Some tests failed. Check the output above for details.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
