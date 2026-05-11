# SECURITY ISSUE: Hardcoded credentials
resource "aws_db_instance" "prod_db" {
  allocated_storage   = 100
  engine              = "mysql"
  engine_version      = "8.0"
  instance_class      = "db.t3.small"
  username            = "admin"
  password            = "MySuper$ecurePassword123"  # Hardcoded password!
  publicly_accessible = false
  skip_final_snapshot = true
  storage_encrypted   = false  # Not encrypted!
}

# SECURITY ISSUE: Exposed AWS access keys in configuration
resource "aws_s3_bucket" "data" {
  bucket = "my-sensitive-data-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_encryption" {
  bucket = aws_s3_bucket.data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# SECURITY ISSUE: Overly permissive security group
resource "aws_security_group" "allow_all" {
  name        = "allow_all_traffic"
  description = "Allow all inbound and outbound traffic"

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to the world!
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to the world!
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # Unrestricted egress
  }
}

# SECURITY ISSUE: Public S3 bucket
resource "aws_s3_bucket" "public_data" {
  bucket = "publicly-accessible-bucket"
}

resource "aws_s3_bucket_acl" "public_data_acl" {
  bucket = aws_s3_bucket.public_data.id
  acl    = "public-read-write"  # Everyone can read and write!
}

# SECURITY ISSUE: Unencrypted EBS volumes
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  
  root_block_device {
    volume_type = "gp2"
    encrypted   = false  # Unencrypted!
  }
  
  tags = {
    Name = "web-server"
  }
}

# SECURITY ISSUE: Missing IAM restrictions
resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "lambda-policy"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"  # Allows ALL actions!
        Resource = "*"
      }
    ]
  })
}

# SECURITY ISSUE: Exposed RDS instance
resource "aws_db_subnet_group" "default" {
  name = "default-subnet-group"
  subnet_ids = [
    "subnet-12345",
    "subnet-67890"
  ]
}

resource "aws_db_instance" "exposed" {
  allocated_storage      = 20
  engine                 = "postgres"
  instance_class         = "db.t3.micro"
  username               = "postgres"
  password               = "insecure"
  db_subnet_group_name   = aws_db_subnet_group.default.name
  publicly_accessible    = true  # Exposed to internet!
  skip_final_snapshot    = true
}
