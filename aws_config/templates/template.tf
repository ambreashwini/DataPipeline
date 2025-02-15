resource "aws_iam_role" "{ROLE_NAME}" {
  name = "{ROLE_NAME}"

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

resource "aws_iam_policy_attachment" "{ROLE_NAME}_attach" {
  name       = "{ROLE_NAME}_attach"
  roles      = [aws_iam_role.{ROLE_NAME}.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

provider "aws" {
  region  = "{AWS_REGION}"
  profile = "{AWS_PROFILE}"
}
