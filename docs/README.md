# Parsers Documentation System

This directory contains automatically-maintained API documentation for the `src/parsers/` module.

## Files

- **PARSERS_API.md** - Comprehensive API documentation for all parsers classes and functions
- **README.md** - This file

## Updating Documentation

The parsers documentation is kept up-to-date through two methods:

### Method 1: GitHub Copilot Agent (Recommended)

The easiest way to update documentation is using the Copilot agent:

```
@parsers-doc-agent update the parsers documentation
```

The agent will:
1. Scan all Python files in `src/parsers/` and subdirectories
2. Extract classes, methods, functions, and docstrings
3. Update `PARSERS_API.md` with complete API reference
4. Report summary of changes

### Method 2: Python Script

You can also run the update script directly:

```bash
python scripts/update_parsers_docs.py
```

This script:
- Uses Python's `ast` module to parse all Python files
- Extracts class definitions, method signatures, and docstrings
- Generates comprehensive markdown documentation
- Updates `docs/PARSERS_API.md` automatically

## When to Update

Update the documentation whenever:
- New classes or functions are added to parsers
- Method signatures change
- Docstrings are updated or improved
- Files are renamed or reorganized
- After completing a feature that touches parser code

## Documentation Structure

The generated documentation includes:

1. **Table of Contents** - Easy navigation to any module/class
2. **Module Organization** - Grouped by subdirectory (diann, search, timsmeth, vneometh)
3. **Class Documentation** - All classes with their purpose
4. **Method Documentation** - All public methods with:
   - Full signature with type hints
   - Parameters and return types
   - Brief description from docstring
5. **Function Documentation** - Standalone functions
6. **Summary Statistics** - Count of classes, methods, functions

## Best Practices

1. **Keep docstrings updated** - The documentation is only as good as the docstrings in the code
2. **Use type hints** - They appear in the generated documentation
3. **Update regularly** - Run the updater after significant changes
4. **Review generated docs** - Check that everything looks correct after updates
5. **Link to docs** - Reference the API docs in other documentation

## Agent Configuration

The documentation agent is defined at:
```
.vscode/agents/parsers-doc-agent.md
```

It contains detailed instructions for:
- When to invoke the agent
- How to scan files
- Documentation formatting rules
- Verification steps

## Future Enhancements

Potential improvements to the documentation system:

- [ ] Add usage examples for each class
- [ ] Generate class diagrams
- [ ] Include parameter descriptions from docstrings
- [ ] Add cross-references between related classes
- [ ] Generate HTML version for web viewing
- [ ] Auto-generate on git commit (pre-commit hook)
- [ ] Include code coverage metrics

## Troubleshooting

**Problem:** Documentation is missing classes/methods  
**Solution:** Check that:
- The file is in `src/parsers/` or a subdirectory
- Methods are public (don't start with `_` unless `__special__`)
- File is valid Python (no syntax errors)

**Problem:** Docstrings not appearing  
**Solution:** Ensure docstrings are:
- Properly formatted (triple quotes)
- Placed immediately after class/function definition
- Not empty

**Problem:** Script fails to run  
**Solution:** 
- Verify Python 3.7+ is installed
- Check that `src/parsers/` directory exists
- Run from project root directory

## Contributing

When adding new parser functionality:

1. Write clear docstrings for all public classes and methods
2. Include type hints in function signatures
3. Update the API documentation after changes
4. Verify the generated documentation looks correct

## Questions?

For questions about the documentation system, see:
- Agent definition: `.vscode/agents/parsers-doc-agent.md`
- Update script: `scripts/update_parsers_docs.py`
- Generated docs: `docs/PARSERS_API.md`

---

**Last Updated:** 2026-07-02
