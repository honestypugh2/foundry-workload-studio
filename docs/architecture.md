# Architecture

Foundry Workload Studio is an opinionated multi-workload accelerator built on Microsoft Foundry, Microsoft Agent Framework, and Azure AI Search.

```mermaid
flowchart LR
    subgraph Clients
        U[User / Field Engineer / Clinician / HR]
    end

    subgraph Edge
        APIM[API Management<br/>(prod only)]
    end

    subgraph Apps[Container Apps]
        HR[HR Policy Assistant]
        CL[Clinical Laser Assistant]
        QC[Quality Complaint Triage]
        MC[Maintenance Copilot]
    end

    subgraph AI[Microsoft Foundry]
        F[Foundry Project<br/>+ Agents]
        M[(gpt-4o-mini)]
        E[(text-embedding-3-small)]
    end

    subgraph Data[Data Plane]
        S[Azure AI Search]
        C[(Cosmos DB)]
        ST[(Blob Storage)]
        KV[(Key Vault)]
    end

    subgraph Obs[Observability]
        LA[Log Analytics]
        AI2[App Insights]
    end

    U --> APIM --> HR
    U --> APIM --> CL
    U --> APIM --> QC
    U --> APIM --> MC

    HR --> F
    CL --> F
    QC --> F
    MC --> F

    F --> M
    F --> E

    HR --> S
    CL --> S
    MC --> S

    HR --> C
    CL --> C
    MC --> C
    QC --> C

    Apps --> AI2
    Apps --> KV
    Apps --> ST
    AI2 --> LA
```

## Use case responsibilities

| Use case | Pattern | Key services |
|---|---|---|
| HR Policy Assistant | Grounded RAG | Foundry, AI Search, Cosmos |
| Clinical Laser Assistant | Grounded RAG + clinical guardrails | Foundry, AI Search |
| Quality Complaint Triage | Structured-output agent (Agent Framework) | Foundry, Cosmos |
| Preventative Maintenance Copilot | Telemetry grounding + RAG | Foundry, AI Search, Storage |

## Environment progression

`dev` → `demo` → `prod` is encoded in `infra/environments/*.bicepparam`. SKU, redundancy, purge protection, ZRS storage, Cosmos continuous backups, and APIM gateway are introduced progressively per the Microsoft Well-Architected Framework.
