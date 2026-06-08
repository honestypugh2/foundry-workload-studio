// Microsoft Foundry account + project (Cognitive Services 'AIServices' kind)
// Provides the unified AI platform endpoint used by Agents SDK and Projects SDK.
param workloadName string
param environmentName string
param location string
param tags object

@description('Object ID of the principal granted Foundry User (data-plane). Empty = skip.')
param principalId string = ''

var accountName = take('aif-${workloadName}-${environmentName}-${uniqueString(resourceGroup().id)}', 60)
var projectName = '${workloadName}-${environmentName}-project'

// Foundry RBAC role IDs (renamed June 2026 — IDs unchanged).
// Source: https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
//   Foundry User             (was Azure AI User)             53ca6127-db72-4b80-b1b0-d745d6d5456d
//   Foundry Project Manager  (was Azure AI Project Manager)  eadc314b-1a2d-4efa-be10-5d325db5065e
//   Foundry Account Owner    (was Azure AI Account Owner)    e47c6f54-e4a2-4754-9501-8e0985b135e1
//   Foundry Owner            (was Azure AI Owner)            c883944f-8b7b-4483-af10-35834be79c4a
// Per docs, do NOT assign roles starting with "Cognitive Services" or
// "Azure AI Developer" for Foundry work.
var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    allowProjectManagement: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: projectName
    description: 'Foundry Workload Studio project for ${environmentName}.'
  }
}

output accountName string = foundry.name
output accountId string = foundry.id
output accountPrincipalId string = foundry.identity.principalId
output projectEndpoint string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${projectName}'
output projectName string = projectName
output projectPrincipalId string = project.identity.principalId

// Grant the supplied principal Foundry User on the Foundry RESOURCE (account)
// scope. Per docs this single assignment covers project access plus data-plane
// calls (agents, model deployments) — preferred over Cognitive Services User.
resource accountFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: foundry
  name: guid(foundry.id, principalId, foundryUserRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalType: 'User'
  }
}

