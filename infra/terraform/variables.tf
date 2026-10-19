variable "cluster_name" {
  description = "Name of the kind cluster"
  type        = string
  default     = "rabbit-hole"
}

variable "namespace" {
  description = "Namespace the app will run in"
  type        = string
  default     = "rabbit-hole"
}