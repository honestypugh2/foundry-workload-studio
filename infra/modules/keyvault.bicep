// Key Vault — RBAC mode, soft delete, purge protection in prod (WAF: Security)
param workloadName string
param environmentName string
param location string
param tags object
param principalId string = ''

var kvName = take('kv-${workloadName}-${environmentName}-${uniqueString(resourceGroup().id)}', 24)
var purgeProtection = environmentName == 'prod'

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: environmentName == 'prod' ? 90 : 7
    enablePurgeProtection: purgeProtection ? true : null
    publicNetworkAccess: 'Enabled'
  }
}

// Key Vault Secrets User role for the deploying principal (data plane access)
resource kvUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(kv.id, principalId, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: kv
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalType: 'User'
  }
}

output vaultUri string = kv.properties.vaultUri
output vaultName string = kv.name
