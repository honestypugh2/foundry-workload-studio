# Infrastructure (`infra/`)

This folder contains the Bicep templates that provision the Azure resources for Foundry Workload Studio.

It is designed to be driven either directly by the `az` CLI or by the **Azure Developer CLI (`azd`)** for a one-command, repeatable deployment across `dev`, `demo`, and `prod` environments.

---

## Layout

```
infra/
├── main.bicep                  # Subscription-scope entry point
├── modules/                    # Per-service modules
│   ├── monitoring.bicep        # Log Analytics + Application Insights
│   ├── keyvault.bicep          # Azure Key Vault (RBAC)
│   ├── storage.bicep           # Storage account (documents container)
│   ├── search.bicep            # Azure AI Search (semantic + vector)
│   ├── cosmos.bicep            # Cosmos DB (conversation history)
│   ├── foundry.bicep           # Microsoft Foundry account + project
│   ├── containerapps.bicep     # Container Apps managed environment
│   └── apim.bicep              # API Management (prod only)
└── environments/
    ├── dev.bicepparam
    ├── demo.bicepparam
    └── prod.bicepparam
```

`main.bicep` targets `subscription` scope, creates `rg-foundryucf-<env>`, and deploys every module into it. Module SKUs and redundancy options are environment-driven (e.g. `Standard_LRS` in dev → `Standard_ZRS` in prod, AI Search `basic` → `standard` with replicas, Cosmos `Serverless` in dev → provisioned + continuous backup in prod).

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Azure CLI | ≥ 2.60 | <https://learn.microsoft.com/cli/azure/install-azure-cli> |
| Bicep | ≥ 0.30 | `az bicep install` (or `az bicep upgrade`) |
| Azure Developer CLI | ≥ 1.10 | `curl -fsSL https://aka.ms/install-azd.sh \| bash` |

Then sign in:

```bash
az login
az account set --subscription <SUBSCRIPTION_ID>
azd auth login
```

You will need permission to **create resource groups** at the subscription scope and to **assign RBAC roles** (the deployment grants the supplied `principalId` `Key Vault Secrets User` on the vault).

---

## Quick start with `azd`

> The repo already contains [`azure.yaml`](../azure.yaml) at the workspace root pointing at this `infra/` folder. If you do not see it, see [Bootstrapping `azure.yaml`](#bootstrapping-azureyaml) below.

```bash
# 1. Initialise an azd environment (one per target: dev / demo / prod)
azd env new dev

# 2. Set required parameters
azd env set AZURE_LOCATION         eastus2
azd env set AZURE_ENV_NAME         dev          # maps to environmentName
azd env set AZURE_PRINCIPAL_ID     "$(az ad signed-in-user show --query id -o tsv)"

# 3. Provision all Azure resources
azd provision

# 4. (Later) tear it all down
azd down --purge --force
```

`azd provision` runs `main.bicep` at subscription scope using the matching `infra/environments/<env>.bicepparam` file, then writes every Bicep `output` (Foundry project endpoint, Search endpoint, Key Vault URI, App Insights connection string, etc.) back into the `azd` environment so the Python apps can read them via `azd env get-values`.

To add another target environment, just `azd env new demo` or `azd env new prod` and rerun `azd provision`.

---

## Direct Bicep / `az` deployment (no azd)

Useful for CI pipelines or quick what-if checks.

```bash
# What-if (no changes applied)
az deployment sub what-if \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters infra/environments/dev.bicepparam \
  --parameters principalId="$(az ad signed-in-user show --query id -o tsv)"

# Apply
az deployment sub create \
  --name foundryucf-dev-$(date +%Y%m%d%H%M) \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters infra/environments/dev.bicepparam \
  --parameters principalId="$(az ad signed-in-user show --query id -o tsv)"
```

Swap `dev.bicepparam` for `demo.bicepparam` or `prod.bicepparam` to target other environments.

To compile only:

```bash
az bicep build --file infra/main.bicep
```

---

## Parameters

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `workloadName`     | no  | `foundryucf` | ≤ 20 chars; used in resource names. |
| `environmentName`  | yes | —            | One of `dev`, `demo`, `prod`. Drives SKUs and which services deploy. |
| `location`         | no  | `eastus2`    | Azure region. |
| `principalId`      | no  | `''`         | Object ID of the developer / CI service principal that needs data-plane access. Leave blank to skip the Key Vault role assignment. |
| `tags`             | no  | `{ ... }`    | Tags applied to every resource. |
| `deployContainerApps` | no | `environmentName != 'dev'` | Provision the Container Apps managed environment. Off in dev (run apps locally). |
| `deployCosmos`     | no  | `environmentName != 'dev'` | Provision Cosmos DB. Off in dev. Reserved for conversation/triage history persistence (see note below). |
| `deployApim`       | no  | `environmentName == 'prod'` | Provision API Management. Prod only by default. |

### Why Cosmos DB?

Cosmos DB is reserved as the persistence layer for two future capabilities:

- **Conversation memory** for the HR and Clinical RAG assistants (per-session
  history keyed by `sessionId`).
- **Triage history** for the Quality Complaint Triage workflow (audit log of
  decisions, severity, and routing).

The current agents are stateless and **do not write to Cosmos** — so it is
**off by default in `dev`**, where the Python apps run locally and don't need
persistence. Demo and prod environments still provision it so the dataplane is
ready when the persistence wiring is added.

If you don't need Cosmos at all, override the flag:

```bash
az deployment sub create \
  --template-file infra/main.bicep \
  --parameters infra/environments/demo.bicepparam \
  --parameters deployCosmos=false
```

or (with `azd`):

```bash
azd env set DEPLOY_COSMOS false   # then map it in azure.yaml infra.parameters
```

---

## Outputs

`main.bicep` emits the values the application needs at runtime:

| Output | Maps to env var |
|--------|-----------------|
| `resourceGroupName`            | `AZURE_RESOURCE_GROUP` |
| `foundryProjectEndpoint`       | `FOUNDRY_PROJECT_ENDPOINT` |
| `searchEndpoint`               | `AZURE_SEARCH_ENDPOINT` |
| `keyVaultUri`                  | `AZURE_KEYVAULT_URI` |
| `appInsightsConnectionString`  | `APPLICATIONINSIGHTS_CONNECTION_STRING` |

After `azd provision`, hydrate a local `.env` for the Python apps:

```bash
azd env get-values > .env
```

---

## Environment differences (WAF alignment)

What gets provisioned per environment:

| Service | dev | demo | prod |
|---------|:---:|:----:|:----:|
| Log Analytics + App Insights | ✅ | ✅ | ✅ |
| Key Vault                    | ✅ | ✅ | ✅ |
| Storage (documents)          | ✅ | ✅ | ✅ |
| Azure AI Search              | ✅ | ✅ | ✅ |
| Microsoft Foundry            | ✅ | ✅ | ✅ |
| Container Apps env           | ❌ | ✅ | ✅ |
| Cosmos DB                    | ❌ | ✅ | ✅ |
| API Management               | ❌ | ❌ | ✅ |

SKU and reliability tuning per environment:

| Pillar | dev | demo | prod |
|--------|-----|------|------|
| Storage redundancy        | `Standard_LRS` | `Standard_LRS` | `Standard_ZRS` |
| AI Search SKU / replicas  | `basic` × 1     | `standard` × 1 | `standard` × 3 (2 partitions) |
| Cosmos                    | _not deployed_  | Provisioned    | Provisioned + continuous backup, zone-redundant |
| Container Apps env        | _not deployed_  | Consumption    | Consumption + zone-redundant |
| Key Vault purge protection| off             | off            | on |
| API Management            | _not deployed_  | _not deployed_ | Developer SKU (gateway) |

---

## Bootstrapping `azure.yaml`

If the repo root is missing `azure.yaml`, create it once:

```yaml
# azure.yaml
name: foundry-workload-studio
metadata:
  template: foundry-workload-studio@1.0.0
infra:
  provider: bicep
  path: infra
  module: main
```

`azd` will then resolve parameters from `infra/environments/<AZURE_ENV_NAME>.bicepparam` automatically.

---

## Troubleshooting

- **`Could not find a part of the path '.../modules/<x>.bicep'`** — stale Bicep language-server cache in VS Code. Run *Bicep: Restart Language Server* or reload the window. `az bicep build infra/main.bicep` is the source of truth.
- **`InvalidTemplateDeployment: principalId is empty`** — pass `--parameters principalId=<oid>` or `azd env set AZURE_PRINCIPAL_ID <oid>`.
- **Key Vault name collision** — names include `uniqueString(rg.id)`; if you redeploy after `azd down` without `--purge`, the soft-deleted vault blocks the new one. Use `azd down --purge` or `az keyvault purge -n <name>`.
- **Foundry account quota** — `AIServices` accounts are regional; if `eastus2` is full, set `AZURE_LOCATION` to another supported region (`eastus`, `westus3`, `swedencentral`).
