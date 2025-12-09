# Workflow State - Telegram Management Bot Panel

## Current Phase

**Status**: `Idle` | `Analyze` | `Blueprint` | `Construct` | `Validate` | `Complete`

**Last Updated**: 2025-01-11

**Active Agent**: N/A

## Workflow Rules

### Rule 1: Always Validate Before Merge

**When**: Code is generated or modified

**Action**:
1. Run validation: `pytest tests/` or `python -m pytest tests/`
2. Check linter errors: Review `read_lints` output
3. If tests fail:
   - Fix errors and retry
   - Iterate until all tests pass
   - Log fixes in action log
4. If tests pass:
   - Auto-merge to main branch (if in feature branch)
   - Update workflow state
   - Mark task as complete

**Validation Checklist**:
- [ ] All unit tests pass
- [ ] All flow tests pass
- [ ] All integration tests pass
- [ ] No linter errors
- [ ] No critical security issues
- [ ] Error handling is properly implemented
- [ ] Logging is appropriate

### Rule 2: Automatic Test Execution

**When**: Any code change is made

**Commands**:
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_unit_*.py          # Unit tests
pytest tests/test_flows_*.py          # Flow tests
pytest tests/test_integration_*.py    # Integration tests
```

**Exit Codes**:
- `0` = All tests passed → Proceed to merge
- `!= 0` = Tests failed → Fix errors and retry

### Rule 3: Error Handling Validation

**When**: Code contains try-except blocks or async operations

**Check**:
- [ ] All async operations wrapped in try-except
- [ ] `FloodWaitError` is handled with retry logic
- [ ] User notifications sent on errors
- [ ] Resources cleaned up in finally blocks
- [ ] Logging includes `exc_info=True` for exceptions
- [ ] Conversation state cleaned up on errors

### Rule 4: Security Validation

**When**: Code touches files, config, or user input

**Check**:
- [ ] No sensitive data in logs (passwords, API keys, full phone numbers)
- [ ] File paths are sanitized
- [ ] User input is validated using `InputValidator`
- [ ] `ADMIN_ID` is verified before sensitive operations
- [ ] No `.env` or `.session` files in commits
- [ ] Configuration data is validated before saving

### Rule 5: Code Quality Standards

**When**: Code is written or modified

**Check**:
- [ ] Follows PEP 8 style guide
- [ ] Uses type hints where helpful
- [ ] Functions have docstrings
- [ ] Uses async/await for I/O operations
- [ ] Uses locks for thread-safe operations
- [ ] Follows rate limiting patterns
- [ ] Uses semaphores for concurrent operations

### Rule 6: Multi-Agent Coordination

**When**: Multiple agents are working on different tasks

**Coordination**:
1. Each agent works in separate git worktree (if using worktrees)
2. Agents communicate via `workflow_state.md` updates
3. Before merging, agents check for conflicts
4. Merge order: Tests → Validation → Security → Merge
5. Update `action_log` with agent ID and task

**Worktree Setup** (if applicable):
```bash
git worktree add ../Telegram-Panel-agent1 main
git worktree add ../Telegram-Panel-agent2 main
# ... up to 8 agents
```

### Rule 7: Autonomous Loop

**When**: Operating in autonomous mode

**Loop Pattern**:
1. **Read State**: Load `project_config.md` and `workflow_state.md`
2. **Interpret Rules**: Apply rules from workflow_state.md
3. **Act**: Execute task (edit/code/test)
4. **Validate**: Run tests and checks
5. **Update State**: Log actions and update workflow_state.md
6. **Repeat**: Continue until task complete or error requires intervention

**Action Types**:
- `edit_file` - Modify existing code
- `write_file` - Create new files
- `run_terminal_cmd` - Execute tests or commands
- `read_file` - Review code
- `grep` - Search codebase
- `codebase_search` - Semantic search

### Rule 8: Automatic Merge Decision

**When**: Validation passes and code is ready

**Merge Criteria** (ALL must pass):
- ✅ All tests pass (`pytest tests/` returns 0)
- ✅ No linter errors
- ✅ Security checks pass
- ✅ Code quality standards met
- ✅ Documentation updated (if needed)

**Merge Process**:
1. If in feature branch: Merge to main
2. Update `workflow_state.md` with completion status
3. Log merge in `action_log`
4. Update `current_phase` to `Complete`

**Skip Merge If**:
- Tests fail
- Security issues detected
- Code quality issues
- User intervention required

## Task Plan

### Current Tasks

**Queue**: `[]` (empty)

**In Progress**: `None`

**Completed**: `[]`

### Task Template

```markdown
### Task ID: [unique-id]
- **Type**: Feature | Bug Fix | Refactor | Test | Documentation
- **Scope**: [file/directory/module]
- **Status**: Pending | In Progress | Validating | Complete | Failed
- **Agent**: [agent-id or N/A]
- **Priority**: High | Medium | Low
- **Description**: [task description]
- **Files Affected**: [list of files]
- **Validation**: [test commands]
- **Dependencies**: [other tasks]
```

## Action Log

### Format

```
[YYYY-MM-DD HH:MM:SS] [AGENT-ID] [ACTION] [RESULT]
```

### Recent Actions

_No actions logged yet_

### Example Entry

```
[2025-01-11 02:50:00] agent-1 [EDIT] Modified src/Handlers.py - Added error handling
[2025-01-11 02:50:30] agent-1 [TEST] Ran pytest tests/ - All tests passed
[2025-01-11 02:50:45] agent-1 [MERGE] Merged feature branch to main - Success
```

## State Management

### Phase Transitions

- `Idle` → `Analyze`: Task received, starting analysis
- `Analyze` → `Blueprint`: Analysis complete, creating plan
- `Blueprint` → `Construct`: Plan approved, starting implementation
- `Construct` → `Validate`: Implementation complete, running validation
- `Validate` → `Complete`: Validation passed, task complete
- `Validate` → `Construct`: Validation failed, fixing issues
- `Complete` → `Idle`: Task complete, ready for next task

### State Persistence

- Update this file after each significant action
- Commit state changes with code changes
- Use git to track state history
- Keep action log limited to last 50 entries

## Error Recovery

### When Tests Fail

1. Read error output from test run
2. Identify failing test(s)
3. Fix code issues
4. Re-run tests
5. If still failing, log error and request intervention
6. Update task status to `Failed` if unable to fix

### When Validation Fails

1. Check specific validation rule that failed
2. Fix issue
3. Re-run validation
4. If critical issue, mark task as `Failed` and log

### When Merge Conflicts

1. Resolve conflicts manually or abort
2. Update state with conflict details
3. Request user intervention if needed

## Autonomous Mode Instructions

**To activate autonomous mode**:

1. Start chat with: "Operate using project_config.md and workflow_state.md in autonomous mode. Follow the loop: Read state > Interpret rules > Act (edit/code/test) > Update state > Repeat until done."

2. AI will:
   - Read `project_config.md` for standards
   - Read `workflow_state.md` for current state and rules
   - Execute tasks following workflow rules
   - Validate before merge
   - Update state after each action
   - Continue until task complete

3. For multi-agent:
   - Assign different tasks to different agents
   - Each agent updates workflow_state.md
   - Coordinator merges results
   - Validate combined results before merge

## Notes

- Keep this file updated with current state
- Log all significant actions
- Update phase when transitioning
- Clear completed tasks periodically
- Use this file to coordinate multi-agent work

