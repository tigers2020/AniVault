# Task Completion Workflow

## When a Task is Completed

### 1. Code Quality Checks
```bash
# Run all quality checks
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

### 2. Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### 3. TaskMaster Updates
```bash
# Mark task as complete
task-master set-status --id=<task_id> --status=done

# Update task with progress notes
task-master update-subtask --id=<subtask_id> --prompt="Implementation completed successfully"
```

### 4. Git Commit
```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat: implement bounded queue with thread safety"

# Push to remote
git push origin feature-branch
```

## Quality Gates
- [ ] All tests pass
- [ ] Code follows style guidelines (ruff)
- [ ] Type hints are correct (mypy)
- [ ] Documentation is updated
- [ ] No breaking changes
- [ ] Performance impact considered

## Commit Message Format
Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation update
- `test:` - Test addition/update
- `refactor:` - Code refactoring
- `style:` - Code style fixes
- `chore:` - Build process or dependency updates

## TaskMaster Integration
- Use `task-master next` to find next task
- Use `task-master show <id>` to view task details
- Use `task-master expand <id>` to break down complex tasks
- Use `task-master set-status` to update progress
- Use `task-master update-subtask` to log implementation notes
