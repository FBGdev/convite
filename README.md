# Convite de aniversário

Site de convite com confirmação de presença, banco Supabase e painel privado. O projeto usa um único evento e foi pensado para abrir bem no celular.

## Personalizar a festa

Edite `config.py`: nome, data (`AAAA-MM-DD`), horário, local, endereço, link do Google Maps, coordenadas do mapa, mensagem e chave Pix. A abertura tipográfica e a seção de presentes estão em `templates/invite.html`; as cores e fontes, em `static/style.css`. A variável de ambiente `PIX_KEY` pode substituir a chave definida em `config.py`. Sem chave Pix, apenas essa opção fica oculta; as sugestões de roupas e perfumes continuam visíveis.

Os ícones SVG locais em `static/icons/` são do [Lucide](https://lucide.dev/) e seguem a licença incluída em `static/icons/LICENSE`.

Confira os dados da festa antes de compartilhar o link.

## Configurar o Supabase

O projeto configurado é `qwrgrogsuxjxcuhmkxjj`.

1. As migrações de `supabase/migrations/` já foram aplicadas a esse projeto via MCP do Supabase. Para configurar outro projeto, execute os arquivos em ordem no SQL Editor dele.
2. Em **Settings → API Keys**, crie uma chave **secret** (`sb_secret_...`) exclusiva para este site. Guarde-a somente nas variáveis de ambiente do servidor.
3. Defina `SUPABASE_URL=https://qwrgrogsuxjxcuhmkxjj.supabase.co` e `SUPABASE_SECRET_KEY` no servidor. Não use a chave `publishable` neste backend.

A tabela tem Row Level Security habilitado e não concede acesso aos papéis públicos `anon` e `authenticated`. O navegador envia o formulário apenas ao servidor Flask; só ele usa a chave secreta para ler e gravar respostas.

## Executar localmente

Requer Python 3.11 ou mais recente.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:ADMIN_PASSWORD = "uma-senha-longa-e-exclusiva"
$env:SECRET_KEY = "uma-chave-aleatoria-com-pelo-menos-32-caracteres"
$env:SUPABASE_URL = "https://qwrgrogsuxjxcuhmkxjj.supabase.co"
$env:SUPABASE_SECRET_KEY = "sua-chave-secreta"
.venv\Scripts\python app.py
```

Abra `http://localhost:5000`. O painel fica em `http://localhost:5000/admin`.

## Publicar com Docker

Copie `.env.example` para `.env`, troque `ADMIN_PASSWORD`, `SECRET_KEY` e `SUPABASE_SECRET_KEY`, depois execute:

```powershell
docker compose up --build -d
```

O serviço escuta na porta 8000. Coloque um domínio e um proxy com HTTPS na frente do serviço. `COOKIE_SECURE=1` exige HTTPS para a sessão funcionar. Para testes locais sem HTTPS, use `COOKIE_SECURE=0`.

As respostas ficam no Supabase e continuam disponíveis depois que o contêiner reinicia. Faça backups pelo Supabase conforme a sua política de retenção.

## Como funciona

- Cada telefone com DDD aceita uma resposta por evento. O formato com ou sem `+55` é normalizado.
- Cada resposta registra apenas a pessoa que preenche o formulário; o convite não oferece opção de adicionar acompanhantes.
- O formulário de confirmação abre em uma janela que ocupa a tela no celular; erros de validação reabrem a janela com os dados preenchidos.
- O convite mostra um mapa do salão, um link para a página do local e um botão para traçar a rota pelo Google Maps.
- A chave Pix é opcional e aparece no convite dentro de "Sugestões de presente" quando estiver definida em `config.py` ou em `PIX_KEY`. Qualquer visitante poderá copiá-la ao abrir essa opção.
- Uma resposta repetida com o mesmo telefone é recusada. Se o convidado precisar corrigir a resposta, a organizadora pode excluir o registro no painel para permitir uma nova confirmação.
- O painel mostra os totais, busca por nome, exclui respostas e exporta CSV. A lista nunca é exposta na página pública.
- Defina uma senha forte no servidor. Sem `ADMIN_PASSWORD`, o painel não aceita login. `SECRET_KEY` deve permanecer estável entre reinícios para manter as sessões válidas.

Este projeto não envia mensagens SMS ou WhatsApp e não edita os dados da festa pelo painel.
