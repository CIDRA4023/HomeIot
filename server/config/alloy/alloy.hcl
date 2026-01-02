local.file_match "varlog" {
  path_targets = [
    { __path__ = "/var/log/*.log", job = "varlog" },
  ]
}

loki.source.file "read_varlog" {
  targets    = local.file_match.varlog.targets
  forward_to = [loki.write.to_loki.receiver]
}

discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
}

discovery.relabel "docker_logs" {
  targets = []
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_service"]
    regex         = "(app|mqtt|influxdb|grafana|cloudflared)"
    action        = "keep"
  }
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_service"]
    regex         = "(.*)"
    target_label  = "container"
    action        = "replace"
  }
  rule {
    target_label = "job"
    replacement  = "docker"
    action       = "replace"
  }
}

loki.source.docker "read_containers" {
  host          = "unix:///var/run/docker.sock"
  targets       = discovery.docker.containers.targets
  relabel_rules = discovery.relabel.docker_logs.rules
  forward_to    = [loki.write.to_loki.receiver]
}

loki.write "to_loki" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
