#!/bin/bash
# Install mutl3y-review-workflow into prism repo

set -e

PRISM_ROOT="/raid5/source/test/prism"
PLUGIN_SOURCE="/raid5/source/test/mutl3y_review_workflow_development"

echo "Installing mutl3y-review-workflow..."

# Remove old plugin directory structure if present
if [ -d "$PRISM_ROOT/.github/plugin" ]; then
    echo "Removing old plugin directory structure..."
    rm -rf "$PRISM_ROOT/.github/plugin"
fi

# Create .github directories if they don't exist
mkdir -p "$PRISM_ROOT/.github/agents"
mkdir -p "$PRISM_ROOT/.github/skills"

# Copy agents and skills directly to .github
echo "Copying agents..."
cp -r "$PLUGIN_SOURCE/agents/"*.agent.md "$PRISM_ROOT/.github/agents/"

echo "Copying skills..."
cp -r "$PLUGIN_SOURCE/skills/"* "$PRISM_ROOT/.github/skills/"

echo ""
echo "✅ Mutl3y workflow installed successfully!"
echo ""
echo "Installed agents:"
ls "$PRISM_ROOT/.github/agents/"
echo ""
echo "Installed skills:"
ls "$PRISM_ROOT/.github/skills/"
echo ""
echo "📚 Quick Start: See MUTL3Y_QUICKSTART.md"
echo ""
echo "To use in VS Code Copilot Chat:"
echo "  1. Reload VS Code window (Cmd/Ctrl+Shift+P > 'Reload Window')"
echo "  2. Configure: @workspace use the mutl3y-setup skill"
echo "  3. Review code: @workspace use the mutl3y-foreman skill to review <path>"
echo ""
echo "⚠️  Important: Skills are invoked with '@workspace use the <skill-name> skill'"
echo "    NOT with slash commands like /mutl3y-config"
echo ""
echo "💡 Full documentation: $PRISM_ROOT/MUTL3Y_QUICKSTART.md"
echo ""
