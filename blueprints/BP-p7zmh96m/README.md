# Azure Resource Group - Bicep

Creates an Azure resource group by deploying Microsoft's `subscription-deployments/create-rg/main.bicep` quickstart template from the public [Azure/azure-quickstart-templates](https://github.com/Azure/azure-quickstart-templates) repository as a subscription-scoped Azure deployment stack. CloudBolt fetches the template, compiles it with a Bicep CLI it downloads itself, shows a what-if preview, pauses for approval, then deploys. The orderer picks an Environment, a name and a location; an optional second step offers the new resource group in that Environment's Resource Group dropdown for VM orders.

The blueprint is also the starting point for any other Bicep template: duplicate it and repoint the copy (see [Deploying another template](#deploying-another-template)).

## Contents
| Role | ID | Name |
|---|---|---|
| Build (seq 1) | OHK-gqvi9kv4 | Deploy Bicep Template |
| Build (seq 2, optional) | OHK-r1imfgdx | Add Resource Group to Environment |
| Teardown | OHK-vm5p34w3 | Remove Resource Group from Environments |
| Teardown | OHK-t2gs5caq | Teardown Bicep Deployment |
| Day-2 action | RSA-fa7r7cg7 | Update Bicep Deployment |
| Day-2 action | RSA-5jeixn92 | Drift Check |
| Shared module | SHM-eybr4hgz | github |
| Shared module | SHM-bbswv27r | bicep_engine |
| Form | FRM-i9zadhpc | Azure Resource Group - Bicep |

## Prerequisites
- An Azure resource handler with at least one Environment entitled to the ordering groups. The order form shows only the Environment; the handler is derived from it.
- The handler's service principal needs Contributor on the subscription: the stack is subscription-scoped and creates and deletes resource groups (`Microsoft.Resources/subscriptions/resourceGroups/write` and `/delete`, `Microsoft.Resources/deploymentStacks/*`, and `Microsoft.Resources/deployments/*` for what-if).
- No GitHub setup: the quickstart repository is public.

## Setup
1. Confirm the CloudBolt service account can execute a downloaded binary from the engine's cache directory. If it cannot (a `noexec` mount or an SELinux block), every order fails at the compile step. As root on the appliance (the command runs as the owner of the proserv directory):

   ```bash
   su -s /bin/bash "$(stat -c %U /var/opt/cloudbolt/proserv)" -c '
   d=/var/opt/cloudbolt/proserv/bicep/0.44.1 && mkdir -p "$d" &&
   curl -fsSL -o "$d/bicep" https://github.com/Azure/bicep/releases/download/v0.44.1/bicep-linux-x64 &&
   chmod +x "$d/bicep" && "$d/bicep" --version'
   ```

2. Allow outbound HTTPS from the appliance to the Bicep release download (GitHub releases, or your mirror), `api.github.com`, `management.azure.com` and `login.microsoftonline.com`. Behind an SSL-inspecting proxy, upload the proxy's CA in **Admin > SSL Certificates**.
3. Pin the template version. The Ref ships as `master`, which Microsoft can change at any time. Replace it with a commit SHA from the quickstart repository in two places that must stay identical: the **Create Resource Group** build item's Ref parameter default, and the hidden Ref field (`plugin-bdi-zzzup54q.ref`) on the blueprint's **Custom Form** tab.
4. Trim the form's Location dropdown (a fixed list of regions) to the regions your Environments use.
5. Sync the repository, then restart CloudBolt so the shared modules load. Repeat the restart after any sync that changes `SHM-bbswv27r` or `SHM-eybr4hgz`.

Anonymous GitHub requests are limited to 60 an hour per appliance IP. If orders hit that limit, or a template lives in a private repository, add a connection in **Admin > Connection Info**: Name `GitHub` (exactly), Protocol `https`, IP/Hostname `api.github.com`, Port `443`, and a fine-grained, read-only (**Contents**) GitHub token as the Password. Re-enter the token after every repo sync; CloudBolt redacts it on export.

## Deploying another template
Any Bicep template in a GitHub repository can be deployed from a copy of this blueprint; the engine needs no template-specific code. The quickstart repository holds hundreds of templates, one per folder; use a folder that has a `main.bicep` (the engine also accepts an ARM `azuredeploy.json`).

1. **Read the template.** Note its `targetScope` (`resourceGroup` when absent, or `subscription`), each `param` and whether it has a default, any `@secure()` parameters, and its `output` names.
2. **Duplicate the blueprint.** On this blueprint's **Overview** tab, click **Duplicate** and enter the new name. CloudBolt copies the build and teardown items, the day-2 actions and the custom form, and renames the copied form's `plugin-bdi-…` fields to the new build items' IDs. The copy's form does not keep the CSS file; to keep the layout, upload [FRM-i9zadhpc_css.css](../../forms/FRM-i9zadhpc/FRM-i9zadhpc_css.css) under **Presentation Options** on the copy's **Custom Form** tab.
3. **Remove the resource-group steps.** Unless the template creates a resource group, delete the **Add Resource Group to Environment** build item and the **Remove Resource Group from Environments** teardown item, and delete the form's `add_to_environment` checkbox.
4. **Point at the template.** On the copy's **Custom Form** tab, set the default values of the hidden Repository, Template Path and Ref fields (`plugin-bdi-<build item ID>.repo`, `.template_path`, `.ref`), for example `Azure/azure-quickstart-templates`, `quickstarts/<provider>/<template>/main.bicep` and a commit SHA. Set the same three values as the build item's parameter defaults.
5. **Add a resource group for a resource-group-scoped template.** Add a required dropdown named `plugin-bdi-<build item ID>.resource_group` whose options come from the build plugin, filtered by the chosen environment:

   ```json
   {
     "type": "dropdown",
     "name": "plugin-bdi-<build item ID>.resource_group",
     "title": "Resource Group",
     "isRequired": true,
     "choicesByUrl": {
       "url": "/api/v3/cmp/customForms/{custom_form_id}/parameterOptions/plugin-bdi-<build item ID>.resource_group/?group={group}&blueprint={blueprint_id}&service_item=BDI-<build item ID>&inputs={\"env_id\": \"{plugin-bdi-<build item ID>.env_id}\"}",
       "path": "options",
       "allowEmptyResponse": true
     }
   }
   ```

   A subscription-scoped template needs no resource group; it ignores one if given.
6. **Replace the template's inputs.** The Dynamic Panel `plugin-bdi-<build item ID>.parameters` carries the template's parameters. Replace its fields (`rgName`, `rgLocation`) with one field per parameter the orderer should set, named exactly as the Bicep parameter. Turn `@allowed` values into a dropdown, and give object and array parameters a comment field that takes JSON. A parameter left off the form uses the template's default; a parameter with no default must be on the form, or the order fails before anything reaches Azure.
7. **Handle secure parameters outside the panel.** The panel is submitted as plaintext and appears in the job log. For an `@secure()` parameter, add a blueprint parameter of type Password, destination Resource, named exactly as the template parameter, and a `bp-param.<name>` password question on the form. The engine reads it from the resource; it is masked in the job log and not copied to the resource's parameter mirrors.
8. **Name the resource.** The engine names the CloudBolt resource from the first template output called `resourceName`, `resource_name`, `name` or `vmName`; if there is none, from the first of the parameters `rgName`, `resourceGroupName`, `resourceName` or `name`. If the template has neither, add `output resourceName string = <name>` to a copy of it, or extend the lists in the engine settings.
9. **Set the location for a subscription-scoped template.** The stack is created in the region given by the first of the parameters `rgLocation`, `resourceGroupLocation` or `location`, else `eastus`.
10. **Set the resource type.** The copy keeps this blueprint's Azure Resource Group resource type; change it to one that fits what the template deploys.
11. Click **Save Form**, order the copy, and review the what-if preview before approving. To keep the copy in source control, export it to your repository.

## Engine settings
The config block at the top of `shared_modules/SHM-bbswv27r/SHM-bbswv27r_script.py` applies to every Bicep blueprint:

| Setting | Default | Purpose |
|---|---|---|
| `BICEP_VERSION`, `BICEP_SHA256` | `0.44.1` and its checksum | Pinned Bicep CLI. Verify the checksum against Microsoft's release independently of any URL change. |
| `BICEP_DOWNLOAD_URL_TEMPLATE` | GitHub releases | Set an internal mirror for restricted networks. |
| `OUTPUT_ALLOWLIST` | `None` (all non-secure outputs) | Restrict which template outputs are recorded on the resource. |
| `RESOURCE_NAME_OUTPUT_CANDIDATES`, `RESOURCE_NAME_PARAM_CANDIDATES` | see step 8 | The output, or failing that the parameter, that names the resource. |
| `DEFAULT_STACK_LOCATION`, `STACK_LOCATION_PARAM_CANDIDATES` | see step 9 | Region a subscription-scoped stack is created in. |
| `DENY_SETTINGS_MODE` | `none` | Stack deny settings (`denyDelete`, `denyWriteAndDelete`). |

Restart CloudBolt after changing a shared module; running processes keep the old one cached.

## Operation
- **Approval.** Build and Update pause after the what-if preview. Click **Continue Job** on the job to deploy (CloudBolt admins only); cancel the job to reject. Nothing is submitted to Azure before approval. The approval window is the global `job_timeout` preference (default 8 hours); raising it affects every job. If the jobengine restarts while a job is paused, the job is canceled with nothing deployed; order or run the action again.
- **Add Resource Group to Environment.** When ticked, the new resource group is added as a `resource_group_arm` option on the Environment the order used, so VM orders can pick it without a resource handler sync. Unticked, the step does nothing.
- **Teardown.** Deletes the stack and what it manages. For this blueprint that includes the resource group, so Azure refuses (409) if someone has since put other resources in it; the job reports this and never force-deletes. The resource group is also removed from the Resource Group options of every Environment on the same subscription; the shared option value itself is kept.
- **Update and Drift Check.** Drift Check is a read-only what-if and never pauses. Update never edits pinned parameters; do not paste `@secure()` values into its plaintext Parameters (JSON) field.
- **Output visibility.** The what-if summary is job output visible to the group. `@secure()` values are redacted; templates must not echo other secrets in outputs.
- **Large repositories.** Only the template's folder is fetched, plus any `bicepconfig.json` above it, so an order from the quickstart repository transfers kilobytes. A template that references files outside its folder (`../`) makes the engine download the whole repository.
- **Deny settings.** The engine excludes its own service principal from a stack's deny assignment. After rotating the principal to a new object ID, stacks created before the rotation still exclude the old one and can no longer be updated by the engine.
