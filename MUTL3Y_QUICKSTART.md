# Mutl3y Review Workflow - Quick Start

The Mutl3y review workflow is now installed in this repository!

## ✅ Installed Components

**Agents** (`.github/agents/`):
- mutl3y-scout
- mutl3y-probe
- mutl3y-builder
- mutl3y-gatekeeper
- mutl3y-archivist
- mutl3y-teams-foreman
- mutl3y-workflow-monitor
- gem-reviewer, gem-researcher, gilfoyle (external)

**Skills** (`.github/skills/`):
- mutl3y-setup
- mutl3y-foreman
- mutl3y-cluster-foreman

## 🚀 How to Use

### Initial Setup

In Copilot Chat:
```
@workspace use the mutl3y-setup skill to configure this workspace
```

This will guide you through:
- Setting paths for plans, artifacts, and logs
- Selecting external reviewer agents
- Configuring workflow preferences

### Start a Review Cycle

For simple reviews (single-agent):
```
@workspace use the mutl3y-foreman skill to review src/prism/scanner_core/ with medium depth
```

For complex reviews (cluster architecture):
```
@workspace use the mutl3y-cluster-foreman skill to review src/prism/ with thorough depth
```

### Check Status

```
@workspace use the mutl3y-setup skill to show current configuration
```

### Reconfigure

```
@workspace use the mutl3y-setup skill to reconfigure paths
```

## 📝 Available Workflow Modes

- **Balanced**: 10-20% cheaper, tiered validation
- **Cost-Optimized**: 30-40% cheaper, manual escalation
- **Maximum Validation**: 50-80% more expensive, always full validation

Configure mode during setup or reconfiguration.

## 🎯 Example Commands

**Quick syntax check**:
```
@workspace use mutl3y-foreman with quick depth on src/prism/api.py
```

**Deep architectural review**:
```
@workspace use mutl3y-cluster-foreman with deep depth on src/prism/
```

**Check cycle status**:
```
@workspace check the current mutl3y workflow status
```

## 📚 Documentation

- Full workflow: `/raid5/source/test/mutl3y_review_workflow_development/plugins/mutl3y-review-workflow/README.md`
- Testing guide: `/raid5/source/test/mutl3y_review_workflow_development/TESTING.md`
- Mode configuration: `/raid5/source/test/mutl3y_review_workflow_development/CONFIGURATION_MODES.md`

## ⚠️ Important Notes

1. **No slash commands**: Skills are invoked via "@workspace use the <skill-name> skill", not /commands
2. **Configuration required**: Run setup skill before first use
3. **Workspace-specific**: Configuration is stored in `.mutl3y-config.yaml` at workspace root
4. **Development mode**: Skills are copied from mutl3y_review_workflow_development. To update, re-run the copy command.

## 🔄 Updating

To get latest changes from the plugin development directory:
```bash
cd /raid5/source/test/prism
cp -r /raid5/source/test/mutl3y_review_workflow_development/agents/* .github/agents/
cp -r /raid5/source/test/mutl3y_review_workflow_development/skills/* .github/skills/
```

## 🐛 Troubleshooting

**Skills not showing up**:
- Reload VS Code window (Cmd/Ctrl+Shift+P > "Reload Window")
- Check that `.github/agents/` and `.github/skills/` directories exist
- Verify files have `.agent.md` extension and `SKILL.md` in skill folders

**Configuration not persisting**:
- Check that `.mutl3y-config.yaml` exists at workspace root
- Verify file permissions allow writing

**Can't find skills**:
- Use full syntax: "@workspace use the mutl3y-setup skill"
- Don't use slash commands - they don't work in VS Code Copilot
