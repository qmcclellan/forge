terraform {
  required_providers {
    coder  = { source = "coder/coder" }
    docker = { source = "kreuzwerker/docker" }
  }
}

provider "docker" {}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

# Demonstrates the variable-convention rule (coder-terraform-target-contract-v1.md
# section 4): type/default/description, all three present. starkgrid-frontend itself
# has zero variables and cannot demonstrate this; this example exists to prove the
# rule is satisfiable and checkable, not merely described.
variable "workspace_image" {
  default     = "mcr.microsoft.com/devcontainers/javascript-node:1-20-bullseye"
  description = "Devcontainer image for the provisioned workspace. Pinned to Node 20 here to match the mapped Forge source's declared runtime (node-20) -- see the mapping doc's 'Honest discrepancy' section for why the real starkgrid-frontend target does not do this today."
  type        = string
}

resource "coder_agent" "main" {
  os   = "linux"
  arch = "amd64"

  startup_script = <<-EOT
    set -e
    npm install -g npm@latest || true
    node -v || true
    npm -v || true
  EOT
}

resource "docker_volume" "home_volume" {
  name = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}-home"
}

resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count
  image = var.workspace_image

  name     = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname = data.coder_workspace.me.name

  entrypoint = [
    "sh",
    "-c",
    coder_agent.main.init_script
  ]

  env = [
    "CODER_AGENT_TOKEN=${coder_agent.main.token}",
  ]

  volumes {
    container_path = "/home/node"
    volume_name    = docker_volume.home_volume.name
    read_only      = false
  }
}

module "code-server" {
  source  = "registry.coder.com/coder/code-server/coder"
  version = "1.4.4"

  agent_id = coder_agent.main.id
}
