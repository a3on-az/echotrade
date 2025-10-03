provider "aws" {
  region = "ap-southeast-2"  # Sydney
}

resource "aws_instance" "echotrade_vps" {
  ami           = "ami-0f2f3c6a4b2b6e4e0"  # Latest Amazon Linux 2 ARM (M4 compatible; check latest AMI ID)
  instance_type = "m6i.large"  # M4-like ARM, 2 vCPU, 8GB RAM
  key_name      = "your_ssh_key"  # Upload your key
  vpc_security_group_ids = [aws_security_group.bot_sg.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker
    systemctl start docker
    systemctl enable docker
    usermod -a -G docker ec2-user
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Install Python 3.12
    yum install -y python3 python3-pip git
    
    # Clone and setup (placeholder - adjust to your repo)
    # git clone https://github.com/your-repo/echotrade.git /home/ec2-user/echotrade
    # cd /home/ec2-user/echotrade
    # pip3 install -r requirements.txt
  EOF

  tags = {
    Name = "EchoTradeBot-VPS"
    Environment = "production"
    Project = "echotrade"
  }
}

resource "aws_security_group" "bot_sg" {
  name = "echotrade_sg"
  description = "Security group for EchoTradeBot VPS"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["YOUR_IP/32"]  # Restrict to your IP/office
    description = "SSH access"
  }
  
  ingress {
    from_port   = 8050
    to_port     = 8050
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # For bot UI; restrict later
    description = "Bot main service"
  }
  
  ingress {
    from_port   = 8051
    to_port     = 8051
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Internal only for ML service
    description = "ML service API"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = {
    Name = "echotrade-security-group"
  }
}

resource "aws_eip" "echotrade_ip" {
  instance = aws_instance.echotrade_vps.id
  domain   = "vpc"
  
  tags = {
    Name = "echotrade-elastic-ip"
  }
}

output "public_ip" {
  value = aws_eip.echotrade_ip.public_ip
  description = "Public IP address of the EchoTradeBot VPS"
}

output "private_ip" {
  value = aws_instance.echotrade_vps.private_ip
  description = "Private IP address of the EchoTradeBot VPS"
}

output "ssh_command" {
  value = "ssh -i your_ssh_key.pem ec2-user@${aws_eip.echotrade_ip.public_ip}"
  description = "SSH command to connect to the VPS"
}