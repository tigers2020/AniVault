"""Test file with deliberate errors to verify quality gates work."""

# This file contains deliberate errors to test our quality gates
# It should be fixed by pre-commit hooks


def bad_function(  # Missing type hints
    param1,  # No type hint
    param2,  # No type hint
):
    """Bad docstring without proper format."""
    unused_var = "This variable is never used"  # Unused variable
    result = param1 + param2  # Bad operation without type checking
    return result


class BadClass:  # Missing docstring
    def __init__(self):
        self.value = None

    def method_without_docstring(self):
        return self.value


# Trailing whitespace:
def function_with_trailing_whitespace():
    return "test"


# Missing newline at end of file
