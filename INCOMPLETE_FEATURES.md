# Incomplete Features and Known Issues

This document lists features that are incomplete, need improvement, or have known issues in the Telegram Panel project.

## Status Legend

- **Incomplete**: Feature is partially implemented or not working
- **Needs Improvement**: Feature works but could be enhanced
- **Known Issue**: Bug or limitation that needs to be addressed
- **Planned**: Feature is planned but not yet implemented

## Incomplete Features

### 1. Bulk Leave Operation
**Status**: ✅ **COMPLETED** (2025-01-27)  
**Location**: `src/actions.py`

- ✅ Individual leave operation exists (`left` method)
- ✅ Bulk leave operation now fully implemented
- ✅ Users can leave groups/channels with multiple accounts simultaneously
- ✅ Proper error handling and session revocation detection added

**Impact**: Medium  
**Priority**: Low (Resolved)

---

### 2. Error Recovery and Retry Logic
**Status**: Needs Improvement  
**Location**: Multiple files

- Some operations have basic error handling
- Retry logic for failed operations is inconsistent
- No automatic recovery from temporary network issues

**Impact**: Medium  
**Priority**: Medium

---

### 3. Rate Limiting Intelligence
**Status**: Needs Improvement  
**Location**: `src/actions.py`

- Basic rate limiting exists with semaphores
- No dynamic adjustment based on Telegram's rate limit responses
- Fixed delays may not be optimal for all operations

**Impact**: Low  
**Priority**: Low

---

### 4. Session Management
**Status**: Needs Improvement  
**Location**: `src/Client.py`

- Basic session detection and loading works
- Session expiration handling could be improved
- No automatic session refresh mechanism

**Impact**: Medium  
**Priority**: Medium

---

### 5. Monitoring Performance
**Status**: Needs Improvement  
**Location**: `src/Monitor.py`

- Message monitoring works but may be slow with many keywords
- No optimization for large keyword lists
- Could benefit from regex pattern matching

**Impact**: Low  
**Priority**: Low

---

## Known Issues

### 1. Persian/Farsi Language Support
**Status**: Known Issue  
**Location**: Multiple files

- Some user-facing messages are in Persian/Farsi
- Inconsistent language usage throughout the codebase
- Error messages may appear in mixed languages

**Impact**: Low  
**Priority**: Low

---

### 2. Concurrent Operation Limits
**Status**: Known Issue  
**Location**: `src/actions.py`

- `MAX_CONCURRENT_OPERATIONS` is hardcoded to 3
- No configuration option to adjust this value
- May not be optimal for all use cases

**Impact**: Low  
**Priority**: Low

---

### 3. Group Update Performance
**Status**: Known Issue  
**Location**: `src/Client.py`

- Updating groups for all accounts can be slow
- No progress indication during group updates
- May timeout with many accounts

**Impact**: Medium  
**Priority**: Medium

---

### 4. Input Validation Edge Cases
**Status**: Known Issue  
**Location**: `src/Validation.py`

- Most validation works correctly
- Some edge cases may not be handled (e.g., very long usernames)
- Unicode handling could be improved

**Impact**: Low  
**Priority**: Low

---

### 5. Logging Verbosity
**Status**: Known Issue  
**Location**: `src/Logger.py`

- Logging levels are not configurable
- Some operations may log too much or too little
- No log rotation mechanism

**Impact**: Low  
**Priority**: Low

---

## Planned Features

### 1. Web Dashboard
**Status**: Planned  
**Description**: Web-based interface for managing the bot and viewing statistics

**Priority**: Low

---

### 2. Database Backend
**Status**: Planned  
**Description**: Replace JSON file storage with a proper database (SQLite/PostgreSQL)

**Priority**: Medium

---

### 3. Scheduled Operations
**Status**: Planned  
**Description**: Schedule bulk operations to run at specific times

**Priority**: Low

---

### 4. Advanced Statistics
**Status**: Planned  
**Description**: More detailed statistics and analytics for operations

**Priority**: Low

---

### 5. Multi-Admin Support
**Status**: Planned  
**Description**: Support for multiple admin users with different permission levels

**Priority**: Low

---

## Testing Coverage

### Current Status
- Unit tests: Good coverage for core components
- Integration tests: Basic coverage exists
- Flow tests: Most user flows are tested

### Missing Tests
- Error recovery scenarios
- Edge cases in bulk operations
- Performance tests for large-scale operations
- Network failure scenarios

---

## Documentation

### Current Status
- README: Complete
- Code comments: Good coverage
- API documentation: Basic

### Missing Documentation
- Architecture diagrams
- Deployment guide
- Performance tuning guide
- Troubleshooting guide expansion

---

## Notes

This project is under active development. Features and issues listed here may change as development progresses. If you encounter issues not listed here, please open an issue on GitHub.

For contributing guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

