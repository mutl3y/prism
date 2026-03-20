# Docs Site Maintenance

This directory is configured for GitHub Pages with Jekyll.

## GitHub Pages Configuration

In repository settings:

1. Open `Settings` -> `Pages`.
2. Under `Source`, choose `Deploy from a branch`.
3. Select branch `main` and folder `/docs`.
4. Save.

Your site will publish from this folder and use `index.md` as the homepage.

Current project-site target:

- `https://mutl3y.github.io/prism/`

## Local Preview (Optional)

You can preview the site locally with Jekyll.

### Prerequisites

- Ruby and Bundler installed
- Jekyll gem available

### One-time Setup

From repository root:

```bash
bundle init
bundle add github-pages --group jekyll_plugins
```

### Serve Locally

From repository root:

```bash
bundle exec jekyll serve --source docs --destination _site_docs --baseurl /prism
```

Then open:

- `http://127.0.0.1:4000`

## Files

- `_config.yml`: Jekyll/GitHub Pages config
- `index.md`: docs homepage
- `_sass/minima/custom-styles.scss`: custom style overrides for the Minima theme
- `article.htm`: long-form project article

## Content Updates

- Add new docs markdown files to `docs/`.
- Add links to `index.md` so they appear on the homepage.
- Keep archived plans under `docs/completed_plans/`.
