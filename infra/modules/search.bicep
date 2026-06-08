// Azure AI Search (RAG) — env-driven SKU
param workloadName string
param environmentName string
param location string
param tags object

@description('Object ID of the principal granted Search data-plane roles. Empty = skip.')
param principalId string = ''

@description('Object ID of the Foundry account managed identity (read-only access). Empty = skip.')
param foundryAccountPrincipalId string = ''

// AI Search RBAC role IDs.
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
// Search Index Data Reader — for the Foundry account managed identity so
// Foundry connections / agent tools can query indexes (per Foundry RBAC docs:
// "To use a new Azure AI Search source, add Foundry to the Azure AI Search
// role assignments.").
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'

var skuMap = {
  dev: 'basic'
  demo: 'standard'
  prod: 'standard'
}
var replicaMap = {
  dev: 1
  demo: 1
  prod: 3
}
var partitionMap = {
  dev: 1
  demo: 1
  prod: 2
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: take('srch-${workloadName}-${environmentName}-${uniqueString(resourceGroup().id)}', 60)
  location: location
  tags: tags
  sku: { name: skuMap[environmentName] }
  properties: {
    replicaCount: replicaMap[environmentName]
    partitionCount: partitionMap[environmentName]
    publicNetworkAccess: 'enabled'
    semanticSearch: 'standard'
    authOptions: {
      aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' }
    }
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name

resource searchIndexDataContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, searchIndexDataContributorRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalType: 'User'
  }
}

resource searchSvcContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: search
  name: guid(search.id, principalId, searchServiceContributorRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalType: 'User'
  }
}

resource foundrySearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryAccountPrincipalId)) {
  scope: search
  name: guid(search.id, foundryAccountPrincipalId, searchIndexDataReaderRoleId)
  properties: {
    principalId: foundryAccountPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalType: 'ServicePrincipal'
  }
}
