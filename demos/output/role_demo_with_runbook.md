# role_demo

Auto-generated scan summary for role_demo.

## Role Variables

| Variable | Default | Type | Required | Source |
| --- | --- | --- | --- | --- |
| `demo_allowed_networks` | `[10.0.0.0/24, 192.168.10.0/24]` | list | No | defaults/main.yml |
| `demo_feature_flags` | `[docs, reporting]` | list | No | defaults/main.yml |
| `demo_service_enabled` | `true` | bool | No | defaults/main.yml |
| `demo_service_log_level` | `info` | str | No | defaults/main.yml |
| `demo_service_name` | `prism-demo` | str | No | defaults/main.yml |
| `demo_service_port` | `8080` | int | No | defaults/main.yml |

## Requirements

- {'collection': 'ansible.builtin'}
