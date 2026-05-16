# SYNTAX ERROR: Missing closing quote in resource type
resource "aws_instance" web_server {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "error-instance
  }
}

# TYPE ERROR: instance_type expects string, providing number
resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-data-bucket"
  
  versioning {
    enabled = "true"  # Should be boolean, not string
  }
}

# SYNTAX ERROR: Unmatched braces
resource "aws_security_group" "web_sg" {
  name = "web-sg"
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  
  # Missing closing brace
