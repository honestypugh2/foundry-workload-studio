// =============================================================================
// Foundry Workload Studio — Main Bicep
// Aligns to Azure Well-Architected Framework: Security (managed identities,
// Key Vault refs, no inline secrets), Reliability (zone-redundant where
// supported), Cost (env-driven SKUs), Operational Excellence (Application
// Insights + Log Analytics), Performance (configurable scale).
// =============================================================================
targetScope = 'subscription'

@description('Workload name; used to compose resource names.')
@maxLength(20)
param workloadName string = 'foundryucf'

@description('Deployment environment.')
@allowed([
  'dev'
  'demo'
  'prod'
])
param environmentName string

@description('Azure region for all resources.')
param location string = 'eastus2'

@description('Object ID of the principal granted data-plane access (e.g., your dev account or CI SP).')
param principalId string = ''

@description('Tags applied to every resource.')
param tags object = {
  workload: 'foundry-workload-studio'
  environment: environmentName
  managedBy: 'bicep'
}

// -----------------------------------------------------------------------------
// Per-service deploy switches.
//
// Defaults follow the principle of least cost: only what each environment
// actually needs is provisioned. The empty defaults below resolve via the
// `deploy*` vars to environment-driven booleans; env-specific .bicepparam
// files can override any of them.
//
//   monitoring | keyvault | storage | search | foundry  → always
//   containerApps                                       → demo + prod
//   cosmos                                              → demo + prod (opt-in persistence)
//   apim                                                → prod
// -----------------------------------------------------------------------------

@description('Deploy Azure Container Apps environment. Default: off in dev (run locally), on in demo/prod.')
param deployContainerApps bool = environmentName != 'dev'

@description('Deploy Azure Cosmos DB. Default: off in dev (no persistence required), on in demo/prod.')
param deployCosmos bool = environmentName != 'dev'

@description('Deploy Azure API Management. Default: prod only.')
param deployApim bool = environmentName == 'prod'

var resourceGroupName = 'rg-${workloadName}-${environmentName}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    principalId: principalId
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    principalId: principalId
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    principalId: principalId
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    principalId: principalId
    foundryAccountPrincipalId: foundry.outputs.accountPrincipalId
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    principalId: principalId
    foundryAccountPrincipalId: foundry.outputs.accountPrincipalId
  }
}

module cosmos 'modules/cosmos.bicep' = if (deployCosmos) {
  name: 'cosmos'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
  }
}

module containerApps 'modules/containerapps.bicep' = if (deployContainerApps) {
  name: 'containerApps'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

module apim 'modules/apim.bicep' = if (deployApim) {
  name: 'apim'
  scope: rg
  params: {
    workloadName: workloadName
    environmentName: environmentName
    location: location
    tags: tags
  }
}

output resourceGroupName string = rg.name
output foundryProjectEndpoint string = foundry.outputs.projectEndpoint
output searchEndpoint string = search.outputs.endpoint
output keyVaultUri string = keyvault.outputs.vaultUri
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output cosmosEndpoint string = cosmos.?outputs.endpoint ?? ''
output containerAppsEnvironmentId string = containerApps.?outputs.environmentId ?? ''
output apimGatewayUrl string = apim.?outputs.apimGatewayUrl ?? ''
