resource "aws_iam_role" "eng-dev" {
  name = "eng-dev"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy_attachment" "eng-dev_attach" {
  name       = "eng-dev_attach"
  roles      = [aws_iam_role.eng-dev.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

provider "aws" {
  region  = "us-east-1"
  profile = "test2"
}
