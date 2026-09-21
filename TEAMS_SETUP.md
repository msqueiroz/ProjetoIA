# MAR.IA no Microsoft Teams

## Arquitetura do piloto

O processo `teams_bot.py` executa no servidor Windows com acesso à VPN e ao
PI AF SDK. O Teams SDK autentica as mensagens recebidas e a MAR.IA mantém as
consultas ao PI em modo somente leitura.

## Pré-requisitos da TI

- Python 3.11 ou superior e PI AF SDK no servidor da aplicação.
- Node.js 20 ou superior para o Teams Developer CLI.
- Permissão de carregamento de aplicativo personalizado no tenant.
- Aplicativo Single Tenant no Microsoft Entra ID e recurso Azure Bot.
- Rota HTTPS aprovada até `POST /api/messages`.

## Configuração local

1. Instale as dependências:

   `python -m pip install -r requirements.txt`

2. Copie `teams.env.example` para `teams.env`.

3. Preencha `CLIENT_ID`, `CLIENT_SECRET` e `TENANT_ID` fornecidos pela TI.
   O arquivo `teams.env` é ignorado pelo Git e não deve ser compartilhado.

4. Inicie o serviço:

   `python teams_bot.py`

5. Valide localmente:

   `http://127.0.0.1:3978/health`

## Registro e instalação no Teams

Instale o Teams Developer CLI e autentique-se:

`npm install -g @microsoft/teams.cli`

`teams login`

Durante o piloto, a TI deve fornecer um endpoint HTTPS que encaminhe para a
porta local 3978. Registre esse endereço com o sufixo `/api/messages`, instale
o aplicativo gerado no Teams e faça o primeiro teste em conversa pessoal.

## Limites do primeiro piloto

- Base padrão configurada por `PI_AF_DATABASE` (inicialmente ETE).
- Consultas ao PI/AF e SMT são somente leitura.
- Respostas textuais e contexto operacional funcionam no Teams.
- Gráficos detalhados continuam disponíveis na aplicação Streamlit.
- O SSO delegado para consultas documentais pela MAR.IA será a próxima etapa.
