targetScope = 'resourceGroup'

@description('Name of the deployment environment')
param environmentName string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('PostgreSQL admin username')
param postgresAdminUsername string = 'botbotadmin'

@description('PostgreSQL admin password')
@secure()
param postgresAdminPassword string

@description('JWT signing key used by the backend')
@secure()
param jwtSecretKey string

@description('API title exposed by backend configuration')
param apiTitle string = 'Swing Trade Bot API'

@description('API version exposed by backend configuration')
param apiVersion string = '0.1.0'

@description('JWT algorithm used by backend authentication')
param jwtAlgorithm string = 'HS256'

@description('JWT expiration in minutes')
param jwtExpireMinutes string = '120'

@description('JWT refresh expiration in minutes')
param jwtRefreshExpireMinutes string = '10080'

@description('Market stream polling interval in seconds')
param marketStreamIntervalSeconds string = '2.0'

@description('Bot automation interval in seconds')
param botAutomationIntervalSeconds string = '60.0'

@description('Container CPU allocation')
param containerCpu string = '0.5'

@description('Container memory allocation')
param containerMemory string = '1Gi'

var resourceToken = uniqueString(subscription().id, resourceGroup().id, location, environmentName)
var tags = {
  environment: environmentName
  managedBy: 'azd'
}

var acrName = toLower('azacr${resourceToken}')
var managedIdentityName = toLower('azid${resourceToken}')
var logAnalyticsName = toLower('azlaw${resourceToken}')
var containerEnvName = toLower('azcae${resourceToken}')
var containerAppName = toLower('azcap${resourceToken}')
var appInsightsName = toLower('azapi${resourceToken}')
var keyVaultName = toLower('azkv${substring(resourceToken, 0, 18)}')
var postgresServerName = toLower('azpgs${resourceToken}')

var postgresHost = '${postgresServerName}.postgres.database.azure.com'
var postgresConnectionString = 'postgresql+psycopg://${postgresAdminUsername}:${postgresAdminPassword}@${postgresHost}:5432/swingbot?sslmode=require'

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: tags
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      searchVersion: 1
      legacy: 0
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
  tags: tags
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
  tags: tags
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: false
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: managedIdentity.properties.principalId
        permissions: {
          secrets: [
            'Get'
          ]
        }
      }
    ]
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminUsername
    administratorLoginPassword: postgresAdminPassword
    availabilityZone: '1'
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
  }
  tags: tags
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  name: 'swingbot'
  parent: postgresServer
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  name: 'AllowAzureServices'
  parent: postgresServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'database-url'
  parent: keyVault
  properties: {
    value: postgresConnectionString
  }
}

resource jwtSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'jwt-secret-key'
  parent: keyVault
  properties: {
    value: jwtSecretKey
  }
}

resource managedEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: listKeys(logAnalytics.id, '2022-10-01').primarySharedKey
      }
    }
  }
  tags: tags
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  tags: union(tags, {
    'azd-service-name': 'backend'
  })
  dependsOn: [
    databaseUrlSecret
    jwtSecret
  ]
  properties: {
    managedEnvironmentId: managedEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: listCredentials(containerRegistry.id, containerRegistry.apiVersion).username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: listCredentials(containerRegistry.id, containerRegistry.apiVersion).passwords[0].value
        }
        {
          name: 'database-url'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-url'
          identity: managedIdentity.id
        }
        {
          name: 'jwt-secret-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/jwt-secret-key'
          identity: managedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${containerRegistry.properties.loginServer}/backend:${environmentName}'
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'API_TITLE'
              value: apiTitle
            }
            {
              name: 'API_VERSION'
              value: apiVersion
            }
            {
              name: 'JWT_SECRET_KEY'
              secretRef: 'jwt-secret-key'
            }
            {
              name: 'JWT_ALGORITHM'
              value: jwtAlgorithm
            }
            {
              name: 'JWT_EXPIRE_MINUTES'
              value: jwtExpireMinutes
            }
            {
              name: 'JWT_REFRESH_EXPIRE_MINUTES'
              value: jwtRefreshExpireMinutes
            }
            {
              name: 'MARKET_STREAM_INTERVAL_SECONDS'
              value: marketStreamIntervalSeconds
            }
            {
              name: 'BOT_AUTOMATION_INTERVAL_SECONDS'
              value: botAutomationIntervalSeconds
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

output RESOURCE_GROUP_ID string = resourceGroup().id
output CONTAINER_APP_URL string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output POSTGRES_SERVER_FQDN string = postgresHost
output KEY_VAULT_NAME string = keyVault.name
