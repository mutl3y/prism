# RUNBOOK: role_demo
---


## Contents

- [Role Notes](#role-notes)
- [Prepare demo service prerequisites](#task-main-yml-prepare-demo-service-prerequisites-1)
- [Ensure demo service group exists](#task-prepare-yml-ensure-demo-service-group-exists-2)
- [Ensure demo service user exists](#task-prepare-yml-ensure-demo-service-user-exists-3)
- [Ensure demo config file is present](#task-main-yml-ensure-demo-config-file-is-present-4)
- [Deploy rendered configuration and validate settings](#task-main-yml-deploy-rendered-configuration-and-validate-settings-5)
- [Render demo service configuration](#task-deploy-yml-render-demo-service-configuration-6)
- [Verify configured feature flags](#task-deploy-yml-verify-configured-feature-flags-7)

---

## Role Notes
<a id="role-notes"></a>

- **Warning:** rollback=manual timeout=60s
- **Note:** This fixture exists only to exercise Prism scanners.


---

## Task Runbooks

<a id="task-main-yml-prepare-demo-service-prerequisites-1"></a>

#### `main.yml` - Prepare demo service prerequisites

- owner=platform impact=low

---

<a id="task-prepare-yml-ensure-demo-service-group-exists-2"></a>

#### `prepare.yml` - Ensure demo service group exists

- owner=platform step=prepare impact=low

---

<a id="task-prepare-yml-ensure-demo-service-user-exists-3"></a>

#### `prepare.yml` - Ensure demo service user exists


---

<a id="task-main-yml-ensure-demo-config-file-is-present-4"></a>

#### `main.yml` - Ensure demo config file is present

- Note: This fixture exists only to exercise Prism scanners.

---

<a id="task-main-yml-deploy-rendered-configuration-and-validate-settings-5"></a>

#### `main.yml` - Deploy rendered configuration and validate settings


---

<a id="task-deploy-yml-render-demo-service-configuration-6"></a>

#### `deploy.yml` - Render demo service configuration

- Warning: rollback=manual timeout=60s

---

<a id="task-deploy-yml-verify-configured-feature-flags-7"></a>

#### `deploy.yml` - Verify configured feature flags


---
