// API Management — production-only secure gateway in front of Container Apps
param workloadName string
param environmentName string
param location string
param tags object
@description('Publisher email for APIM (required).')
param publisherEmail string = 'platform@example.com'
@description('Publisher organization for APIM.')
param publisherName string = 'Foundry Workload Studio'

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: take('apim-${workloadName}-${environmentName}-${uniqueString(resourceGroup().id)}', 50)
  location: location
  tags: tags
  sku: { name: 'Developer', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
}

output apimName string = apim.name
output apimGatewayUrl string = apim.properties.gatewayUrl
