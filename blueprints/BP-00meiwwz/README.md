# HCP Terraform No-Code Module

Provisions infrastructure from a pinned HCP Terraform no-code registry module, in a dedicated workspace per deployment. The orderer picks a CloudBolt Environment (its Azure subscription and tenant become the workspace's `ARM_SUBSCRIPTION_ID` / `ARM_TENANT_ID`), names the workspace, and fills the module's variables from dropdowns constrained by that environment. Workspaces are created with Auto Apply on, so HCP Terraform applies each successful plan and the job never pauses for review.

Deployed resources are of type **HCP Terraform Workspace**. The HCP Terraform Workspace extension ([XUI-ax1sluwi](../../extensions/XUI-ax1sluwi/)) adds Terraform and Terraform Variables tabs to them.

## Contents
| Role | ID | Name |
|---|---|---|
| Build | OHK-axtt0yqq | HCP Terraform No-Code Module |
| Teardown | OHK-y9d1uwhw | Teardown HCP Terraform No-Code Module |
| Discovery | OHK-b1n02ula | Discover HCP Terraform No-Code Workspaces |
| Options hook | HPA-swe1kifa | Generate options for HCP Terraform coordinates (hook OHK-529jjzli) |
| Day-2 action | RSA-dxrh4m6j | Update Variables (hook OHK-lvy5tj0y, form FRM-h4py5w3a) |
| Day-2 action | RSA-pngq92ss | Deploy Latest Version (hook OHK-4y8f1vff) |
| Shared module | SHM-jlguerjr | tfc_api |
| Shared module | SHM-r0oq14r7 | env_options |
| Shared module | SHM-9h13o859 | vm_adoption |
| Webhook | IWH-yj93is5z | Form Options (hook OHK-fx500o2r) |
| Form | FRM-1dxfulvq | HCP Terraform No-Code Module order form |
| Sample module | [sample-module/](sample-module/) | Azure VM module the shipped order form is authored for |

## Prerequisites
- An HCP Terraform organization on an edition that includes no-code provisioning (Standard or Premium, not the free tier), used only for CloudBolt deployments.
- A sandbox Azure subscription and a service principal with a role in every subscription your CloudBolt environments point at.
- A Git repository for the module on a VCS host HCP Terraform supports, with admin rights on it.
- CloudBolt Environments on Azure resource handlers, entitled to the ordering groups, with resource groups and subnets imported, VM sizes enabled, and at least one OS build.

## Security
- CloudBolt authenticates with an Owners team token, which has organization-wide rights, and anyone who can author a CloudBolt plugin can read a ConnectionInfo password. Keep nothing else in the organization.
- `terraform plan` runs with the variable set's Azure credentials in its environment, so write access to the module repository is access to those credentials. Restrict collaborators, protect release tags, and back the variable set with a sandbox subscription.
- Every non-sensitive output is recorded on the resource in plaintext, visible to the group. Mark any secret-bearing output `sensitive = true`.

## Setup

### 1. Project and credentials
1. In HCP Terraform, create a project (for example `cloudbolt-deployments`). Create no workspaces in it; CloudBolt creates one per deployment.
2. In **Organization Settings > Variable sets**, create a variable set scoped to that project only, not flagged *priority*, with these **Environment** variables:

   | Key | Value | Sensitive |
   |---|---|---|
   | `ARM_CLIENT_ID` | service principal application (client) ID | yes |
   | `ARM_CLIENT_SECRET` | service principal secret | yes |
   | `ARM_TENANT_ID` | tenant ID | yes |
   | `ARM_SUBSCRIPTION_ID` | a default subscription ID | no |

   CloudBolt writes `ARM_SUBSCRIPTION_ID` and `ARM_TENANT_ID` on each workspace from the chosen environment; a priority set would override them.

### 2. Publish the module
1. Copy [sample-module/](sample-module/) into the root of its own repository, push it, and tag `v1.0.0`.
2. In **Organization Settings > Version Control > Providers**, connect the VCS provider and grant it access to that repository.
3. Open **Registry > Publish > Module**, pick the provider and repository, keep tag-based publishing, tick **Add Module to no-code provision allowlist**, and click **Publish module**.
4. Open the module, click **Configure Settings > Edit versions and variable options**, pick the version, and save. Every deployment provisions that version until you move the pin.

### 3. Token and ConnectionInfo
1. In **Organization Settings > Teams > Owners**, generate a team API token. Organization tokens are rejected by the no-code endpoints.
2. In CloudBolt, open **Admin > Connection Info** and add a connection. Leave the username and headers empty.

   | Field | Value |
   |---|---|
   | Name | `HCP Terraform` |
   | Labels | `tf-cloud` |
   | Protocol | `https` |
   | IP/Hostname | `app.terraform.io` (or your Terraform Enterprise host) |
   | Port | `443` |
   | Password | the team token |

### 4. Pin the coordinates
On the blueprint's **Parameters** tab, click **Add option** on each parameter below, in this order, and pick the value from the list. Each list is filtered by the ones above it.

| Parameter | Value |
|---|---|
| `tfc_connection_info` | the `tf-cloud` ConnectionInfo |
| `tfc_organization` | the organization |
| `tfc_project` | the project from step 1 |
| `tfc_nocode_module_id` | the module from step 2, listed as `name (provider) -- nocode-…` |

A parameter with one option is hidden from the order form and written onto each deployment's resource before the build runs. A repo sync re-creates the options from the metadata, so export the blueprint back to the repo after pinning. The build refuses to run while any coordinate is unpinned.

### 5. Sync and restart
1. Sync the repository, then sync `webhooks/` on its own: a blueprint sync does not refresh the Form Options webhook its form calls.
2. Restart CloudBolt so the shared modules load. Repeat after any sync that changes `tfc_api`.
3. Re-enter the token in every `tf-cloud` ConnectionInfo. CloudBolt redacts it on export, so do this after every sync; until then every HCP Terraform job fails with a 401 naming the connection.

## Sample module
An Azure VM with a NIC on an existing subnet, Linux or Windows. The order form's Module Variables panel uses these names.

| Variable | Form field | Notes |
|---|---|---|
| `vm_name` | VM Name | 1–64 letters, numbers, hyphens; Windows uses the first 15 as computer name |
| `resource_group_name` | Resource Group | Existing; the VM and NIC go here |
| `subnet_id` | Subnet | Full ARM ID; the VM is created in the subnet's VNet region |
| `vm_size` | VM Size | e.g. `Standard_B2s` |
| `admin_username` | Admin Username | Default `azureadmin` |
| `admin_password` | Admin Password | Written to HCP Terraform as sensitive |
| `os_image` | OS Image | `publisher:offer:sku:version` |
| `tags` | Tags | `map(string)` |
| `os_type` | (none) | `auto` (default), `linux` or `windows` |
| `os_disk_storage_account_type` | (none) | Default `Standard_LRS` |

Outputs: `vm_name`, `vm_id`, `private_ip_address`, `location`, `os_type`, and `cloudbolt_vm_ids`, which gives each VM a CloudBolt Server record.

## Using another module
Clone this blueprint, pin its own coordinates, and author a form for the module's variables. No plugin or shared-module change is needed.
- The module must declare its `azurerm` provider itself, with no `subscription_id` and no subscription or tenant variables. Emit `cloudbolt_vm_ids` (a `list(string)` of VM resource IDs) to get Server records.
- Freeze the build plugin's `action_inputs` before authoring: the form hardcodes the `plugin-bdi-<build item ID>` field names.
- In the Module Variables panel, name each field exactly as its Terraform variable. Keep the required `workspace_name` field; it names the workspace and resource and is not sent to Terraform.
- For dropdowns filled from the environment, point `choicesByUrl` at `/api/v3/cmp/inboundWebHooks/form-options/run/?source=<source>&group={group}&env_id={plugin-bdi-<build item ID>.env_id}`, where `<source>` is `resource_group`, `subnet`, `vm_size`, `os_image`, `location` or `cf:<field>`. For options defined on the module in HCP Terraform, use `source=tfc_variable_options&blueprint={blueprint_id}&variable=<name>` (`path: options`, `valueName: value`, `titleName: title`).
- List sensitive variables in the hidden `_sensitive` field, and use a key/value matrix for map variables.
- Keep the form's `rendering_mode: jquery` and its CSS file.

## Operation
- **Provision.** Workspace Name is the HCP Terraform workspace name and the CloudBolt resource name; it must be unique in the organization, and a name in use fails the order before anything is created. The build adopts the workspace's auto-queued first run and follows it to completion; the job log carries the run URL and plan counts. Canceling while the run is queued discards it and leaves the resource failed with its workspace ID stored; once planning has started, HCP Terraform finishes the run. Retrying re-adopts the same workspace.
- **Update Variables.** Opens a form built from the order form, pre-filled with the deployment's values. Unknown and sensitive keys are rejected, a blank field keeps its value, and it fails fast if the workspace has a pending run.
- **Module versions.** To move to a new version, tag and publish it, then pick it under **Configure Settings** on the module. New orders use it at once. Existing deployments show **Update available** on the Terraform tab; **Deploy Latest Version** upgrades them. It is idempotent and can run on several deployments at once; if the new version adds a required variable, the plan fails, so set the variable on the workspace in HCP Terraform and run it again.
- **Servers.** Each ID in `cloudbolt_vm_ids` becomes a child Server of the resource, flagged *Created By Terraform*. Day-2 runs re-adopt from the refreshed outputs; teardown retires the records after the destroy run. CloudBolt never deletes the VMs itself.
- **Teardown.** Fails fast if another CloudBolt job owns the resource; otherwise discards orphaned runs, runs a destroy, and deletes the workspace.
- **Blocked workspace.** A run nobody is waiting on blocks the workspace and makes day-2 actions fail fast. Discard it from the resource's Terraform tab, or in HCP Terraform.
- **Sync Resources.** The discovery plugin lists the organization's workspaces created from the pinned module (any version, any project), refreshes each resource's module version, latest run, outputs and variables, onboards a workspace with no resource into the Unassigned group, and marks a resource Historical when its workspace returns 404. Sensitive values are never read. Keep `auto_historical_resources` off: it would retire deployments that are still provisioning.
- **Resource type label.** A sync never renames an existing resource type. Set the label to "HCP Terraform Workspace" once in **Admin > Resource Types**.
