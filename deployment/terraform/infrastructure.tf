terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "West Europe"
}

variable "resource_group_name" {
  type    = string
  default = "rg-healthsphere"
}

variable "postgres_admin_username" {
  type    = string
  default = "healthsphereadmin"
}

variable "postgres_admin_password" {
  type      = string
  sensitive = true
}

variable "postgres_sku_name" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "redis_sku_name" {
  type    = string
  default = "Basic"
}

variable "redis_capacity" {
  type    = number
  default = 0
}

variable "storage_account_tier" {
  type    = string
  default = "Standard"
}

variable "storage_replication_type" {
  type    = string
  default = "LRS"
}

module "healthsphere" {
  source                   = "./modules/healthsphere"
  location                 = var.location
  resource_group_name      = var.resource_group_name
  postgres_admin_username  = var.postgres_admin_username
  postgres_admin_password  = var.postgres_admin_password
  postgres_sku_name        = var.postgres_sku_name
  redis_sku_name           = var.redis_sku_name
  redis_capacity           = var.redis_capacity
  storage_account_tier     = var.storage_account_tier
  storage_replication_type = var.storage_replication_type
}

output "acr_login_server" {
  value = module.healthsphere.acr_login_server
}

output "aks_cluster_name" {
  value = module.healthsphere.aks_cluster_name
}

output "postgres_fqdn" {
  value = module.healthsphere.postgres_fqdn
}

output "redis_hostname" {
  value = module.healthsphere.redis_hostname
}

output "storage_account_name" {
  value = module.healthsphere.storage_account_name
}
