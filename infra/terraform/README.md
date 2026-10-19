# Local Kubernetes Cluster

Creates a kind cluster and an app namespace.

Requirements: Docker Desktop, terraform, kind, kubectl.

        terraform init
        terraform apply
        kubectl --context kind-rabbit-hole get nodes

Tear down with 'terraform destroy'.