using '../main.bicep'

param workloadName = 'foundryucf'
param environmentName = 'demo'
param location = 'eastus2'
param principalId = ''
param tags = {
  workload: 'foundry-workload-studio'
  environment: 'demo'
  costCenter: 'ai-platform'
  managedBy: 'bicep'
}
