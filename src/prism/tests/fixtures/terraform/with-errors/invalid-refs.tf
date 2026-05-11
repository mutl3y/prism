# REFERENCE ERROR: Using undefined variable
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.undefined_instance_type  # This variable doesn't exist!
  
  tags = {
    Name = var.undefined_tag_name  # This variable doesn't exist either!
  }
}

# REFERENCE ERROR: Using undefined resource
resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = aws_vpc.undefined.id  # This resource doesn't exist!
  
  ingress {
    from_port      = 80
    to_port        = 80
    protocol       = "tcp"
    security_groups = [aws_security_group.missing.id]  # Reference to non-existent SG
  }
}

# REFERENCE ERROR: Accessing non-existent output from module
resource "aws_instance" "app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t2.micro"
  subnet_id              = module.networking.undefined_subnet_id  # This output doesn't exist!
  vpc_security_group_ids = [module.network.security_group_id]    # Module name typo
}

# REFERENCE ERROR: Invalid attribute access
resource "aws_rds_instance" "db" {
  allocated_storage = 20
  engine           = "mysql"
  instance_class   = "db.t3.micro"
  username         = "admin"
  password         = aws_secretsmanager_secret.db_password.undefined_attribute  # Invalid attribute
  publicly_accessible = false
}
