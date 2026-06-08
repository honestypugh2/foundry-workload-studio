using '../main.bicep'

param workloadName = 'foundryucf'
param environmentName = 'prod'
param location = 'eastus2'
param principalId = ''
param tags = {
  workload: 'foundry-workload-studio'
  environment: 'prod'
  costCenter: 'ai-platform'
  managedBy: 'bicep'
  dataClassification: 'confidential'
}
