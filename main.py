"""Mirror new messages between two Discord channels using an official bot account."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import discord


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("discord-mirror")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


BOT_TOKEN = required_env("BOT_TOKEN")
SOURCE_CHANNEL_IDS = {
    int(channel_id.strip())
    for channel_id in required_env("SOURCE_CHANNEL_IDS").split(",")
    if channel_id.strip()
}
if not SOURCE_CHANNEL_IDS:
    raise RuntimeError("SOURCE_CHANNEL_IDS must contain at least one channel ID")
DESTINATION_CHANNEL_ID = int(required_env("DESTINATION_CHANNEL_ID"))
PORT = int(os.getenv("PORT", "8080"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return

        ready = client.is_ready()
        body = b'{"status":"ok"}' if ready else b'{"status":"starting"}'
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        logger.debug("health endpoint: " + format, *args)


def start_health_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    threading.Thread(target=server.serve_forever, name="health-server", daemon=True).start()
    logger.info("Health endpoint listening on port %s", PORT)
    return server


@client.event
async def on_ready() -> None:
    logger.info("Connected as %s (%s)", client.user, client.user.id if client.user else "unknown")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.channel.id not in SOURCE_CHANNEL_IDS:
        return

    destination = client.get_channel(DESTINATION_CHANNEL_ID)
    if destination is None:
        try:
            destination = await client.fetch_channel(DESTINATION_CHANNEL_ID)
        except discord.HTTPException:
            logger.exception("Could not find destination channel %s", DESTINATION_CHANNEL_ID)
            return

    if not isinstance(destination, (discord.TextChannel, discord.Thread)):
        logger.error("Destination %s does not accept text messages", DESTINATION_CHANNEL_ID)
        return

    files: list[discord.File] = []
    attachment_links: list[str] = []
    for attachment in message.attachments[:10]:
        try:
            files.append(await attachment.to_file(use_cached=True))
        except (discord.HTTPException, discord.NotFound):
            logger.warning("Could not mirror attachment %s; forwarding its URL", attachment.filename)
            attachment_links.append(attachment.url)

    content = message.content or ""
    if attachment_links:
        content = "\n".join(part for part in (content, *attachment_links) if part)
    if not content and not files and not message.embeds:
        content = "(mensagem sem texto ou anexo compatível)"

    try:
        await destination.send(
            content=content[:2000] or None,
            embeds=message.embeds[:10],
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
            suppress_embeds=False,
        )
        logger.info("Mirrored message %s to channel %s", message.id, DESTINATION_CHANNEL_ID)
    except discord.HTTPException:
        logger.exception("Could not mirror message %s", message.id)
    finally:
        for file in files:
            file.close()


async def run() -> None:
    server = start_health_server()
    try:
        await client.start(BOT_TOKEN)
    finally:
        server.shutdown()
        server.server_close()
        if not client.is_closed():
            await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Shutting down")
