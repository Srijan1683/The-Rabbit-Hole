# Kubernetes deployment

Requires the kind cluster from infra/terraform and a .env file

    IMAGE_TAG=<commit sha> ./k8s/deploy.sh
    kubectl --context kind-rabbit-hole -n rabbit-hole port-forward svc/app 8000:8000
    curl localhost:8000/health

## CI

.github/workflows/k8s-deploy.yml creates a throwaway kind cluster with Terraform, builds the PR's image, deploys with deploy.sh, smoke tests /health and the database scheme, then destroys the cluster.