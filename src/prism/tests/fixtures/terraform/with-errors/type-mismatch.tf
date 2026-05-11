variable "instance_count" {
  type    = number
  default = 2
}

variable "environment" {
  type    = string
  default = "dev"
}

# TYPE MISMATCH: variable expects number, providing string
resource "aws_instances" "web" {
  count         = var.instance_count
  instance_type = var.instance_count  # Should be string, not number!
  ami           = "ami-0c55b159cbfafe1f0"
}

# TYPE MISMATCH: list expected, string provided
resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = "vpc-12345"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = "0.0.0.0/0"  # Should be list ["0.0.0.0/0"], not string
  }
}

# TYPE MISMATCH: boolean expected, string provided
resource "aws_rds_instance" "db" {
  allocated_storage    = 20
  engine               = "mysql"
  instance_class       = "db.t3.micro"
  username             = "admin"
  password             = "changeme"
  publicly_accessible  = "true"  # Should be boolean, not string
  skip_final_snapshot  = yes      # Should be boolean true, not bare yes
}
