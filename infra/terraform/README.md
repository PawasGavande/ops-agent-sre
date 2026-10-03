# EKS infrastructure (Terraform)

Creates a VPC (2 AZs, private+public subnets, single NAT) and an EKS cluster with one managed node group.

## Cost warning
Roughly **US$0.15-0.20 per hour** while running: EKS control plane ($0.10/h), one NAT gateway (~$0.045/h + data),
and 2x t3.medium SPOT nodes. **Run `terraform destroy` when you are done.**

## Prerequisites
Terraform >= 1.6, AWS CLI configured (`aws sts get-caller-identity` works), kubectl.

## Use
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # set api_allowed_cidrs to YOUR_IP/32
terraform init
terraform plan
terraform apply                                # ~15 minutes
$(terraform output -raw configure_kubectl)     # point kubectl at the cluster
kubectl get nodes
```

## Tear down
```bash
# remove anything that created AWS load balancers first (e.g. ArgoCD server Service of type LoadBalancer)
terraform destroy
```

## Notes
- State is local by default (git-ignored). Use the commented S3 backend in `versions.tf` for shared state.
- Public API endpoint is restricted by `api_allowed_cidrs`; the default allows everyone, so set it.
