#!/bin/bash

# Migration Script: solo-server → solo-cli
# This script helps you migrate from solo-server to solo-cli

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Solo Server → Solo CLI Migration Tool                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if old package is installed
echo -e "${BLUE}[1/4]${NC} Checking for old package installation..."
if pip show solo-server &> /dev/null || uv pip show solo-server &> /dev/null; then
    echo -e "${YELLOW}✓${NC} Found solo-server installation"
    OLD_PACKAGE_FOUND=true
else
    echo -e "${GREEN}✓${NC} No old package found (fresh install)"
    OLD_PACKAGE_FOUND=false
fi

# Check for old configuration
echo ""
echo -e "${BLUE}[2/4]${NC} Checking for existing configuration..."
if [ -d "$HOME/.solo_server" ]; then
    echo -e "${YELLOW}✓${NC} Found configuration at ~/.solo_server"
    CONFIG_FOUND=true
    
    # Show what's in the config
    echo -e "   Contents:"
    if [ -f "$HOME/.solo_server/config.json" ]; then
        echo -e "   ${GREEN}✓${NC} config.json"
    fi
    if [ -f "$HOME/.solo_server/lerobot_config.json" ]; then
        echo -e "   ${GREEN}✓${NC} lerobot_config.json"
    fi
    if [ -d "$HOME/.solo_server/logs" ]; then
        echo -e "   ${GREEN}✓${NC} logs/"
    fi
else
    echo -e "${GREEN}✓${NC} No existing configuration found"
    CONFIG_FOUND=false
fi

# Uninstall old package
if [ "$OLD_PACKAGE_FOUND" = true ]; then
    echo ""
    echo -e "${BLUE}[3/4]${NC} Uninstalling old package (solo-server)..."
    
    # Try uv first, then pip
    if command -v uv &> /dev/null; then
        uv pip uninstall solo-server -y || true
    else
        pip uninstall solo-server -y || true
    fi
    
    echo -e "${GREEN}✓${NC} Old package uninstalled"
else
    echo ""
    echo -e "${BLUE}[3/4]${NC} Skipping uninstall (no old package found)"
fi

# Migrate configuration
if [ "$CONFIG_FOUND" = true ]; then
    echo ""
    echo -e "${BLUE}[4/4]${NC} Migrating configuration..."
    
    # Check if new config directory already exists
    if [ -d "$HOME/.solo" ]; then
        echo -e "${YELLOW}⚠${NC}  New configuration directory (~/.solo) already exists!"
        echo ""
        echo "Options:"
        echo "  1) Backup current ~/.solo and migrate ~/.solo_server"
        echo "  2) Keep current ~/.solo (skip migration)"
        echo "  3) Cancel migration"
        echo ""
        read -p "Choose option (1-3): " choice
        
        case $choice in
            1)
                BACKUP_DIR="$HOME/.solo.backup.$(date +%Y%m%d_%H%M%S)"
                echo -e "   ${BLUE}→${NC} Creating backup at $BACKUP_DIR"
                mv "$HOME/.solo" "$BACKUP_DIR"
                echo -e "   ${BLUE}→${NC} Migrating configuration..."
                mv "$HOME/.solo_server" "$HOME/.solo"
                echo -e "${GREEN}✓${NC} Configuration migrated successfully"
                echo -e "   ${YELLOW}ℹ${NC}  Old config backed up to: $BACKUP_DIR"
                ;;
            2)
                echo -e "${YELLOW}⊘${NC} Skipped configuration migration"
                echo -e "   ${YELLOW}ℹ${NC}  Your old config remains at ~/.solo_server"
                ;;
            3)
                echo -e "${RED}✗${NC} Migration cancelled"
                exit 1
                ;;
            *)
                echo -e "${RED}✗${NC} Invalid option. Migration cancelled."
                exit 1
                ;;
        esac
    else
        echo -e "   ${BLUE}→${NC} Moving ~/.solo_server to ~/.solo"
        mv "$HOME/.solo_server" "$HOME/.solo"
        echo -e "${GREEN}✓${NC} Configuration migrated successfully"
    fi
else
    echo ""
    echo -e "${BLUE}[4/4]${NC} No configuration to migrate"
fi

# Installation instructions
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Migration Complete!                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "1. Install the new package:"
echo "   ${YELLOW}uv pip install solo-cli${NC}"
echo "   or"
echo "   ${YELLOW}pip install solo-cli${NC}"
echo ""
echo "2. Verify installation:"
echo "   ${YELLOW}solo --help${NC}"
echo ""
echo "3. Check your configuration:"
echo "   ${YELLOW}solo status${NC}"
echo ""
echo -e "${BLUE}ℹ${NC}  For more details, see: ${YELLOW}MIGRATION.md${NC}"
echo ""

