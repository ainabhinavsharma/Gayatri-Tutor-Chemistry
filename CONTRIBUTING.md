# Contributing to Gayatri Tutor V3

First off, thank you for considering contributing to Gayatri Tutor V3! It's people like you that make this tool great.

## How Can I Contribute?

We have recently published a [Comprehensive Audit Document](gayatri_tutor_v3_comprehensive_audit_and_fix.md) that lists numerous identified issues across our codebase. 
These issues cover everything from critical bugs (P0) to minor improvements and edge cases (P3).

All of these issues have been marked with **[HELP WANTED]**. 

### Steps to Contribute:

1. **Pick an Issue**: Browse the `gayatri_tutor_v3_comprehensive_audit_and_fix.md` file and find an issue that interests you. 
2. **Fork the Repository**: Create a fork of this repository to your own GitHub account.
3. **Create a Branch**: Create a new branch for your fix (e.g., `git checkout -b fix/issue-12-tool-registry`).
4. **Make your changes**: Implement the fix! Make sure to also add regression tests if applicable.
5. **Test your changes**: Run the app locally and verify the bug is resolved.
6. **Submit a Pull Request**: Push your branch to your fork and submit a Pull Request to our `main` branch. 
   - In your PR description, please mention the Issue number or title from the audit document that you are fixing.

### Development Setup

Please read `development.md` for instructions on how to set up the project locally.

### Writing Tools

Tools that can run for a long time (e.g. network requests, heavy computation, data processing loops) must support **cooperative cancellation**. 
Python threads cannot be forcefully killed. If your tool ignores a timeout, the thread will continue running in the background indefinitely.

1. Decorate your tool with `@cooperative_tool` from `core.agents.policy`.
2. Within loops or long-running sections, periodically call `check_cancelled()`.

Example:
```python
from core.agents.policy import cooperative_tool, check_cancelled

@tool_registry.register("long_running_task", timeout_s=10.0)
@cooperative_tool
def my_task():
    for item in items:
        check_cancelled()  # Raises CancelledError if timeout was reached
        process(item)
```

Tools that are purely synchronous and very fast (e.g., simple file reads, math ops) do not need `@cooperative_tool`.

We look forward to reviewing your Pull Requests!
