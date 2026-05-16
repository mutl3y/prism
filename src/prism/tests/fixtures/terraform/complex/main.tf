terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Networking module for VPC and networking resources
module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  tags         = local.common_tags
}

# Compute module for EC2 instances and Auto Scaling Groups
module "compute" {
  source = "./modules/compute"

  project_name           = var.project_name
  environment            = var.environment
  instance_count         = var.instance_count
  instance_type          = var.instance_type
  subnet_ids             = module.networking.private_subnet_ids
  security_group_id      = module.networking.app_security_group_id
  tags                   = local.common_tags
  
  depends_on = [module.networking]
}

# Storage module for S3 buckets and related resources
module "storage" {
  source = "./modules/storage"

  project_name = var.project_name
  environment  = var.environment
  bucket_force_destroy = var.environment == "dev" ? true : false
  tags         = local.common_tags
}

# Database module for RDS instances
module "database" {
  source = "./modules/database"

  project_name              = var.project_name
  environment               = var.environment
  db_instance_class         = var.db_instance_class
  db_allocated_storage      = var.db_allocated_storage
  db_subnet_group_name      = module.networking.db_subnet_group_name
  db_security_group_id      = module.networking.db_security_group_id
  tags                      = local.common_tags
  
  depends_on = [module.networking]
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    CreatedAt   = timestamp()
  }
}
