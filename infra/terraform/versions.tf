terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Local state by default. For team use, switch to a remote backend, e.g.:
  # backend "s3" {
  #   bucket         = "<your-state-bucket>"
  #   key            = "opsagent/eks.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "<your-lock-table>"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "opsagent"
      ManagedBy = "terraform"
    }
  }
}
