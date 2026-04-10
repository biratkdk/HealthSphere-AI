variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "postgres_admin_username" {
  type = string
}

variable "postgres_admin_password" {
  type      = string
  sensitive = true
}

variable "postgres_sku_name" {
  type = string
}

variable "redis_sku_name" {
  type = string
}

variable "redis_capacity" {
  type = number
}

variable "storage_account_tier" {
  type = string
}

variable "storage_replication_type" {
  type = string
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  suffix               = lower(random_string.suffix.result)
  acr_name             = "hsacr${local.suffix}"
  storage_account_name = "hsstorage${local.suffix}"
  redis_name           = "hsredis${local.suffix}"
  postgres_name        = "hs-postgres-${local.suffix}"
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "law-healthsphere-${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_registry" "this" {
  name                = local.acr_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "Standard"
  admin_enabled       = false
}

resource "azurerm_storage_account" "this" {
  name                            = local.storage_account_name
  location                        = azurerm_resource_group.this.location
  resource_group_name             = azurerm_resource_group.this.name
  account_tier                    = var.storage_account_tier
  account_replication_type        = var.storage_replication_type
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = true
  allow_nested_items_to_be_public = false
}

resource "azurerm_storage_share" "shared" {
  name               = "healthsphere-shared"
  storage_account_id = azurerm_storage_account.this.id
  quota              = 100
}

resource "azurerm_storage_container" "artifacts" {
  name                  = "artifacts"
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = local.postgres_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  version                       = "16"
  administrator_login           = var.postgres_admin_username
  administrator_password        = var.postgres_admin_password
  sku_name                      = var.postgres_sku_name
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "healthsphere"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_redis_cache" "this" {
  name                = local.redis_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  capacity            = var.redis_capacity
  family              = var.redis_sku_name == "Premium" ? "P" : "C"
  sku_name            = var.redis_sku_name
  minimum_tls_version = "1.2"
  enable_non_ssl_port = false
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = "aks-healthsphere-${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  dns_prefix          = "healthsphere-${local.suffix}"

  default_node_pool {
    name       = "system"
    node_count = 2
    vm_size    = "Standard_D4s_v5"
  }

  identity {
    type = "SystemAssigned"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  }

  role_based_access_control_enabled = true
  oidc_issuer_enabled               = true
  workload_identity_enabled         = true

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.this.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.this.fqdn
}

output "redis_hostname" {
  value = azurerm_redis_cache.this.hostname
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}
