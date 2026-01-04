# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Comprehensive button and keyboard verification
- Thread-safe counter updates for bulk operations
- FloodWaitError and SessionRevokedError handling
- Automatic revoked session cleanup
- Improved error handling and validation
- Complete test coverage for all handlers

### Fixed
- Race conditions in concurrent operations
- Memory leaks in handlers dictionary
- Duplicate error messages
- Missing handlers for poll bulk operations
- Thread safety issues in conversation state management

### Improved
- Error messages consistency
- Code organization and structure
- Documentation and README
- Test coverage and quality

## [1.0.0] - 2025-01-27

### Initial Release
- Account management system
- Message monitoring with keywords
- Bulk operations (reaction, poll, join, block, send PV, comment)
- Individual operations
- Statistics and reporting
- Complete test suite

