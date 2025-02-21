resource "aws_iam_role" "eng-dev" {
  name = "eng-dev"

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

resource "aws_iam_policy_attachment" "eng-dev_s3_attach" {
  name       = "eng-dev_s3_attach"
  roles      = [aws_iam_role.eng-dev.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_policy_attachment" "eng-dev_dynamodb_attach" {
  name       = "eng-dev_dynamodb_attach"
  roles      = [aws_iam_role.eng-dev.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

resource "aws_iam_policy_attachment" "eng-dev_lambda_attach" {
  name       = "eng-dev_lambda_attach"
  roles      = [aws_iam_role.eng-dev.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

provider "aws" {
  region  = "us-east-1"
  profile = "test"
}
