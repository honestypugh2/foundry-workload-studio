// Default parameter file consumed by `azd up`. Values are pulled from the
// azd environment so the same template works for dev/demo/prod.
using './main.bicep'

param workloadName = readEnvironmentVariable('AZURE_WORKLOAD_NAME', 'foundryucf')
param environmentName = readEnvironmentVariable('AZURE_DEPLOYMENT_ENV', 'dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')
param tags = {
  workload: 'foundry-workload-studio'
  environment: readEnvironmentVariable('AZURE_DEPLOYMENT_ENV', 'dev')
  managedBy: 'azd'
}
