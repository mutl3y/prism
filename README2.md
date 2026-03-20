Of course. Here is the complete, raw Markdown content. You can copy this directly into your `README.md` file.

---

# Prism: Your Automation's Living Documentation

Project site: [mutl3y.github.io/prism](https://mutl3y.github.io/prism)

<div align="center">
  <!-- Optional: Add a logo here -->
  <!-- <img src="path/to/your/logo.png" alt="Prism Logo" width="200"/> -->
  <p>
    <strong>From Code to Knowledge: Automatically generate beautiful, accurate, and operator-friendly documentation for your Ansible roles, collections, and repositories.</strong>
  </p>
  <p>
    <!-- Badges: Replace placeholders with your actual badge URLs -->
    <a href="#"><img src="https://img.shields.io/pypi/v/prism.svg" alt="PyPI version"></a>
    <a href="#"><img src="https://img.shields.io/github/actions/workflow/status/mutl3y/prism/default.yml?branch=main" alt="Build Status"></a>
    <a href="#"><img src="https://img.shields.io/pypi/l/prism.svg" alt="License"></a>
  </p>
</div>

---

Ansible is the source of truth for your infrastructure, but its documentation is often the first source of technical debt. Manually written READMEs quickly become stale, making roles hard to reuse, difficult to onboard new team members to, and dangerous to operate in a crisis.

**Prism solves this by treating your documentation as code.** It performs static analysis on your Ansible content to generate comprehensive, accurate, and genuinely useful documentation that can never drift from the source of truth.

## ✨ Key Features

Prism goes beyond simple variable lists. It's an ecosystem designed to capture and share your operational knowledge.

### intelligently Adapts to Your Style
>
> **Problem:** Most doc generators force you into a rigid template.
>
> **Prism's Solution:** Having been trained on over 37,000 real-world roles, Prism's AI-powered engine understands common conventions. It intelligently detects your existing section headers (like `Usage`, `Example Playbook`, or `Role Variables`) and injects its content, preserving your hand-written prose. It meets you where you are.

### 🤖 From Code to Crisis: Automated Runbooks
>
> **Problem:** When automation fails, operators need a procedure, not just code.
>
> **Prism's Solution:** Add a simple `#t# Runbook` comment to your tasks to provide human-centric guidance. Prism extracts these directives and generates a clean, ordered operational runbook—a lifeline that translates declarative code into an imperative procedure for when it matters most.
>
> ```yaml
>   #t# Runbook
>   #t# Before proceeding, ensure no active transactions are in the message queue.
>   #t# Use `mq-status --check` to verify.
> - name: Stop the primary application service
>   ansible.builtin.service:
>     name: my-app
>     state: stopped
> ```

### 🌐 Fleet-Wide Governance with `prism-learn`
>
> **Problem:** You can't manage what you can't measure.
>
> **Prism's Solution:** Prism exports rich, structured metadata about your entire automation fleet. Its companion project, [`prism-learn`](https://github.com/mutl3y/prism-learn), ingests this data, allowing you to answer strategic questions about documentation health, complexity hotspots, and dependency risk across your entire organization.

## 🚀 Quick Start

Get your first auto-generated README in under a minute.

1. **Install Prism** from PyPI:

    ```bash
    pip install prism-ansible
    ```

2. **Navigate** to your project directory:

    ```bash
    cd /path/to/your/ansible-project
    ```

3. **Run Prism** against a role:

    ```bash
    prism role roles/my-webserver-role
    ```

4. **Done!** Open `roles/my-webserver-role/README.md` to see your new, living documentation.

## ⚙️ CI/CD Integration: Keep Docs Fresh Automatically

Prism is designed to run in your CI/CD pipeline, ensuring your documentation is always in sync with your code. Here’s a sample GitHub Action that automatically updates the README on every push to `main`.

**`.github/workflows/prism-docs.yml`**

```yaml
name: Update Prism Docs

on:
  push:
    branches:
      - main

jobs:
  update-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install Prism
        run: pip install prism-ansible

      - name: Run Prism on a role
        # Or use 'prism repo .' to scan the entire repository
        run: prism role path/to/your/role

      - name: Commit updated README
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "docs: Regenerate Prism documentation"
          file_pattern: "path/to/your/role/README.md"
```

## Command-Line Usage

Prism provides commands to scan at different scopes:

* **Scan a single role:**

    ```bash
    prism role <path/to/role>
    ```

* **Scan an entire collection:**

    ```bash
    prism collection <path/to/collection>
    ```

* **Scan a full repository:**

    ```bash
    prism repo <path/to/repo>
    ```

Run `prism --help` for a full list of commands and options, including different output formats like `json`, `html`, and `pdf`.

## 🔧 Configuration

For advanced customization, create a `.prism.yml` file in the root of your target repository. This allows you to override default settings, map custom section headers, and fine-tune output behavior.

**Example `.prism.yml`:**

```yaml
# .prism.yml
style_guide:
  # Tell Prism that your "How to Use" section is for role usage
  section_mappings:
    usage: "How to Use"

output:
  # Change the header for the variables section in the final README
  variable_section_title: "Available Knobs"
```

## 🌱 Contributing

Prism is an open-source project, and contributions are welcome! Whether it's submitting a bug report, adding a new feature, or improving documentation, we'd love to have your help. Please see our [Contributing Guide](docs/CONTRIBUTING.md) to get started.

## 📄 License

Prism is licensed under the [MIT License](LICENSE).
