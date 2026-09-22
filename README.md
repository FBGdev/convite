# Convite de aniversário

Site de convite com confirmação de presença, SQLite e painel privado. O projeto usa um único evento e foi pensado para abrir bem no celular.

## Personalizar a festa

Edite `config.py`: nome, data (`AAAA-MM-DD`), horário, local, endereço, mensagem e regras de acompanhantes. A arte está em `static/birthday-art.svg`; as cores e fontes, em `static/style.css`.

Os valores fornecidos são **exemplos**. Substitua tudo antes de compartilhar o link.

## Executar localmente

Requer Python 3.11 ou mais recente.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:ADMIN_PASSWORD = "uma-senha-longa-e-exclusiva"
$env:SECRET_KEY = "uma-chave-aleatoria-com-pelo-menos-32-caracteres"
.venv\Scripts\python app.py
```

Abra `http://localhost:5000`. O painel fica em `http://localhost:5000/admin`.

## Publicar com Docker

Copie `.env.example` para `.env`, troque `ADMIN_PASSWORD` e `SECRET_KEY`, depois execute:

```powershell
docker compose up --build -d
```

O serviço escuta na porta 8000. Coloque um domínio e um proxy com HTTPS na frente do serviço. `COOKIE_SECURE=1` exige HTTPS para a sessão funcionar. Para testes locais sem HTTPS, use `COOKIE_SECURE=0`.

O volume `respostas` guarda o banco SQLite entre reinícios e atualizações do contêiner. Faça backup desse volume antes de mudanças na hospedagem. Em outras plataformas, configure `DATABASE_PATH` para um disco persistente; um sistema de arquivos temporário perde as respostas após reinício.

## Como funciona

- Cada telefone com DDD aceita uma resposta por evento. O formato com ou sem `+55` é normalizado.
- Uma resposta repetida pede o código de edição exibido na primeira confirmação. O código é mostrado só uma vez e o banco armazena apenas seu hash. Se for perdido, a organizadora pode excluir o registro no painel para permitir uma nova resposta.
- O painel mostra os totais, busca por nome, exclui respostas e exporta CSV. A lista nunca é exposta na página pública.
- Defina uma senha forte no servidor. Sem `ADMIN_PASSWORD`, o painel não aceita login. `SECRET_KEY` deve permanecer estável entre reinícios para manter as sessões válidas.

Este projeto não envia mensagens SMS ou WhatsApp e não edita os dados da festa pelo painel.
