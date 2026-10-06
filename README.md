# Discord channel mirror

Um serviço Python que encaminha novas mensagens de um canal Discord para outro usando uma aplicação de bot oficial. Ele copia texto, embeds e anexos quando o Discord permite o envio do arquivo. Menções são desativadas na cópia para evitar notificações em massa.

O repositório indicado serviu como referência funcional. O código original usa o token de uma conta pessoal do Discord; esta implementação não reutiliza esse mecanismo. Use somente um token de bot criado no Discord Developer Portal.

## Configuração

1. Crie uma aplicação e um bot no [Discord Developer Portal](https://discord.com/developers/applications).
2. Em **Bot**, habilite **Message Content Intent**. O bot precisa desse intent privilegiado para receber o texto das mensagens.
3. Convide o bot para os dois servidores com permissões de ver canais, ler histórico e enviar mensagens. No canal de destino, permita também anexar arquivos e incorporar links.
4. Defina `BOT_TOKEN`, `SOURCE_CHANNEL_IDS` e `DESTINATION_CHANNEL_ID` como variáveis de ambiente. `SOURCE_CHANNEL_IDS` aceita vários IDs separados por vírgula. Não coloque o token no GitHub nem em arquivos versionados.
5. Configure as mesmas variáveis como secrets/environment variables no Hoskes Cloud.

O serviço encaminha somente mensagens novas recebidas enquanto estiver conectado. Ele não importa histórico. A aplicação precisa ter o Message Content Intent habilitado no Developer Portal, e o bot precisa conseguir ver o canal de origem.

## Hospedagem Docker

O `Dockerfile` expõe a porta `8080` e oferece uma rota `GET /health` para o estado do bot. Configure o projeto Hoskes Cloud a partir do repositório GitHub e defina os valores de ambiente na configuração privada do projeto. O processo principal permanece conectado ao gateway do Discord enquanto o contêiner estiver em execução.

## Execução local

Copie `.env.example` para `.env`, preencha as variáveis e carregue-as no ambiente antes de executar `python main.py`. Não versione `.env`.

## Limites

- O destino pode rejeitar anexos grandes ou tipos de arquivo não aceitos; quando possível, o bot encaminha o link do anexo.
- A cópia de mensagens está limitada aos recursos e permissões da API oficial do Discord.
- O bot ignora mensagens de outros bots e não replica mensagens antigas.
