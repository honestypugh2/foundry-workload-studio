using '../main.bicep'

param workloadName = 'foundryucf'
param environmentName = 'dev'
param location = 'eastus2'
param principalId = ''
param tags = {
  workload: 'foundry-workload-studio'
  environment: 'dev'
  costCenter: 'ai-platform'
  managedBy: 'bicep'
}
