// Cosmos DB — conversation/session persistence
param workloadName string
param environmentName string
param location string
param tags object

var accountName = take(toLower('cosmos-${workloadName}-${environmentName}-${uniqueString(resourceGroup().id)}'), 44)
var dbName = 'foundry-workload-studio'

var backupPolicy = environmentName == 'prod' ? {
  type: 'Continuous'
  continuousModeProperties: { tier: 'Continuous7Days' }
} : {
  type: 'Periodic'
  periodicModeProperties: {
    backupIntervalInMinutes: 240
    backupRetentionIntervalInHours: 24
    backupStorageRedundancy: 'Local'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [
      { locationName: location, failoverPriority: 0, isZoneRedundant: environmentName == 'prod' }
    ]
    capabilities: environmentName == 'dev' ? [{ name: 'EnableServerless' }] : []
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    backupPolicy: backupPolicy
  }
}

resource db 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmos
  name: dbName
  properties: { resource: { id: dbName } }
}

resource conversationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: db
  name: 'conversations'
  properties: {
    resource: {
      id: 'conversations'
      partitionKey: { paths: ['/sessionId'], kind: 'Hash' }
      defaultTtl: 60 * 60 * 24 * 30
    }
  }
}

output endpoint string = cosmos.properties.documentEndpoint
output accountName string = cosmos.name
output databaseName string = dbName
