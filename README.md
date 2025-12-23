# 🕵️ Steam Ban Monitor Bot

Um bot para Discord desenvolvido em Python que monitora conversas para identificar perfis da Steam banidos (VAC ou Game Ban). O bot verifica links compartilhados em tempo real e também realiza varreduras periódicas no histórico do chat.

## 🚀 Funcionalidades

- **Monitoramento em Tempo Real:** Verifica instantaneamente qualquer link da Steam (`steamcommunity.com`) enviado no canal monitorado.
- **Web Scraping Direto:** Utiliza `lxml` e `requests` para analisar a página pública do perfil, sem necessidade da API Key da Steam.
- **Detecção de Banimentos:** Identifica:
  - VAC Bans (Valve Anti-Cheat).
  - Game Bans (Banimentos de desenvolvedores).
  - Data do banimento (calculada com base nos dias decorridos).
- **Varredura Periódica (Loop):** A cada 10 minutos, re-analisa as últimas 100 mensagens para garantir que nada passou despercebido.
- **Persistência de Dados:** Salva perfis já detectados em um banco de dados local (`historico_bans.json`) para evitar alertas repetidos.
- **Alertas Visuais:** Envia um Embed organizado no canal de saída com foto, nome, tipo de ban e link do perfil.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **[Discord.py](https://discordpy.readthedocs.io/):** Interação com a API do Discord.
- **Requests & LXML:** Para requisições HTTP e parsing de HTML (Web Scraping via XPath).
- **JSON:** Armazenamento local leve de histórico.
- **Asyncio:** Para gerenciamento de tarefas assíncronas e loops de verificação.