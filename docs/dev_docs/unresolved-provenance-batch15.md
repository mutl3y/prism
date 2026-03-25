---
layout: default
title: Unresolved Provenance Issues — Batch 15
---

## Unresolved Provenance Issues — Batch 15

**Batch:** 15 (`overnigh_500-builtins-top20-20260324`)
**Cohort:** 20 matched targets
**Total variables:** 5,257
**Unresolved:** 1,300 (24.73%)

Variables are grouped by provenance category. Only `is_unresolved=true` rows
and `is_ambiguous=true` rows appear here. Resolved variables are omitted.

---

## ansible-opnsense

**Repo:** <https://github.com/Rosa-Luxemburgstiftung-Berlin/ansible-opnsense>
**Unresolved:** 128 / 216 (59.3%)
**Ambiguous:** 21

### No static definition (128)

- `__ipsec_section`
- `__ipsec_section_listname`
- `__ipsec_section_loop`
- `__ipsec_section_settings`
- `__ipsec_section_settings_elem`
- `__swanctl_section`
- `__swanctl_section_listname`
- `__swanctl_section_loop`
- `__swanctl_section_settings`
- `__swanctl_section_settings_elem`
- `__uuid`
- `__uuidsettings`
- `_checkelements`
- `_configd_action`
- `_filter`
- `_filtersettings`
- `_nutsection`
- `_opnldapusers`
- `_opnunbndsettings`
- `_opnunbndsettingsuuid`
- `_srcdst`
- `_uuid`
- `_uuidvalues`
- `_vlan`
- `_vlansettings`
- `alert`
- `alertcfg`
- `cfg`
- `clients`
- `clientscfg`
- `configd_actions`
- `configd_actions_scripts`
- `configd_actions_template_scripts`
- `cronjobcfg`
- `delete_local_xml_file`
- `dnsallowoverride`
- `dnslocalhost`
- `dnsserver`
- `domainname`
- `group`
- `hostname`
- `ignore_deprecate_gateways_with_names_per_iface`
- `ikeid`
- `ikeids`
- `instance`
- `instancecfg`
- `ipsecphasevar`
- `ipsecphasevar2`
- `job`
- `nolog_ldapusersync`
- `nutsection`
- `nutsectioncfg`
- `opn_IPsec`
- `opn_Swanctl`
- `opn_alias`
- `opn_authservers`
- `opn_bridges`
- `opn_cas`
- `opn_certs`
- `opn_check_filter_rules`
- `opn_cron_jobs`
- `opn_dhcpd`
- `opn_dhcpd_staticmap`
- `opn_dyndns_accounts`
- `opn_dyndns_general`
- `opn_filter`
- `opn_gateway_groups`
- `opn_gateways`
- `opn_gateways_version`
- `opn_general`
- `opn_group`
- `opn_haproxy_backends`
- `opn_haproxy_frontends`
- `opn_haproxy_general`
- `opn_haproxy_healthchecks`
- `opn_haproxy_servers`
- `opn_hasync`
- `opn_ifgroups`
- `opn_interfaces_all`
- `opn_interfaces_remove`
- `opn_interfaces_specific`
- `opn_interfaces_vlan_parent_interface`
- `opn_ipsec`
- `opn_laggs`
- `opn_monit`
- `opn_nat`
- `opn_nat_onetoone`
- `opn_nat_port_forward`
- `opn_nat_settings`
- `opn_nextid`
- `opn_nut`
- `opn_openvpn_instances`
- `opn_openvpn_overwrites`
- `opn_openvpn_servers`
- `opn_openvpn_statickeys`
- `opn_staticroutes`
- `opn_sync_users_ldap_remove_tmp`
- `opn_sysctl`
- `opn_syslog`
- `opn_unbound`
- `opn_unboundplus`
- `opn_unset`
- `opn_user_from_ldap`
- `opn_virtualip`
- `opn_virtualip_all`
- `opn_virtualip_specific`
- `opn_vlan_filter`
- `opn_vlans`
- `opn_wireguard`
- `opn_zabbixagent`
- `overwrite`
- `overwritecfg`
- `p2`
- `rule`
- `servers`
- `serverscfg`
- `servicecfg`
- `services`
- `statickey`
- `statickeycfg`
- `testcfg`
- `tests`
- `unboundplussection`
- `unboundplussectionsettings`
- `uniqid`
- `unsetitem`
- `userparameter`
- `uuid`

### Ambiguous: Runtime set\_fact (21)

- `_configured_ca2uuid`
- `_configured_cert2uuid`
- `_configured_group2uuid`
- `_configured_user2uuid`
- `_current_nextuid`
- `_current_user`
- `_current_user_uid`
- `_foundcheckelements`
- `_ldbsearch_argv`
- `_listsort`
- `change_dns`
- `change_hashalgopt`
- `configuredmemberlist`
- `dhcp_registered_dnsserver`
- `dhcp_registered_dnsserver_count`
- `dnsallowoverride_state`
- `eao_list`
- `encalgopt_children`
- `encalgopt_reset`
- `opn_user`
- `requestedmemberlist`

---

## AZURE-CIS

**Repo:** <https://github.com/ansible-lockdown/AZURE-CIS>
**Unresolved:** 128 / 273 (46.9%)

### No static definition (128)

- `api_parameters`
- `az_sql_server_advanced_threat_protection_setting`
- `az_sql_server_advanced_threat_protection_setting_raw`
- `az_sql_server_firewall_rule`
- `az_sql_server_firewall_rule_raw`
- `az_sql_server_vulnerability_assessment_setting`
- `az_sql_server_vulnerability_assessment_setting_raw`
- `azfcis_days_retained`
- `azure_access_token`
- `azure_activity_log_alerts`
- `azure_activity_log_alerts_raw`
- `azure_aks_list`
- `azure_aks_list_raw`
- `azure_auth_header`
- `azure_disk_list`
- `azure_disk_list_raw`
- `azure_keyvault_key_list`
- `azure_keyvault_key_list_raw`
- `azure_keyvault_list`
- `azure_keyvault_list_raw`
- `azure_keyvault_secret_list`
- `azure_keyvault_secret_list_raw`
- `azure_locations_with_virtual_network`
- `azure_lock_list`
- `azure_lock_list_raw`
- `azure_monitor_diagnostic_settings_list`
- `azure_monitor_diagnostic_settings_list_all`
- `azure_monitor_diagnostic_settings_list_all_raw`
- `azure_monitor_diagnostic_settings_list_raw`
- `azure_monitor_diagnostic_settings_subscription_list`
- `azure_monitor_diagnostic_settings_subscription_list_raw`
- `azure_monitor_log_profiles_list`
- `azure_monitor_log_profiles_list_raw`
- `azure_mysql_server_list`
- `azure_mysql_server_list_raw`
- `azure_network_nsg_list`
- `azure_network_nsg_list_raw`
- `azure_network_vnet_list`
- `azure_network_vnet_list_raw`
- `azure_network_watcher_flow_log_show`
- `azure_network_watcher_flow_log_show_raw`
- `azure_network_watcher_list_raw`
- `azure_postgres_server_configuration_list`
- `azure_postgres_server_configuration_list_raw`
- `azure_postgres_server_firewall_rule_list`
- `azure_postgres_server_firewall_rule_list_raw`
- `azure_postgres_server_list`
- `azure_postgres_server_list_raw`
- `azure_resource_list`
- `azure_resource_list_keyvault`
- `azure_resource_list_keyvault_raw`
- `azure_resource_list_raw`
- `azure_resource_show_keyvault`
- `azure_resource_show_keyvault_raw`
- `azure_role_definition_list`
- `azure_role_definition_list_raw`
- `azure_security_center_policy_assignments`
- `azure_security_contacts`
- `azure_security_pricing_app_services`
- `azure_security_pricing_container_registry`
- `azure_security_pricing_key_vaults`
- `azure_security_pricing_kubernetes_service`
- `azure_security_pricing_mcas`
- `azure_security_pricing_raw`
- `azure_security_pricing_sql_servers`
- `azure_security_pricing_sql_sql_server_virtual_machines`
- `azure_security_pricing_storage_accounts`
- `azure_security_pricing_virtual_machine`
- `azure_security_pricing_wdatp`
- `azure_service_principal`
- `azure_sql_db_list`
- `azure_sql_db_list_raw`
- `azure_sql_db_tde_show`
- `azure_sql_db_tde_show_raw`
- `azure_sql_server_ad_admin_list`
- `azure_sql_server_ad_admin_list_raw`
- `azure_sql_server_audit_policy_show`
- `azure_sql_server_audit_policy_show_raw`
- `azure_sql_server_list`
- `azure_sql_server_list_raw`
- `azure_sql_server_tde_protector_list`
- `azure_sql_server_tde_protector_list_raw`
- `azure_storage_account_list`
- `azure_storage_account_list_raw`
- `azure_storage_account_logging_show_queue`
- `azure_storage_account_logging_show_queue_raw`
- `azure_storage_blob_delete_policy_show`
- `azure_storage_blob_delete_policy_show_raw`
- `azure_storage_container_list`
- `azure_storage_container_list_raw`
- `azure_storage_logging_show_blob`
- `azure_storage_logging_show_blob_raw`
- `azure_storage_logging_show_table`
- `azure_storage_logging_show_table_raw`
- `azure_subscription_auto_provisioning_settings`
- `azure_subscription_id`
- `azure_vm_extension_list_raw`
- `azure_vm_list`
- `azure_vm_list_raw`
- `azure_vm_show`
- `azure_vm_show_raw`
- `azure_webapp_auth_show`
- `azure_webapp_auth_show_raw`
- `azure_webapp_config_show`
- `azure_webapp_config_show_raw`
- `azure_webapp_deployment_list_publishing_profiles`
- `azure_webapp_deployment_list_publishing_profiles_raw`
- `azure_webapp_identity_show`
- `azure_webapp_identity_show_raw`
- `azure_webapp_list`
- `azure_webapp_list_raw`
- `azure_webapp_show`
- `azure_webapp_show_raw`
- `evidence_query`
- `exception_evidence_message`
- `guest_users`
- `insights_operational_logs_storage_container_list`
- `locations_with_virtual_network_but_without_network_watcher`
- `non_privileged_user_roles_with_no_mfa`
- `packages`
- `privileged_user_roles_with_no_mfa`
- `request_graph_access_token_output`
- `role_assignments`
- `rule_results`
- `rule_results_path`
- `this_rule`
- `user_roles`
- `users`

---

## bitcoin_core

**Repo:** <https://github.com/lifeofguenter/ansible-role-bitcoin-core>
**Unresolved:** 96 / 104 (92.3%)

### No static definition (96)

- `ansible_managed`
- `ansible_processor_vcpus`
- `bitcoin_conf_addnode`
- `bitcoin_conf_alertnotify`
- `bitcoin_conf_assumevalid`
- `bitcoin_conf_banscore`
- `bitcoin_conf_bantime`
- `bitcoin_conf_bind`
- `bitcoin_conf_blockmaxsize`
- `bitcoin_conf_blockmaxweight`
- `bitcoin_conf_blockmintxfee`
- `bitcoin_conf_blocknotify`
- `bitcoin_conf_blockprioritysize`
- `bitcoin_conf_blockreconstructionextratxn`
- `bitcoin_conf_bytespersigop`
- `bitcoin_conf_connect`
- `bitcoin_conf_daemon`
- `bitcoin_conf_datacarrier`
- `bitcoin_conf_datacarriersize`
- `bitcoin_conf_dbcache`
- `bitcoin_conf_debug`
- `bitcoin_conf_disablewallet`
- `bitcoin_conf_discover`
- `bitcoin_conf_dns`
- `bitcoin_conf_dnsseed`
- `bitcoin_conf_externalip`
- `bitcoin_conf_fallbackfee`
- `bitcoin_conf_forcednsseed`
- `bitcoin_conf_keypool`
- `bitcoin_conf_listen`
- `bitcoin_conf_listenonion`
- `bitcoin_conf_loadblock`
- `bitcoin_conf_logips`
- `bitcoin_conf_logtimestamps`
- `bitcoin_conf_maxconnections`
- `bitcoin_conf_maxmempool`
- `bitcoin_conf_maxorphantx`
- `bitcoin_conf_maxreceivebuffer`
- `bitcoin_conf_maxsendbuffer`
- `bitcoin_conf_maxtimeadjustment`
- `bitcoin_conf_maxtxfee`
- `bitcoin_conf_maxuploadtarget`
- `bitcoin_conf_mempoolexpiry`
- `bitcoin_conf_mempoolreplacement`
- `bitcoin_conf_minrelaytxfee`
- `bitcoin_conf_mintxfee`
- `bitcoin_conf_onion`
- `bitcoin_conf_onlynet`
- `bitcoin_conf_par`
- `bitcoin_conf_paytxfee`
- `bitcoin_conf_peerbloomfilters`
- `bitcoin_conf_permitbaremultisig`
- `bitcoin_conf_port`
- `bitcoin_conf_printtoconsole`
- `bitcoin_conf_proxy`
- `bitcoin_conf_proxyrandomize`
- `bitcoin_conf_prune`
- `bitcoin_conf_reindex`
- `bitcoin_conf_reindex_chainstate`
- `bitcoin_conf_rescan`
- `bitcoin_conf_rest`
- `bitcoin_conf_rpcallowip`
- `bitcoin_conf_rpcauth`
- `bitcoin_conf_rpcbind`
- `bitcoin_conf_rpccookiefile`
- `bitcoin_conf_rpcpassword`
- `bitcoin_conf_rpcport`
- `bitcoin_conf_rpcserialversion`
- `bitcoin_conf_rpcthreads`
- `bitcoin_conf_rpcuser`
- `bitcoin_conf_salvagewallet`
- `bitcoin_conf_seednode`
- `bitcoin_conf_server`
- `bitcoin_conf_shrinkdebugfile`
- `bitcoin_conf_spendzeroconfchange`
- `bitcoin_conf_sysperms`
- `bitcoin_conf_testnet`
- `bitcoin_conf_timeout`
- `bitcoin_conf_torcontrol`
- `bitcoin_conf_torpassword`
- `bitcoin_conf_txconfirmtarget`
- `bitcoin_conf_txindex`
- `bitcoin_conf_uacomment`
- `bitcoin_conf_upgradewallet`
- `bitcoin_conf_usehd`
- `bitcoin_conf_wallet`
- `bitcoin_conf_walletbroadcast`
- `bitcoin_conf_walletnotify`
- `bitcoin_conf_walletrbf`
- `bitcoin_conf_whitebind`
- `bitcoin_conf_whitelist`
- `bitcoin_conf_whitelistforcerelay`
- `bitcoin_conf_whitelistrelay`
- `bitcoin_conf_zapwallettxes`
- `blockprioritysize`
- `packages`

---

## open_ondemand

**Repo:** <https://github.com/OSC/ood-ansible>
**Unresolved:** 94 / 185 (50.8%)
**Ambiguous:** 2

### No static definition (94)

- `additional_rpm_installs`
- `agent_tar`
- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_distribution_release`
- `ansible_managed`
- `ansible_os_family`
- `apache_oidc_mod_package`
- `auto_groups_filter`
- `clusters`
- `custom_location_directives`
- `custom_vhost_directives`
- `dashboard_layout`
- `dex_settings`
- `dex_uri`
- `disable_logs`
- `disabled_shell_message`
- `dummy`
- `facl_domain`
- `globus_endpoints`
- `google_analytics_tag_id`
- `help_menu`
- `httpd_access_log`
- `httpd_error_log`
- `httpd_logformat`
- `install_from_src`
- `listen_addr_port`
- `map_fail_uri`
- `module_file_dir`
- `nginx_min_uid`
- `nginx_root`
- `nginx_tar`
- `nginx_version`
- `node_uri`
- `oidc_client_id`
- `oidc_client_secret`
- `oidc_cookie_same_site`
- `oidc_crypto_passphrase`
- `oidc_discover_root`
- `oidc_discover_uri`
- `oidc_provider_metadata_url`
- `oidc_remote_user_claim`
- `oidc_scope`
- `oidc_session_inactivity_timeout`
- `oidc_session_max_duration`
- `oidc_settings`
- `oidc_state_max_number_of_cookies`
- `oidc_uri`
- `ood_apps`
- `ood_auth_openidc`
- `ood_install_apps`
- `ood_oidc_crypto_passphrase`
- `ood_ondemand_d_configs`
- `passenger_agent_url`
- `passenger_base_dir`
- `passenger_disable_anonymous_telemetry`
- `passenger_lib_dir`
- `passenger_log_file`
- `passenger_nginx_url`
- `passenger_remote_dl`
- `passenger_src_dir`
- `passenger_support_binaries_dir`
- `passenger_tar`
- `passenger_url`
- `passenger_version`
- `pinned_apps`
- `pinned_apps_group_by`
- `pinned_apps_menu_length`
- `proxy_server`
- `pun_custom_env`
- `pun_log_format`
- `pun_pre_hook_exports`
- `pun_pre_hook_root_cmd`
- `register_method`
- `register_method_options`
- `register_root`
- `register_uri`
- `rnode_uri`
- `ruby_lib_dir`
- `secure_node_uri`
- `secure_rnode_uri`
- `security_csp_frame_ancestors`
- `security_strict_transport`
- `show_nginx_stage_help_message`
- `ssl`
- `ssl_proxy`
- `strip_proxy_cookies`
- `strip_proxy_headers`
- `support_ticket`
- `tmpdir`
- `user_env`
- `user_map_cmd`
- `user_regex`
- `user_settings_file`

### Ambiguous: Runtime set\_fact (2)

- `deb_distro`
- `el_distro`

---

## rhel6_stig

**Repo:** <https://github.com/ansible-lockdown/RHEL6-STIG>
**Unresolved:** 76 / 123 (61.8%)

### No static definition (76)

- `aide_dbfile`
- `ansible_architecture`
- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_mounts`
- `audit_arch`
- `audit_log_dir_owner_audit`
- `audit_log_dir_perms_audit`
- `audit_log_file_perms_audit`
- `audit_package_group_ownership_audit`
- `audit_package_integrity_check_audit`
- `audit_package_ownership_audit`
- `audit_package_permissions_audit`
- `auditd_logfile`
- `auditd_syslog_output_audit`
- `auto_lock_enable_audit`
- `bluetooth_service_check`
- `dev_shm_mount`
- `gconftool_pattern_audit`
- `grub_audit_audit`
- `grub_auth_audit`
- `grub_pass`
- `gui_screen_lock_hotkey_audit`
- `idle_lock_audit`
- `idle_timeout_gconf_audit`
- `interface_config_files`
- `ip6tables_config`
- `iptables_config`
- `login_failures_account_require`
- `login_failures_interval_audit`
- `logindefs_pass_warn_age_audit`
- `mac_policy_audit`
- `nfs_all_squash_disabled_audit`
- `nfs_mounts_missing_nodev`
- `nfs_mounts_missing_nosuid`
- `pamd_files`
- `postfix_service_running_audit`
- `repo_crypto_check_audit`
- `repo_d_gpgcheck_check_audit`
- `rexec_service_check`
- `rhel_06_000530_audit`
- `rhel_06_000531_audit`
- `rhel_06_000532_audit`
- `rlogin_service_check`
- `rpm_file_permissions_audit`
- `rpm_group_ownership_audit`
- `rpm_integrity_audit`
- `rpm_verify_packages`
- `rsh_service_check`
- `rsyslog_logfiles`
- `samba_check`
- `securetty_serial_consoles_audit`
- `selinux_device_file_context_audit`
- `selinux_device_file_context_patch`
- `selinux_policy_audit`
- `setugid_programs`
- `snmpconf_test`
- `snmpd_audit`
- `snmpd_version_audit`
- `sshd_client_alive_interval_audit`
- `sudoer_configs`
- `sudoers_include_audit`
- `sudoers_includedirs_files`
- `sys_command_owner_audit`
- `sys_command_perms_audit`
- `sys_lib_owner_audit`
- `sys_lib_perms_audit`
- `telnet_service_check`
- `unlocked_sys_accounts_audit`
- `users`
- `vsftpd_config_file_audit`
- `vsftpd_service_installed_audit`
- `vsftpd_xinetd_startup_file_audit`
- `wireless_interface_config_files`
- `xinetd_services`
- `ypbind_service_check`

---

## Ansible-RHEL7-CIS-Benchmarks

**Repo:** <https://github.com/HarryHarcourt/Ansible-RHEL7-CIS-Benchmarks>
**Unresolved:** 74 / 247 (30.0%)
**Ambiguous:** 1

### No static definition (74)

- `accounts_6_2_1`
- `aide_1_3_1`
- `ansible_default_ipv4`
- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_distribution_version`
- `ansible_managed`
- `ansible_mounts`
- `at`
- `audit_5_4_2`
- `audit_6_1_1`
- `audit_6_1_10`
- `audit_6_1_11`
- `audit_6_1_12`
- `audit_6_1_13`
- `audit_6_1_14`
- `audit_6_2_10`
- `audit_6_2_11`
- `audit_6_2_12`
- `audit_6_2_13`
- `audit_6_2_14`
- `audit_6_2_15`
- `audit_6_2_16`
- `audit_6_2_17`
- `audit_6_2_18`
- `audit_6_2_19`
- `audit_6_2_6`
- `audit_6_2_7`
- `audit_6_2_8`
- `audit_6_2_9`
- `cat_5_4_3`
- `cis_st`
- `cron`
- `egrep_5_4_1_1`
- `egrep_5_4_1_2`
- `egrep_5_4_1_3`
- `egrep_5_4_1_4`
- `find_logfiles_4_2_4`
- `gpg_pubkey_check`
- `grub_1_4_1`
- `hosts_allow_3_4_2`
- `hosts_deny_3_4_3`
- `modprobe_1_1_1_1`
- `modprobe_1_1_1_2`
- `modprobe_1_1_1_3`
- `modprobe_1_1_1_4`
- `modprobe_1_1_1_5`
- `modprobe_1_1_1_6`
- `modprobe_1_1_1_7`
- `modprobe_1_1_1_8`
- `modprobe_3_3_3`
- `modprobe_3_5_1`
- `modprobe_3_5_2`
- `modprobe_3_5_3`
- `modprobe_3_5_4`
- `security_limits_1_5_1`
- `sha512_check`
- `shell_output`
- `sshd_config`
- `sysconfig_init_1_4_2`
- `sysconfig_init_1_4_3`
- `v_3_1_1_kernel_param`
- `v_3_1_2_kernel_param`
- `v_3_2_1_kernel_param`
- `v_3_2_2_kernel_param`
- `v_3_2_3_kernel_param`
- `v_3_2_4_kernel_param`
- `v_3_2_5_kernel_param`
- `v_3_2_6_kernel_param`
- `v_3_2_7_kernel_param`
- `v_3_2_8_kernel_param`
- `v_3_3_1_kernel_param`
- `v_3_3_2_kernel_param`
- `which_1_5_4`

### Ambiguous: Other ambiguous (1)

- `cis_aide_database_filename`

---

## clickhouse

**Repo:** <https://github.com/idealista/clickhouse_role>
**Unresolved:** 71 / 192 (37.0%)
**Ambiguous:** 1

### No static definition (71)

- `ansible_distribution`
- `ansible_managed`
- `ansible_os_family`
- `clickhouse_admin_password`
- `clickhouse_admin_user`
- `clickhouse_admin_users`
- `clickhouse_compression`
- `clickhouse_config_xml_extra_config`
- `clickhouse_copier_custom_config_file_path`
- `clickhouse_custom_config_file_path`
- `clickhouse_custom_extra_config_file_path`
- `clickhouse_custom_extra_users_file_path`
- `clickhouse_custom_grant_roles`
- `clickhouse_custom_grants`
- `clickhouse_custom_headers_response`
- `clickhouse_custom_profiles`
- `clickhouse_custom_quotas_xml`
- `clickhouse_custom_users_file_path`
- `clickhouse_custom_users_xml`
- `clickhouse_default_database`
- `clickhouse_default_replica_name`
- `clickhouse_default_replica_path`
- `clickhouse_distributed_ddl`
- `clickhouse_encryption`
- `clickhouse_graphite`
- `clickhouse_grpc_port`
- `clickhouse_http_handlers`
- `clickhouse_https_port`
- `clickhouse_interserver_http_host`
- `clickhouse_interserver_https_port`
- `clickhouse_jdbc_bridge`
- `clickhouse_jdbc_bridge_config_path`
- `clickhouse_jdbc_bridge_datasources`
- `clickhouse_jdbc_bridge_datasources_path`
- `clickhouse_jdbc_bridge_deb_package`
- `clickhouse_jdbc_bridge_documentation_link`
- `clickhouse_jdbc_bridge_drivers_path`
- `clickhouse_jdbc_bridge_env`
- `clickhouse_jdbc_bridge_file_drivers_path`
- `clickhouse_jdbc_bridge_group`
- `clickhouse_jdbc_bridge_log_file`
- `clickhouse_jdbc_bridge_log_level`
- `clickhouse_jdbc_bridge_log_path`
- `clickhouse_jdbc_bridge_service`
- `clickhouse_jdbc_bridge_service_enabled`
- `clickhouse_jdbc_bridge_service_state`
- `clickhouse_jdbc_bridge_service_template_path`
- `clickhouse_jdbc_bridge_user`
- `clickhouse_keeper`
- `clickhouse_kerberos`
- `clickhouse_ldap`
- `clickhouse_listen_backlog`
- `clickhouse_listen_hosts`
- `clickhouse_listen_reuse_port`
- `clickhouse_listen_try`
- `clickhouse_logger_overrides`
- `clickhouse_logger_overrides_legacy`
- `clickhouse_macros`
- `clickhouse_mergetree_settings`
- `clickhouse_packages_extra`
- `clickhouse_prometheus`
- `clickhouse_remote_url_allow_hosts`
- `clickhouse_replicated_tables_macros`
- `clickhouse_rocksdb`
- `clickhouse_tcp_port_secure`
- `clickhouse_tcp_with_proxy_port`
- `clickhouse_user_directories_ldap`
- `clickhouse_user_xml_extra_config`
- `clickhouse_zookeeper`
- `clikhouse_interserver_http_credentials`
- `row`

### Ambiguous: Runtime set\_fact (1)

- `actual_privs`

---

## datadog

**Repo:** <https://github.com/DataDog/ansible-datadog>
**Unresolved:** 65 / 273 (23.8%)
**Ambiguous:** 55

### No static definition (65)

- `Agent`
- `CURRENT`
- `Cleaning`
- `Since`
- `This`
- `a`
- `agent`
- `agent_datadog_repo_file_contents`
- `agent_dd_config_dir`
- `agent_dd_group`
- `agent_dd_notify_agent`
- `agent_dd_user`
- `agent_groupname`
- `agent_regexp`
- `agent_username`
- `ansible_date_time`
- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_distribution_version`
- `ansible_managed`
- `baseurl`
- `because`
- `command`
- `compliance_config`
- `datadog_agent_max_minor_version`
- `datadog_bugfix`
- `datadog_integration`
- `datadog_major`
- `datadog_minor`
- `datadog_url`
- `datadog_use_mount`
- `don`
- `downgrading`
- `expect`
- `fail`
- `found`
- `http_proxy`
- `if`
- `import`
- `include`
- `installed`
- `installed_agent_regexp`
- `integration`
- `lot`
- `major`
- `maybe_arch`
- `metadata`
- `needed`
- `of`
- `older`
- `only`
- `runtime_security_config`
- `security`
- `supposed`
- `t`
- `task`
- `the`
- `them`
- `third_party`
- `this`
- `to`
- `version`
- `versions`
- `want`
- `we`

### Ambiguous: Runtime set\_fact (55)

- `agent_datadog_agent_debian_version`
- `agent_datadog_agent_linux_version`
- `agent_datadog_agent_macos_version`
- `agent_datadog_agent_major_version`
- `agent_datadog_agent_os2version`
- `agent_datadog_agent_redhat_version`
- `agent_datadog_agent_suse_version`
- `agent_datadog_agent_windows_version`
- `agent_datadog_before_7180`
- `agent_datadog_before_7241`
- `agent_datadog_before_7400`
- `agent_datadog_before_7610`
- `agent_datadog_bugfix`
- `agent_datadog_checks`
- `agent_datadog_config`
- `agent_datadog_downgrade_detected`
- `agent_datadog_epoch`
- `agent_datadog_force_reinstall`
- `agent_datadog_includepkgs`
- `agent_datadog_installed_bugfix`
- `agent_datadog_installed_major`
- `agent_datadog_installed_minor`
- `agent_datadog_installed_version`
- `agent_datadog_major`
- `agent_datadog_minor`
- `agent_datadog_release`
- `agent_datadog_remove_custom_repo_file`
- `agent_datadog_rpm_version_finding_cmd`
- `agent_datadog_skip_install`
- `agent_datadog_suffix`
- `agent_datadog_sysprobe_enabled`
- `agent_datadog_sysprobe_installed`
- `agent_datadog_tracked_checks`
- `agent_datadog_version_finding_cmds`
- `agent_datadog_windows_config_root`
- `agent_datadog_windows_installed_product_ids`
- `agent_dd_download_url`
- `agent_do_yum_repo_gpgcheck`
- `agent_do_zypper_repo_gpgcheck`
- `agent_key_fingerprint`
- `agent_key_needs_import`
- `agent_keyring_url`
- `agent_macos_user_data`
- `agent_version`
- `agent_win_install_args`
- `ansible_pkg_mgr`
- `apm_single_step_instrumentation_should_install`
- `datadog_agent_binary_path`
- `datadog_agent_target`
- `datadog_apm_single_step_instrumentation_environment`
- `datadog_installer_install_ssi_script_url`
- `datadog_remote_update_in_progress`
- `install_info`
- `install_signature`
- `integration_command_user`

---

## CIS-Debian10-Ansible

**Repo:** <https://github.com/dbernaci/CIS-Debian10-Ansible>
**Unresolved:** 63 / 318 (19.8%)

### No static definition (63)

- `all_mounts`
- `ansible_mounts`
- `debian10cis_rules_5_4_1_1`
- `debian10cis_rules_5_4_1_2`
- `debian10cis_rules_5_4_1_3`
- `multiline`
- `output_1_1_10`
- `output_1_1_10_opts`
- `output_1_1_21`
- `output_1_1_3`
- `output_1_1_3_opts`
- `output_1_1_4`
- `output_1_1_4_opts`
- `output_1_1_5`
- `output_1_1_5_opts`
- `output_1_1_8`
- `output_1_1_8_opts`
- `output_1_1_9`
- `output_1_1_9_opts`
- `output_1_6_1`
- `output_1_7_1_2`
- `output_2_2_15`
- `output_3_1_2`
- `output_3_2_2`
- `output_3_2_2_v6`
- `output_4_1_11`
- `output_4_2_1_5`
- `output_4_2_3`
- `output_4_3`
- `output_5_1_8_atallow`
- `output_5_1_8_callow`
- `output_5_1_8_dpkg`
- `output_5_2_2`
- `output_5_2_3`
- `output_5_4_1_5`
- `output_5_4_2`
- `output_5_5`
- `output_6_1_1`
- `output_6_1_10`
- `output_6_1_11`
- `output_6_1_12`
- `output_6_1_13`
- `output_6_1_14`
- `output_6_2_1`
- `output_6_2_10`
- `output_6_2_11`
- `output_6_2_12`
- `output_6_2_13`
- `output_6_2_14`
- `output_6_2_15`
- `output_6_2_16`
- `output_6_2_17`
- `output_6_2_18`
- `output_6_2_19`
- `output_6_2_2`
- `output_6_2_20`
- `output_6_2_3`
- `output_6_2_4`
- `output_6_2_5`
- `output_6_2_6`
- `output_6_2_7`
- `output_6_2_8`
- `output_6_2_9`

---

## drone

**Repo:** <https://github.com/appleboy/ansible-drone>
**Unresolved:** 58 / 109 (53.2%)

### No static definition (58)

- `drone_agent_config`
- `drone_authentication_endpoint`
- `drone_authentication_skip_verify`
- `drone_authentication_token`
- `drone_cookie_secret`
- `drone_cookie_secure`
- `drone_cookie_timeout`
- `drone_database_datasource`
- `drone_database_secret`
- `drone_docker_config`
- `drone_gogs_debug`
- `drone_gogs_server`
- `drone_gogs_skip_verify`
- `drone_legacy_token_mapping_file`
- `drone_logs_debug`
- `drone_logs_nocolor`
- `drone_logs_text`
- `drone_logs_trace`
- `drone_registry_endpoint`
- `drone_registry_secret`
- `drone_registry_skip_verify`
- `drone_repository_filter`
- `drone_rpc_secret`
- `drone_runner_arch`
- `drone_runner_devices`
- `drone_runner_environ`
- `drone_runner_kernel`
- `drone_runner_labels`
- `drone_runner_name`
- `drone_runner_os`
- `drone_runner_privileged_images`
- `drone_runner_variant`
- `drone_runner_volumes`
- `drone_secret_endpoint`
- `drone_secret_plugin_endpoint`
- `drone_secret_plugin_skip_verify`
- `drone_secret_plugin_token`
- `drone_secret_secret`
- `drone_secret_skip_verify`
- `drone_server_config`
- `drone_server_proto`
- `drone_stash_consumer_key`
- `drone_stash_consumer_secret`
- `drone_stash_debug`
- `drone_stash_private_key`
- `drone_stash_server`
- `drone_stash_skip_verify`
- `drone_tls_autocert`
- `drone_trace`
- `drone_ui_disabled`
- `drone_ui_password`
- `drone_ui_realm`
- `drone_ui_username`
- `drone_user_create`
- `drone_user_filter`
- `drone_webhook_endpoint`
- `drone_webhook_secret`
- `drone_webhook_skip_verify`

---

## ansible-vault

**Repo:** <https://github.com/ansible-community/ansible-vault>
**Unresolved:** 52 / 319 (16.3%)
**Ambiguous:** 2

### No static definition (51)

- `__vault_plugin_acme_enable`
- `__vault_plugin_acme_registered_sha256`
- `__vault_plugin_acme_sha256sum`
- `__vault_plugin_acme_zip_dir`
- `__vault_plugin_acme_zip_file`
- `__vault_write_acme`
- `_index_plugin`
- `_vault_repo_pkg`
- `_vault_repository_url`
- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_distribution_release`
- `ansible_distribution_version`
- `ansible_env`
- `ansible_managed`
- `ansible_os_family`
- `ansible_pkg_mgr`
- `ansible_python_version`
- `only`
- `read`
- `task`
- `truthy`
- `vault_azurekeyvault_client_id`
- `vault_azurekeyvault_client_secret`
- `vault_azurekeyvault_key_name`
- `vault_azurekeyvault_tenant_id`
- `vault_azurekeyvault_vault_name`
- `vault_backup_config`
- `vault_consul_token`
- `vault_custom_configuration`
- `vault_disable_mlock`
- `vault_os_packages`
- `vault_prometheus_retention_time`
- `vault_raft_autopilot_reconcile_interval`
- `vault_raft_cloud_auto_join`
- `vault_raft_cloud_auto_join_port`
- `vault_raft_cloud_auto_join_scheme`
- `vault_raft_leader_tls_servername`
- `vault_raft_max_entry_size`
- `vault_raft_performance_multiplier`
- `vault_raft_snapshot_threshold`
- `vault_raft_trailing_logs`
- `vault_redirect_address`
- `vault_service_registration_consul_token`
- `vault_statsd_address`
- `vault_statsite_address`
- `vault_telemetry_disable_hostname`
- `vault_telemetry_usage_gauge_period`
- `vault_tls_config_path`
- `vault_transit_namespace`
- `vault_transit_tls_server_name`

### Dynamic include\_vars (path unknown at scan time) (1)

- `params`

### Ambiguous: Runtime set\_fact (2)

- `installation_required`
- `vault_addr`

---

## ansible-my

**Repo:** <https://github.com/Kenya-West/ansible-my>
**Unresolved:** 51 / 51 (100.0%)

### No static definition (51)

- `backup_restic_node_locations_additional`
- `cert_location_root_path`
- `domains_keys`
- `emails`
- `initial_configure_generated_password_analytics_node_docker_exporter`
- `initial_configure_generated_password_analytics_node_fail2ban_exporter`
- `initial_configure_generated_password_analytics_node_frps_exporter_client`
- `initial_configure_generated_password_analytics_node_frps_exporter_prometheus`
- `initial_configure_generated_password_analytics_node_logporter_prometheus`
- `initial_configure_generated_password_analytics_node_logporter_standard_user`
- `initial_configure_generated_password_analytics_node_node_exporter_client`
- `initial_configure_generated_password_analytics_node_node_exporter_prometheus`
- `initial_configure_generated_password_analytics_node_vector_prometheus`
- `initial_configure_generated_password_analytics_node_vector_standard_user`
- `initial_configure_generated_password_analytics_node_vector_victorialogs`
- `initial_configure_generated_password_analytics_server_mongodb_exporter`
- `initial_configure_generated_password_analytics_server_prometheus_grafana`
- `initial_configure_generated_password_analytics_server_prometheus_user`
- `initial_configure_generated_password_analytics_server_pushgateway_client`
- `initial_configure_generated_password_analytics_server_pushgateway_prometheus`
- `initial_configure_generated_password_analytics_server_victorialogs`
- `initial_configure_generated_password_analytics_server_victoriametrics`
- `initial_configure_generated_password_backup_restic_server`
- `initial_configure_generated_password_docker_autodiscovery_basic_auth_users`
- `initial_configure_generated_password_proxy_client_frpc_client_dashboard`
- `initial_configure_generated_password_rclone`
- `initial_configure_generated_password_root`
- `initial_configure_generated_password_vpn_caddy_metrics_client_user`
- `initial_configure_generated_password_vpn_caddy_metrics_prometheus_user`
- `initial_configure_generated_password_vpn_caddy_zapret_secret`
- `initial_configure_generated_password_vpn_common_frp_client_dashboard`
- `initial_configure_generated_password_vpn_common_frp_dashboard`
- `initial_configure_generated_password_vpn_common_frp_token`
- `initial_configure_generated_password_vpn_server_remnawave_custom_login_route`
- `initial_configure_generated_password_vpn_server_remnawave_custom_login_route_path`
- `initial_configure_generated_password_vpn_server_remnawave_metrics`
- `initial_configure_generated_password_wg`
- `initial_configure_generated_password_wg_prometheus_metrics`
- `initial_configure_host_domain_name`
- `initial_configure_host_xray_domain_name`
- `initial_configure_user_input_acme_email`
- `initial_configure_user_input_cloudflare_api_token_dns`
- `initial_configure_user_input_gh_token`
- `initial_configure_user_input_user_email`
- `node_exporter_web_listen_address_port`
- `path_to_internal_services_predefined_full`
- `pgdump_backup_location_root_path`
- `restic_server_docker_vars`
- `root_password`
- `standard_user`
- `vector_exporter_external_port`

---

## windows_2022_stig

**Repo:** <https://github.com/ansible-lockdown/Windows-2022-STIG>
**Unresolved:** 47 / 383 (12.3%)

### No static definition (47)

- `ansible_distribution`
- `ansible_distribution_major_version`
- `ansible_windows_domain_member`
- `ansible_windows_domain_role`
- `warn_control_id`
- `wn22_00_000020_audit_dc`
- `wn22_00_000020_audit_dm_sa`
- `wn22_00_000040_audit`
- `wn22_00_000150_program_files_86_audit`
- `wn22_00_000150_program_files_audit`
- `wn22_00_000160_windows_dir_audit`
- `wn22_00_000180_audit`
- `wn22_00_000190_account_audit_dc`
- `wn22_00_000190_account_audit_dm_sa`
- `wn22_00_000200_audit_dc`
- `wn22_00_000200_audit_dm_sa`
- `wn22_00_000210_audit_dc`
- `wn22_00_000230_audit`
- `wn22_00_000240_files`
- `wn22_00_000270_audit`
- `wn22_00_000280_firewall_audit`
- `wn22_00_000310_audit_dc`
- `wn22_00_000310_audit_sa`
- `wn22_00_000330_audit_dc`
- `wn22_00_000330_audit_sa`
- `wn22_00_000420_audit`
- `wn22_00_000430_audit`
- `wn22_00_000430_isssite_audit`
- `wn22_00_000450_orphaned_group_accounts`
- `wn22_00_000450_orphaned_user_accounts`
- `wn22_au_000030_app_log_location`
- `wn22_au_000030_app_log_permissions`
- `wn22_au_000040_sec_log_location`
- `wn22_au_000040_sec_log_permissions`
- `wn22_au_000050_system_log_location`
- `wn22_au_000050_system_log_permissions`
- `wn22_au_000060_event_viewer_permissions`
- `wn22_dc_000120_audit_dirlocation`
- `wn22_dc_000120_audit_shares`
- `wn22_dc_000310_audit`
- `wn22_dc_000430_audit`
- `wn22_pk_000010_root_3_Check`
- `wn22_pk_000010_root_4_Check`
- `wn22_pk_000010_root_5_Check`
- `wn22_pk_000010_root_6_Check`
- `wn22_pk_000020_interop_check_for_49`
- `wn22_pk_000030_cceb_interop_check`

---

## rhel8_cis

**Repo:** <https://github.com/ansible-lockdown/RHEL8-CIS>
**Unresolved:** 45 / 764 (5.9%)
**Ambiguous:** 20

### No static definition (44)

- `allow_auditd_uid_user_exclusions`
- `ansible_distribution_major_version`
- `ansible_distribution_version`
- `ansible_env`
- `ansible_interfaces`
- `arch_syscalls`
- `attribute`
- `discovered_auditd_immutable_check`
- `discovered_logfile_list`
- `discovered_logfiles`
- `handler`
- `ld_passwd_regex`
- `ld_passwd_yaml`
- `mount_option_changed_when`
- `mount_point`
- `mount_point_fs_and_options`
- `noqa`
- `reboot_required`
- `required_mount`
- `required_option`
- `rhel8cis_full_crypto_policy`
- `rhel8cis_journal_remote_upload_config_file`
- `rhel8cis_pass`
- `rhel8cis_passwd_complex_option`
- `rhel8cis_passwd_dcredit`
- `rhel8cis_passwd_dictcheck_value`
- `rhel8cis_passwd_difok_value`
- `rhel8cis_passwd_lcredit`
- `rhel8cis_passwd_maxrepeat_value`
- `rhel8cis_passwd_maxsequence_value`
- `rhel8cis_passwd_minclass`
- `rhel8cis_passwd_minlen_value`
- `rhel8cis_passwd_ocredit`
- `rhel8cis_passwd_quality_enforce_root_value`
- `rhel8cis_passwd_quality_enforce_value`
- `rhel8cis_passwd_ucredit`
- `rhel8cis_unowned_group`
- `rpm_gpg_key`
- `rpm_key`
- `rpm_packager`
- `sudo_password_rule`
- `supported_syscalls`
- `syscalls`
- `warn_control_id`

### Dynamic include\_vars (path unknown at scan time) (1)

- `ansible_distribution`

### Ambiguous: Runtime set\_fact (19)

- `audit_pkg_arch_name`
- `control_number`
- `current_crypto_module`
- `current_crypto_policy`
- `discovered_suid_sgid_files_flatten`
- `discovered_unowned_files_flatten`
- `grub2_path`
- `post_audit_results`
- `pre_audit_results`
- `prelim_captured_passwd_data`
- `prelim_interactive_users`
- `prelim_max_int_uid`
- `prelim_min_int_uid`
- `prelim_mount_names`
- `prelim_mount_point_fs_and_options`
- `rhel8cis_boot_path`
- `rhel8cis_flush_ipv4_route`
- `rhel8cis_flush_ipv6_route`
- `root_paths`

### Ambiguous: Other ambiguous (1)

- `change_requires_reboot`

---

## CIS-Ubuntu-20.04-Ansible

**Repo:** <https://github.com/alivx/CIS-Ubuntu-20.04-Ansible>
**Unresolved:** 44 / 159 (27.7%)

### No static definition (44)

- `aide_checksums`
- `aide_exclude_paths`
- `cfile`
- `configFiles`
- `faillock_state`
- `filtered_sgid_executables`
- `filtered_suid_executables`
- `issue`
- `issue_net`
- `kernel_modules_using_usb`
- `motd`
- `os_release`
- `os_version`
- `output_1_7_1_2`
- `output_5_4_1_5`
- `output_6_1_1`
- `output_6_1_10`
- `output_6_1_11`
- `output_6_1_12`
- `output_6_1_13`
- `output_6_1_14`
- `output_6_2_1`
- `output_6_2_11`
- `output_6_2_12`
- `output_6_2_13`
- `output_6_2_14`
- `output_6_2_15`
- `output_6_2_16`
- `output_6_2_2`
- `output_6_2_4`
- `output_6_2_5`
- `output_6_2_5_list`
- `output_6_2_6`
- `output_6_2_7_files`
- `output_6_2_7_folders`
- `output_6_2_8`
- `output_6_2_9`
- `password`
- `postfix`
- `private_keys`
- `public_keys`
- `vartemp`
- `worldWriteableList`
- `xdnx`

---

## cis_ubuntu_2404

**Repo:** <https://github.com/MVladislav/ansible-cis-ubuntu-2404>
**Unresolved:** 43 / 572 (7.5%)
**Ambiguous:** 5

### No static definition (43)

- `AppArmor`
- `NOTE`
- `ansible_managed`
- `be`
- `bug`
- `cis_ubuntu2404_fs_module_file`
- `cis_ubuntu2404_rule_1_1_2_2_2`
- `cis_ubuntu2404_rule_1_1_2_2_3`
- `cis_ubuntu2404_rule_1_1_2_2_4`
- `cis_ubuntu2404_rule_1_1_2_2_shm_size`
- `cis_ubuntu2404_rule_1_1_2_3_2`
- `cis_ubuntu2404_rule_1_1_2_3_3`
- `cis_ubuntu2404_rule_1_1_2_4_2`
- `cis_ubuntu2404_rule_1_1_2_4_3`
- `cis_ubuntu2404_rule_1_1_2_5_2`
- `cis_ubuntu2404_rule_1_1_2_5_3`
- `cis_ubuntu2404_rule_1_1_2_5_4`
- `cis_ubuntu2404_rule_1_1_2_6_2`
- `cis_ubuntu2404_rule_1_1_2_6_3`
- `cis_ubuntu2404_rule_1_1_2_6_4`
- `cis_ubuntu2404_rule_1_1_2_7_2`
- `cis_ubuntu2404_rule_1_1_2_7_3`
- `cis_ubuntu2404_rule_1_1_2_7_4`
- `cis_ubuntu2404_rule_5_1_24_ssh_pub_key`
- `cis_ubuntu2404_single_firewall_check`
- `cis_ubuntu2404_ssh_allow_groups`
- `cis_ubuntu2404_ssh_allow_users`
- `cis_ubuntu2404_ssh_deny_groups`
- `cis_ubuntu2404_ssh_deny_users`
- `cis_ubuntu2404_system_accounts_do_not_have_valid_login_shell_users`
- `error`
- `filename`
- `fixed`
- `for`
- `later`
- `matching_entry`
- `outer_item`
- `parentdir`
- `removed`
- `should`
- `sometimes`
- `this`
- `throws`

### Ambiguous: Runtime set\_fact (5)

- `cis_ubuntu2404_apparmor_update_to_complain_profiles`
- `cis_ubuntu2404_apparmor_update_to_enforce_profiles`
- `cis_ubuntu2404_is_fs_mounted`
- `cis_ubuntu2404_wireless_drivers`
- `tmpfiles_config_file`

---

## nginx

**Repo:** <https://github.com/nginx/ansible-role-nginx>
**Unresolved:** 43 / 123 (35.0%)

### No static definition (43)

- `ansible_managed`
- `ansible_python`
- `bundle`
- `config_check`
- `config_full`
- `jinja2_version`
- `jwt_file`
- `jwt_payload_encoded`
- `keysite`
- `logrotate_check`
- `nginx_agent_api`
- `nginx_agent_app_protect`
- `nginx_agent_config_dirs`
- `nginx_agent_extensions`
- `nginx_agent_features`
- `nginx_agent_instance_group`
- `nginx_agent_queue_size`
- `nginx_agent_server`
- `nginx_agent_tags`
- `nginx_agent_tls`
- `nginx_amplify_agent_config`
- `nginx_distribution_package`
- `nginx_install_source_static_modules`
- `nginx_latest_version`
- `nginx_license_status`
- `nginx_plus_version`
- `nginx_repository`
- `nginx_selinux_module`
- `nginx_selinux_tcp_ports`
- `nginx_selinux_udp_ports`
- `nginx_service_restart`
- `nginx_service_restartonfailure`
- `nginx_service_restartsec`
- `nginx_service_timeoutstartsec`
- `nginx_service_timeoutstopsec`
- `nginx_signing_key`
- `nginx_skip_os_install_config_check`
- `nginx_source`
- `nginx_version`
- `openssl_source`
- `pcre_source`
- `upgrade`
- `zlib_source`

---

## rhel7_stig

**Repo:** <https://github.com/ansible-lockdown/RHEL7-STIG>
**Unresolved:** 42 / 555 (7.6%)
**Ambiguous:** 14

### No static definition (41)

- `aitem`
- `ansible_distribution_major_version`
- `ansible_distribution_version`
- `ansible_env`
- `ansible_hostname`
- `ansible_mounts`
- `ansible_python`
- `append`
- `default_control`
- `dev_shm_mount`
- `dev_shm_mount_opts`
- `find_command_base`
- `gpg_keys`
- `gpg_package`
- `grub_cmdline_linux`
- `handler`
- `ini_item`
- `insert`
- `ld_passwd_regex`
- `ld_passwd_yaml`
- `newline`
- `noexec`
- `noqa`
- `nosuid`
- `old_control`
- `param`
- `rhel07stig_smartcarddriver`
- `rhel7stig_audisp_remote_server`
- `rhel7stig_log_aggregation_port`
- `rhel7stig_log_aggregation_server`
- `rhel7stig_oscap_scan`
- `rhel7stig_passwd_tasks`
- `rhel7stig_postscanresults`
- `rhel7stig_prescanresults`
- `rhel_07_010320_010330_preauth_audit`
- `rhel_07_010330_authfail_audit`
- `rpm_gpg_key`
- `search`
- `sudo_password_rule`
- `this_item`
- `this_result`

### Dynamic include\_vars (path unknown at scan time) (1)

- `ansible_distribution`

### Ambiguous: Runtime set\_fact (14)

- `audit_pkg_arch_name`
- `post_audit_results`
- `pre_audit_results`
- `prelim_local_mount_names`
- `prelim_nfs_mount_names`
- `rhel7stig_bootloader_path`
- `rhel7stig_interactive_uid_start`
- `rhel7stig_interactive_uid_stop`
- `rhel7stig_legacy_boot`
- `rhel7stig_not_boot_path`
- `rhel7stig_passwd`
- `rhel_07_021031_world_writable_files_flat`
- `rhel_07_stig_interactive_homedir_inifiles`
- `rhel_07_stig_interactive_homedir_results`

---

## nomad

**Repo:** <https://github.com/ansible-community/ansible-nomad>
**Unresolved:** 41 / 191 (21.5%)
**Ambiguous:** 2

### No static definition (40)

- `ansible_distribution`
- `ansible_distribution_version`
- `ansible_service_mgr`
- `circonus_broker_id`
- `circonus_broker_select_tag`
- `circonus_check_display_name`
- `circonus_check_force_metric_activation`
- `circonus_check_id`
- `circonus_check_instance_id`
- `circonus_check_search_tag`
- `circonus_check_tags`
- `circonus_submission_interval`
- `circonus_submission_url`
- `nomad_authoritative_region`
- `nomad_autopilot`
- `nomad_config_custom`
- `nomad_network_interface`
- `nomad_node_pool`
- `nomad_os_packages`
- `nomad_telemetry`
- `nomad_telemetry_backwards_compatible_metrics`
- `nomad_telemetry_circonus_api_app`
- `nomad_telemetry_circonus_api_token`
- `nomad_telemetry_circonus_api_url`
- `nomad_telemetry_collection_interval`
- `nomad_telemetry_datadog_address`
- `nomad_telemetry_datadog_tags`
- `nomad_telemetry_disable_dispatched_job_summary_metrics`
- `nomad_telemetry_disable_hostname`
- `nomad_telemetry_disable_tagged_metrics`
- `nomad_telemetry_filter_default`
- `nomad_telemetry_prefix_filter`
- `nomad_telemetry_prometheus_metrics`
- `nomad_telemetry_publish_allocation_metrics`
- `nomad_telemetry_publish_node_metrics`
- `nomad_telemetry_statsd_address`
- `nomad_telemetry_statsite_address`
- `nomad_telemetry_use_node_name`
- `plugin_config`
- `template_config`

### Dynamic include\_vars (path unknown at scan time) (1)

- `ansible_os_family`

### Ambiguous: Runtime set\_fact (2)

- `nomad_encrypt`
- `version_to_compare`

---

## wimpy.deploy

**Repo:** <https://github.com/wimpy/wimpy.deploy>
**Unresolved:** 39 / 100 (39.0%)

### No static definition (39)

- `ansible_date_time`
- `boto_profile`
- `wimpy_after_deploy_tasks_file`
- `wimpy_application_name`
- `wimpy_application_port`
- `wimpy_aws_autoscaling_launch_configuration_user_data`
- `wimpy_aws_autoscaling_previous`
- `wimpy_aws_autoscaling_vpc_subnets`
- `wimpy_aws_cloudformation_facts`
- `wimpy_aws_ebs_optimized`
- `wimpy_aws_elb_security_groups`
- `wimpy_aws_elb_vpc_subnets`
- `wimpy_aws_hosted_zone_name`
- `wimpy_aws_instance_monitoring`
- `wimpy_aws_instance_role`
- `wimpy_aws_keypair`
- `wimpy_aws_lc_security_groups`
- `wimpy_aws_ramdisk_id`
- `wimpy_aws_spot_price`
- `wimpy_aws_volumes`
- `wimpy_before_deploy_tasks_file`
- `wimpy_cloudformation_parameters`
- `wimpy_cloudformation_parameters_with_elb`
- `wimpy_deployment_description`
- `wimpy_deployment_environment`
- `wimpy_deployment_status`
- `wimpy_docker_compose_file_provided`
- `wimpy_docker_image_name`
- `wimpy_docker_login`
- `wimpy_docker_registry`
- `wimpy_docker_registry_email`
- `wimpy_docker_registry_password`
- `wimpy_docker_registry_username`
- `wimpy_github_deployment_out`
- `wimpy_github_token`
- `wimpy_old_launch_configurations`
- `wimpy_previous_cf`
- `wimpy_release_version`
- `wimpy_rollback_to_launchconfiguration`

---

_Report generated from batch 15 scan snapshots. Individual variable names
reflect scanner output at scan time; roles may have changed since._
