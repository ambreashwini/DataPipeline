resource "aws_iam_role" "{ROLE_NAME}" {
  name = "{ROLE_NAME}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy_attachment" "{ROLE_NAME}_s3_attach" {
  name       = "{ROLE_NAME}_s3_attach"
  roles      = [aws_iam_role.{ROLE_NAME}.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_policy_attachment" "{ROLE_NAME}_dynamodb_attach" {
  name       = "{ROLE_NAME}_dynamodb_attach"
  roles      = [aws_iam_role.{ROLE_NAME}.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

resource "aws_iam_policy_attachment" "{ROLE_NAME}_lambda_attach" {
  name       = "{ROLE_NAME}_lambda_attach"
  roles      = [aws_iam_role.{ROLE_NAME}.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

provider "aws" {
  region  = "{AWS_REGION}"
  profile = "{AWS_PROFILE}"
}
