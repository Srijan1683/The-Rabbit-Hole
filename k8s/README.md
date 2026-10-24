# Kubernetes deployment

Requires the kind cluster from infra/terraform and a .env file

    IMAGE_TAG=<commit sha> ./k8s/deploy.sh
    kubectl --context kind-rabbit-hole -n rabbit-hole port-forward svc/app 8000:8000
    curl localhost:8000/health