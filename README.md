# 🖨️ Sistema Multiagente de IA — Beaver's Choice Paper Company

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Conclu%C3%ADdo-brightgreen)

Solução de Inteligência Artificial baseada em **arquitetura multiagente** desenvolvida para otimizar a gestão de inventário, automatizar cotações dinâmicas com descontos por volume, processar vendas e fornecer inteligência de negócios em tempo real para a **Beaver's Choice Paper Company**.

---

## 📋 Índice

- [Visão Geral do Projeto](#-visão-geral-do-projeto)
- [Arquitetura do Sistema Multiagente](#-arquitetura-do-sistema-multiagente)
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Estrutura do Repositório](#-estrutura-do-repositório)
- [Pré-requisitos e Instalação](#-pré-requisitos-e-instalação)
- [Configuração de Segurança (.env)](#-configuração-de-segurança-env)
- [Como Executar](#-como-executar)
- [Exemplos de Uso e Resultados](#-exemplos-de-uso-e-resultados)
- [Autor](#-autor)

---

## 🎯 Visão Geral do Projeto

Empresas de distribuição de insumos físicos enfrentam gargalos operacionais quando dependem de processos manuais para checar estoques, calcular descontos comerciais e fechar pedidos. Este projeto resolve esse desafio orquestrando **4 agentes especializados** que operam de forma coordenada sobre um banco de dados relacional (`SQLite3`), garantindo:

- **Respostas instantâneas** às consultas de clientes;
- **Precificação competitiva** com análise de histórico e regras progressivas de desconto;
- **Prevenção de ruptura de estoque** com alertas e reabastecimento automático;
- **Transparência total** nas decisões (aprovações e rejeições fundamentadas).

---

## 🏗️ Arquitetura do Sistema Multiagente

O sistema segue o padrão **Orchestrator-Workers** (limitado a 4 agentes ativos para alta coesão e baixa latência), onde cada agente possui responsabilidades estritas e ferramentas dedicadas de acesso ao banco de dados:

```mermaid
graph TD
    subgraph Entrada
        C[Cliente / Requisição de Pedido]
    end

    subgraph Sistema Multiagente
        O[Agente Orquestrador <br/> <i>Gerencia intenções e delega tarefas</i>]
        
        IA[Agente de Inventário <br/> <i>Verifica estoque e reposição</i>]
        QA[Agente de Cotações <br/> <i>Precificação e descontos</i>]
        SA[Agente de Vendas & Finanças <br/> <i>Transações, caixa e relatórios</i>]
    end

    subgraph Persistência & Ferramentas SQLite
        T1[getstocklevel]
        T2[getallinventory]
        T3[getsupplierdeliverydate]
        T4[searchquotehistory]
        T5[createtransaction]
        T6[getcashbalance]
        T7[generatefinancialreport]
    end

    C -->|Envia Solicitação| O
    O -->|1. Consulta Estoque| IA
    O -->|2. Solicita Preço| QA
    O -->|3. Efetiva Venda| SA

    IA --> T1 & T2 & T3
    QA --> T4
    SA --> T5 & T6 & T7

    IA -->|Status e Prazos| O
    QA -->|Cotação Calculada| O
    SA -->|Recibo / Erro| O
    O -->|Resposta Explicável| C
