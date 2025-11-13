# Migration Guide: solo-server → solo-cli

## 📢 Important Notice

The package has been renamed from **`solo-server`** to **`solo-cli`** to better reflect its purpose as a interactive CLI tool for Physical AI.

### What Changed?

- **PyPI Package Name**: `solo-server` → `solo-cli`
- **Package Directory Name**: `solo_server` → `solo`
- **Configuration Directory**: `~/.solo_server` → `~/.solo`
- **Repository URL**: `GetSoloTech/solo-server` → `GetSoloTech/solo-cli`

### What Stayed the Same?

- **CLI Command**: Still use `solo` command (no change)
- **All Commands**: `solo setup`, `solo serve`, `solo robo`, etc. work exactly the same
- **Functionality**: All features remain identical

---

## 🔄 Migration Steps

### Quick Migration (Automated)

We provide an automated migration script to make the process easier:

```bash
# Clone the new repository
git clone https://github.com/GetSoloTech/solo-cli.git
cd solo-cli

# Run the migration script
./migrate.sh
```

The script will:
- ✅ Detect old `solo-server` installation
- ✅ Find and backup existing configuration
- ✅ Uninstall the old package
- ✅ Migrate `~/.solo_server` to `~/.solo`
- ✅ Provide next steps for installing the new package

### Manual Migration

If you prefer to migrate manually, follow these steps:

### Step 1: Uninstall Old Package

```bash
# If installed via uv/pip
uv pip uninstall solo-server
# or
pip uninstall solo-server
```

### Step 2: Install New Package

```bash
# From PyPI
uv pip install solo-cli

# Or from source
git clone https://github.com/GetSoloTech/solo-cli.git
cd solo-cli
uv pip install -e .
```

### Step 3: Migrate Configuration (Optional)

If you have existing configuration, you can migrate it:

```bash
# Option 1: Rename the directory (keeps all existing settings)
mv ~/.solo_server ~/.solo

# Option 2: Copy configuration file only
mkdir -p ~/.solo
cp ~/.solo_server/config.json ~/.solo/config.json

# Option 3: Start fresh with new configuration
solo setup
```

### Step 4: Verify Installation

```bash
# Check the CLI works
solo --help

# Check your configuration
solo status
```

---

## 🗂️ Configuration Migration Details

### Configuration File Location

**Old Location:**
```
~/.solo_server/config.json
~/.solo_server/logs/
```

**New Location:**
```
~/.solo/config.json
~/.solo/logs/
```

### Configuration File Format

The `config.json` format remains **exactly the same**. No changes needed to the content.

---

## 🐛 Troubleshooting


### Issue: Configuration not found

**Solution:**
```bash
# Check if old config exists
ls -la ~/.solo_server/

# Migrate to new location
mv ~/.solo_server ~/.solo

# Or run setup again
solo setup
```

### Issue: Import errors in custom scripts

If you have custom Python scripts that import the package:

**Old:**
```python
from solo_server.config import CONFIG_PATH
from solo_server.utils.hardware import hardware_info
```

**New:**
```python
from solo.config import CONFIG_PATH
from solo.utils.hardware import hardware_info
```

---

## 📦 Docker Users

If you're using Docker with solo-cli:

### Volume Mounts

**Old:**
```bash
-v ~/.solo_server:/root/.solo_server
```

**New:**
```bash
-v ~/.solo:/root/.solo
```

### Update Your Docker Commands

The new package automatically uses the correct paths. If you have custom Docker scripts, update volume mount paths from `.solo_server` to `.solo`.

---

## 🔗 Quick Reference

| Item | Old | New |
|------|-----|-----|
| PyPI Package | `solo-server` | `solo-cli` |
| Package Directory | `solo_server` | `solo` |
| Config Directory | `~/.solo_server` | `~/.solo` |
| CLI Command | `solo` | `solo` ✅ (unchanged) |
| GitHub Repo | `GetSoloTech/solo-server` | `GetSoloTech/solo-cli` |

---

## 💡 Need Help?

- **Documentation**: [docs.getsolo.tech](https://docs.getsolo.tech)
- **Issues**: [GitHub Issues](https://github.com/GetSoloTech/solo-cli/issues)
- **Website**: [getsolo.tech](https://getsolo.tech)

---

## ⏱️ Timeline

- **Old Package (`solo-server`)**: Deprecated, no longer maintained
- **New Package (`solo-cli`)**: Current, actively maintained
- **Recommended Action**: Migrate at your earliest convenience

The migration is straightforward and should take less than 5 minutes!

