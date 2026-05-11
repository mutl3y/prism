output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.networking.vpc_cidr
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "app_security_group_id" {
  description = "Application security group ID"
  value       = module.networking.app_security_group_id
}

output "instance_ids" {
  description = "EC2 instance IDs"
  value       = module.compute.instance_ids
}

output "instance_private_ips" {
  description = "EC2 instance private IPs"
  value       = module.compute.instance_private_ips
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.storage.bucket_name
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.storage.bucket_arn
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.database.rds_endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.database.database_name
}
