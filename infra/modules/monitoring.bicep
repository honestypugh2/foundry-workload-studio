// Monitoring: Log Analytics + Application Insights (workspace-based)
// WAF: Operational Excellence
@description('Workload name')
param workloadName string
@description('Environment name')
param environmentName string
param location string
param tags object
@description('Object ID granted Reader on Application Insights (Foundry tracing UI).')
param principalId string = ''

// Monitoring Reader — required to view Application Insights traces in Foundry
// portal per https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
var monitoringReaderRoleId = '43d0d8ad-25c7-4714-9337-8ba259a9fe05'

var lawName = 'log-${workloadName}-${environmentName}'
var aiName = 'appi-${workloadName}-${environmentName}'

var retentionDays = environmentName == 'prod' ? 90 : 30

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: retentionDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output logAnalyticsWorkspaceId string = law.id
output appInsightsConnectionString string = appi.properties.ConnectionString
output appInsightsId string = appi.id

resource appiReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: appi
  name: guid(appi.id, principalId, monitoringReaderRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringReaderRoleId)
    principalType: 'User'
  }
}
