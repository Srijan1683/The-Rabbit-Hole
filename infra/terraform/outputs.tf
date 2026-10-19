output "cluster_name" {
  value = kind_cluster.this.name
}

output "kubectl_context" {
  value = "kind-${kind_cluster.this.name}"
}

output "namespace" {
  value = kubernetes_namespace_v1.app.metadata[0].name
}