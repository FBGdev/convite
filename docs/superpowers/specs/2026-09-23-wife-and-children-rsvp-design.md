# Confirmação de presença com esposa e filhos

## Objetivo

Permitir que uma pessoa confirme a própria presença junto com sua esposa e seus filhos, informando o nome de cada um. O convite não oferecerá cadastro de outros acompanhantes.

## Formulário público

- Os campos de familiares aparecem somente quando a pessoa seleciona “Sim, vou!”.
- A pessoa pode marcar “Vou levar minha esposa” e, nesse caso, deve informar o nome dela.
- A pessoa pode adicionar até dois campos para filhos e informar o nome de cada um. É possível remover um campo adicionado antes de enviar.
- O limite é de uma esposa e dois filhos por resposta, além da pessoa que responde.
- Ao selecionar “Não poderei ir”, os campos de familiares são desativados. O servidor também recusa uma resposta negativa que envie familiares.
- Em caso de erro, o formulário reabre com os nomes preenchidos, e a mensagem explica o que precisa ser corrigido.

## Dados e validação

- Uma nova migração adiciona `wife_name` (texto opcional) e `children_names` (lista de textos, inicialmente vazia) à tabela `rsvps`.
- Os campos existentes `companions` e `children` continuam armazenando as quantidades: `companions` será 1 quando houver esposa e 0 caso contrário; `children` será o tamanho de `children_names`.
- O servidor normaliza espaços dos nomes, exige de 2 a 120 caracteres em cada nome e aceita no máximo uma esposa e dois filhos. Ele ignora valores de quantidade enviados pelo navegador e calcula as quantidades a partir dos nomes validados.
- Respostas já existentes permanecem intactas. Como os nomes não foram coletados antes, os novos campos ficam vazios nesses registros; eventuais quantidades antigas continuam preservadas.
- A migração deve ser aplicada no Supabase antes de publicar o código que grava e consulta os novos campos.

## Painel e exportação

- Cada resposta mostra o nome da esposa e os nomes dos filhos, quando existirem.
- A busca por nome também encontra respostas pelo nome de um familiar.
- O painel mantém a contagem de respostas e de recusas; a contagem de presenças passa a somar a pessoa que respondeu e os familiares registrados. Quantidades antigas sem nome, se houver, também entram nessa soma.
- O CSV inclui colunas para esposa, filhos e total de pessoas da resposta. Para os filhos, os nomes são separados por vírgula na mesma célula.
- A confirmação de sucesso informa que a resposta da família foi registrada, sem expor os nomes em uma página pública.

## Verificação

- Testar presença individual, esposa, um ou dois filhos, esposa com filhos, resposta negativa e a recusa de um terceiro filho.
- Testar nomes inválidos, preservação do formulário após erro, números de acompanhantes forjados, duplicidade de telefone, busca no painel, totais e CSV.
- Conferir que registros antigos sem os novos campos ainda são exibidos corretamente.
