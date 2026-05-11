output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "web_instance_id" {
  description = "Web server instance ID"
  value       = aws_instance.web.id
}

output "web_instance_private_ip" {
  description = "Web server private IP"
  value       = aws_instance.web.private_ip
}

output "security_group_id" {
  description = "Application security group ID"
  value       = aws_security_group.app.id
}
