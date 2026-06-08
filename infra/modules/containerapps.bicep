// Container Apps environment for hosting use case APIs
param workloadName string
param environmentName string
param location string
param tags object
param logAnalyticsWorkspaceId string
param appInsightsConnectionString string

var envName = 'cae-${workloadName}-${environmentName}'

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: split(logAnalyticsWorkspaceId, '/')[8]
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
    zoneRedundant: environmentName == 'prod'
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output environmentId string = cae.id
output environmentName string = cae.name
#disable-next-line outputs-should-not-contain-secrets
output appInsightsConnectionString string = appInsightsConnectionString
