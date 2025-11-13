# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2024-11-12

### 🎉 MAJOR: Package Renamed from solo-server to solo-cli

This version marks the official rename of the package from `solo-server` to `solo-cli`.

### Changed

#### Package & Repository
- **BREAKING**: Package name changed from `solo-server` to `solo-cli` on PyPI
- **BREAKING**: Python package renamed from `solo_server` to `solo`
- **BREAKING**: Repository moved from `GetSoloTech/solo-server` to `GetSoloTech/solo-cli`
- **BREAKING**: Configuration directory changed from `~/.solo_server` to `~/.solo`

#### Performance Improvements
- Implemented lazy-loading for CLI commands to improve startup time
- Reduced initial import overhead by deferring heavy imports until command execution

### Added
- `MIGRATION.md` - Comprehensive migration guide for upgrading from solo-server
- `migrate.sh` - Automated migration script to help users transition smoothly
- Migration notice in README.md to alert users of the package rename
- Deprecation notice in package description

### Fixed
- N/A (This release focuses on the package rename)

See [MIGRATION.md](MIGRATION.md) for detailed instructions.

### Important Notes

- ✅ The CLI command name remains `solo` (unchanged)
- ✅ All commands work exactly the same way
- ✅ Configuration file format is identical
- ✅ All functionality preserved
- ⚠️ You must manually migrate or recreate your configuration
- ⚠️ Update any custom scripts that import `solo_server` to import `solo`

---

## Future Versions

Stay tuned for more updates! We're continuously improving Solo CLI to make Physical AI deployment easier and more efficient.

For the latest changes, see the [GitHub Releases](https://github.com/GetSoloTech/solo-cli/releases) page.

