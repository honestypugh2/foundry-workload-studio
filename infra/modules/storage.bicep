// Storage account for document ingestion (WAF: Security — TLS1.2+, no public blob access)
param workloadName string
param environmentName string
param location string
param tags object

@description('Object ID of the principal granted Storage Blob Data Contributor. Empty = skip.')
param principalId string = ''

@description('Object ID of the Foundry account managed identity (read-only access). Empty = skip.')
param foundryAccountPrincipalId string = ''

// Storage Blob Data Contributor — required because allowSharedKeyAccess=false.
var blobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
// Storage Blob Data Reader — for the Foundry account managed identity, per
// https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry#notes-and-limitations
var blobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

var rawName = toLower(replace('st${workloadName}${environmentName}${uniqueString(resourceGroup().id)}', '-', ''))
var stgName = substring('${rawName}storage', 0, 24)
var sku = environmentName == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'

resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: stgName
  location: location
  tags: tags
  sku: { name: sku }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: stg
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: environmentName == 'prod' ? 30 : 7 }
  }
}

resource docsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'documents'
  properties: { publicAccess: 'None' }
}

output storageAccountName string = stg.name
output storageAccountId string = stg.id

resource blobDataContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: stg
  name: guid(stg.id, principalId, blobDataContributorRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataContributorRoleId)
    principalType: 'User'
  }
}

// Foundry account MI → read-only access to seeded documents.
resource foundryBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryAccountPrincipalId)) {
  scope: stg
  name: guid(stg.id, foundryAccountPrincipalId, blobDataReaderRoleId)
  properties: {
    principalId: foundryAccountPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataReaderRoleId)
    principalType: 'ServicePrincipal'
  }
}
