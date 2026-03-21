# Style Guide Source Repositories

Candidate repositories whose existing READMEs are useful as style guides for generated review output.

## Primary review set

- [geerlingguy/ansible-role-packer](https://github.com/geerlingguy/ansible-role-packer)
  - Strong, widely used Ansible role README structure.
  - Good baseline for sections, examples, and concise operational tone.
- [geerlingguy/ansible-role-nginx](https://github.com/geerlingguy/ansible-role-nginx)
  - Similar maintainable section layout with infrastructure-focused documentation.
- [geerlingguy/ansible-role-apache](https://github.com/geerlingguy/ansible-role-apache)
  - Useful for comparing web-service role documentation patterns.
- [geerlingguy/ansible-role-mysql](https://github.com/geerlingguy/ansible-role-mysql)
  - Good source for variable-heavy role documentation style.
- [geerlingguy/ansible-role-postgresql](https://github.com/geerlingguy/ansible-role-postgresql)
  - Useful for service + configuration + variable-rich examples.
- [geerlingguy/ansible-role-php](https://github.com/geerlingguy/ansible-role-php)
  - Good example of package-oriented role documentation.

## Secondary comparison set

- [mutl3y/ansible_port_listener](https://github.com/mutl3y/ansible_port_listener)
  - Helpful for validating style-guide behavior against a smaller repo with lighter variable metadata.
- [dev-sec/ansible-ssh-hardening](https://github.com/dev-sec/ansible-ssh-hardening)
  - Security-focused role with more opinionated documentation.
- [bertvv/ansible-role-bind](https://github.com/bertvv/ansible-role-bind)
  - Useful for testing dense variable and example sections.
- [weareinteractive/ansible-ssh](https://github.com/weareinteractive/ansible-ssh)
  - Alternative tone/layout for comparison with geerlingguy-style roles.

## Notes

- Use these repositories as formatting and section-structure guides, not as factual sources.
- Generated content should continue to come from the scanner output.
- The first live validation target is `geerlingguy/ansible-role-packer`.
