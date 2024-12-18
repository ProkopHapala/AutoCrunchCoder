# C++ Analyzer Test Plan

## Overview
This document outlines the test-driven development plan for implementing remaining features in the C++ analyzer.

## Test Development Guidelines

### Critical Development Rules

1. **One Test at a Time**
   - ALWAYS focus on fixing one failing test at a time
   - Do not move on to other tests until the current test is passing
   - If multiple tests are failing, pick the simplest one first

2. **Code Preservation**
   - When possible, void modify working code that has already passed tests
   - When modifying functionality, prefer to create new versions of functions with different names
   - Only replace old functions with new versions after thorough testing and after the test passed

3. **Incremental Changes**
   - Make small, focused changes
   - Test after each change
   - If a change causes other tests to fail, immediately revert it

4. **Version Control**
   - Create checkpoints of working code
   - Roll back to last working version if multiple tests start failing
   - Document which tests were passing at each checkpoint

## Testing Strategy
1. Each issue will be addressed individually with dedicated test cases
2. High verbosity logging will be enabled only for failing tests
3. Debug prints will be strategically placed to understand failures
4. Tests will be implemented in order of dependency (simpler features first)

### Focused Test-Driven Development

1. **Focus on One Test at a Time**
   - Run only the specific test you're working on using the following format:
   ```bash
   python3 -m pytest tests/test_cpp_type_analyzer.py::TestTypeCollector::<test_name> -v
   ```
   - Example for location tracking:
   ```bash
   python3 -m pytest tests/test_cpp_type_analyzer.py::TestTypeCollector::test_location_tracking -v
   ```

2. **Development Cycle**
   - Choose one failing test to focus on
   - Run only that specific test
   - Make minimal changes needed to fix the test
   - Verify the test passes
   - Commit the changes after the failing test is corrected and passes
   - Only then move on to the next failing test

3. **Benefits of This Approach**
   - Reduces confusion by focusing on one issue at a time
   - Prevents unintended side effects
   - Makes debugging easier
   - Ensures clear understanding of each test's requirements
   - reduces runtime and lenght of the debugging output (log) which can be otherwise overwhelming and hard to read
   - Maintains code quality through incremental improvements

### Test Categories

## Current Test Status (6/10 Passing)

### Passing Tests
1. Base Class Processing
   - Simple single inheritance
   - Multiple inheritance
   - Access specifier handling
   - Base class name resolution

2. Basic Types
   - Built-in type registration
   - User-defined types
   - Type qualifiers

3. Class in Namespace
   - Namespace scoping
   - Class definition in namespace
   - Nested namespaces

4. Class Processing
   - Class definition
   - Method declarations
   - Virtual methods
   - Override specifiers

5. Namespace Processing
   - Namespace declaration
   - Namespace contents
   - Using declarations

6. Scope Names
   - Scope stack management
   - Qualified names
   - Name resolution

### Failing Tests
1. Cross-File Dependencies
   - Issue: Header paths not absolute
   - Priority: Medium
   - Next Steps:
     - Store absolute paths
     - Implement header resolution
     - Track file dependencies

2. Function Calls
   - Issue: Call tracking not implemented
   - Priority: High
   - Next Steps:
     - Add call tracking to methods
     - Handle constructor calls
     - Support virtual dispatch

3. Location Tracking
   - Issue: Missing location info
   - Priority: Medium
   - Next Steps:
     - Add location to all nodes
     - Fix point adjustment
     - Standardize location format

4. Method Resolution
   - Issue: Class attribute access
   - Priority: High
   - Next Steps:
     - Fix class info storage
     - Implement method lookup
     - Handle inheritance

## Implementation Plan

### Phase 1: Function Call Tracking (Current Priority)
1. Write test cases
   - Basic function calls
   - Method calls on objects
   - Constructor calls
   - Virtual function calls
   
2. Implementation Steps
   - Add FunctionCall class with location and scope
   - Track calls in function bodies
   - Implement method resolution
   - Handle virtual dispatch

3. Debug Strategy
   - Log function declarations
   - Track method calls
   - Verify virtual table
   - Check call resolution

### Phase 2: Location Tracking
1. Test Cases
   - Node locations
   - Source ranges
   - Point adjustments
   
2. Implementation Steps
   - Add location to all nodes
   - Standardize location format
   - Fix point adjustment
   - Add range validation

3. Debug Strategy
   - Log node locations
   - Verify source ranges
   - Check adjustments
   - Validate positions

### Phase 3: Cross-File Dependencies
1. Test Cases
   - Include resolution
   - Header dependencies
   - Path handling
   
2. Implementation Steps
   - Store absolute paths
   - Track file dependencies
   - Handle include paths
   - Resolve headers

3. Debug Strategy
   - Log file paths
   - Track includes
   - Verify resolution
   - Check dependencies

## Debug Strategy
- Verbosity Levels:
  - 0: Errors only
  - 1: Basic progress
  - 2: Detailed state

- Debug Points:
  - Function entry/exit
  - Node processing
  - Type registration
  - Call resolution
  - Location updates

- Error Handling:
  - Clear error messages
  - State dumps on failure
  - Stack traces
  - Context information

## Success Criteria
1. Test Coverage
   - All 10 tests passing
   - No regressions
   - Clear failure messages

2. Code Quality
   - Clean architecture
   - Clear documentation
   - Efficient processing
   - Memory safety

3. Feature Completeness
   - Function call tracking
   - Location information
   - Cross-file dependencies
   - Method resolution

## Next Steps
1. Implement function call tracking
   - Start with basic calls
   - Add virtual dispatch
   - Handle constructors

2. Fix location tracking
   - Add to all nodes
   - Standardize format
   - Fix adjustments

3. Add cross-file support
   - Handle paths
   - Track dependencies
   - Resolve headers
