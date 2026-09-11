"""
╔══════════════════════════════════════════════════════════════════╗
║                    👹  MONSTRÃO BOT  🔥                          ║
║                Bot Oficial do servidor CSI                       ║
║                        v1.0 — Online                              ║
╚══════════════════════════════════════════════════════════════════╝

Módulos:
  • VoiceMaster  — Calls temporárias com painel de controle
  • Logs Call    — Registra entradas/saídas/trocas de voz
  • Logs Chat    — Registra mensagens editadas/apagadas
  • Boas-vindas  — Recebe membros novos e registra quem convidou
  • Aniversários — Parabeniza a galera automaticamente
  • Diálogo      — Monstrão aprende a conversar com a galera
  • Config       — Comandos pra configurar os canais/categorias do bot

Prefixo de comando: m!  (ou M!)
"""

import discord
from discord.ext import commands, tasks
import asyncio
import os
import re
import json
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

# ══════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURAÇÕES GERAIS
# ══════════════════════════════════════════════════════════════════

TOKEN = os.getenv("MONSTRAO_TOKEN") or os.getenv("TOKEN")

PREFIXOS = ["m!", "M!"]

# Pasta de dados persistente (volume do Railway montado em /data).
# Pode ser trocada com a env var DATA_DIR se precisar rodar local sem o volume.
DATA_DIR = os.getenv("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE      = os.path.join(DATA_DIR, "monstrao_config.json")
DIALOGO_FILE     = os.path.join(DATA_DIR, "monstrao_dialogo.json")
ANIVERSARIO_FILE = os.path.join(DATA_DIR, "monstrao_aniversarios.json")
TICKETS_FILE     = os.path.join(DATA_DIR, "monstrao_tickets.json")

VM_LOBBY_NAME    = "🔜 cria sua call, guerreiro(a)"
VM_DEFAULT_LIMIT = 0     # 0 = sem limite
VM_EMPTY_DELAY   = 5     # segundos antes de deletar call vazia

# Canal padrão do painel de tickets (pode ser trocado com m!ticketpainel #canal)
DEFAULT_TICKET_CHANNEL_ID = 1499002823202050120

# Categoria padrão onde os canais de ticket nascem (pode ser trocada com m!setticketcategoria)
DEFAULT_TICKET_CATEGORIA_ID = 1499002724442837052

# Imagens padrão do painel — dá pra atualizar com m!setticketimagens caso o link expire
DEFAULT_TICKET_IMG_URL = "https://cdn.discordapp.com/attachments/1438634577470947429/1447619136091062332/Design_sem_nome_2.gif?ex=6aa425e1&is=6aa2d461&hm=83bc4816173c0190bbcbe75287d26dde1f01105699a936a3c634945db8056a53"
DEFAULT_TICKET_THUMB_URL = "https://cdn.discordapp.com/attachments/1429893251560636606/1547775993194749982/image.png?ex=6aa4a639&is=6aa354b9&hm=c4ccec7592bef497ccbdba4a6957ff455e1082f5c326f02637f730e62768d068"

# tipo -> (emoji, label, descrição curta pro select)
TICKET_TIPOS = {
    "suporte":     ("🛟", "Suporte",     "Dúvidas, ajuda geral e problemas no servidor"),
    "parceria":    ("🤝", "Parceria",    "Quer fechar uma parceria com a CSI"),
    "reclamacao":  ("⚠️", "Reclamação", "Denúncias e quebra de regras"),
    "seja_staff":  ("🧑‍💼", "Seja Staff", "Quer entrar pra equipe de staff da CSI"),
}

# ══════════════════════════════════════════════════════════════════
#  🗄️  PERSISTÊNCIA SIMPLES EM JSON
# ══════════════════════════════════════════════════════════════════

def _load(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_config(guild_id: int) -> dict:
    cfg = _load(CONFIG_FILE, {})
    return cfg.get(str(guild_id), {})


def set_config_value(guild_id: int, key: str, value) -> None:
    cfg = _load(CONFIG_FILE, {})
    gid = str(guild_id)
    cfg.setdefault(gid, {})
    cfg[gid][key] = value
    _save(CONFIG_FILE, cfg)


# ══════════════════════════════════════════════════════════════════
#  🤖  SETUP DO BOT
# ══════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.guilds          = True
intents.voice_states    = True
intents.invites         = True

bot = commands.Bot(command_prefix=PREFIXOS, intents=intents, help_command=None)

# ══════════════════════════════════════════════════════════════════
#  🎨  PALETA DE CORES DO MONSTRÃO
# ══════════════════════════════════════════════════════════════════

COR_VERDE   = 0x1B5E20   # verde escamado
COR_ROXO    = 0x4B0082   # roxo sombrio
COR_LARANJA = 0xFF6600   # fogo / energia
COR_OK      = 0x00E676
COR_ERRO    = 0xFF5252
COR_DOURADO = 0xFFD700
COR_AZUL    = 0x5865F2


def embed_ok(titulo: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=titulo, description=desc, color=COR_OK, timestamp=datetime.now(timezone.utc))
    e.set_footer(text="👹 Monstrão • CSI")
    return e


def embed_erro(desc: str) -> discord.Embed:
    e = discord.Embed(title="❌ Ihh, deu ruim!!", description=desc, color=COR_ERRO, timestamp=datetime.now(timezone.utc))
    e.set_footer(text="👹 Monstrão • CSI")
    return e


def embed_info(titulo: str, desc: str, cor: int = COR_ROXO) -> discord.Embed:
    e = discord.Embed(title=titulo, description=desc, color=cor, timestamp=datetime.now(timezone.utc))
    e.set_footer(text="👹 Monstrão • CSI")
    return e


# ══════════════════════════════════════════════════════════════════
#  🎙️  VOICEMASTER — CALLS TEMPORÁRIAS
# ══════════════════════════════════════════════════════════════════

_VM_MSGS = {
    "sem_call":          "eae, {user}!! você ainda não tem call ativa!! entra em **🔜 cria sua call, guerreiro(a)** que eu arrumo uma pra você na hora!! 💪🔥",
    "renomeada":         "prontinho, guerreiro(a)!! sua call agora é **{nome}**!! ficou brabo!! 🔥👹",
    "limite_set":        "fechado!! sua call agora aceita até **{limite}** guerreiro(s)!! 🎯💪",
    "limite_removido":   "removido!! agora a call é sem limite, pode chamar a galera toda!! 🥳👹",
    "trancada":          "call trancada na porrada!! só entra quem você deixar!! 🔒💪",
    "destrancada":       "call destrancada!! geral pode entrar agora!! 🔓👹",
    "invisivel":         "call escondida!! ninguém vai nem saber que ela existe!! 👻🔥",
    "visivel":           "call visível de novo pra todo mundo!! 👁️👹",
    "usuario_kickado":   "valeu e até mais, **{user}**!! o dono pediu pra você sair da call!! 👋🔥",
    "usuario_banido":    "**{user}** tomou ban da call!! não entra mais não!! 🚫👹",
    "usuario_permitido": "**{user}** tá liberado(a) pra entrar na call!! bem-vindo(a), guerreiro(a)!! 💪🔥",
    "dono_transferido":  "combinado!! agora **{user}** é o(a) novo(a) dono(a) dessa call!! 👑👹",
    "dono_reivindicado": "você assumiu o comando da call!! agora é sua, guerreiro(a)!! 👑🔥",
    "bitrate_set":       "áudio ajustado pra **{bitrate}kbps**!! ficou som de monstro!! 🎧👹",
    "permanente":        "sua call agora é **permanente**!! não some nem vazia!! 💎🔥",
    "temporaria":        "sua call voltou a ser **temporária**!! some quando esvaziar!! 🕐👹",
    "nao_na_call":       "você precisa tá dentro de uma call pra usar isso, {user}!! 🥲💪",
    "user_nao_na_call":  "esse usuário não tá na sua call não!! 🤔👹",
    "ja_dono":           "você já é o dono dessa call, mermão!! 😤🔥",
    "dono_ainda_na_call":"o dono ainda tá na call!! só dá pra assumir quando ele sair!! 🥲👹",
    "setup_existe":      "já tem um lobby do Monstrão configurado aqui!! usa `m!vm reset` pra recriar!! 🤔🔥",
    "nao_gerenciada":    "essa call não é gerenciada pelo Monstrão não!! 🤔👹",
    "nao_achou_user":    "não achei esse usuário no servidor!! confere o nome aí!! 🤔🔥",
}


def _vm_msg(key: str, **kwargs) -> str:
    m = _VM_MSGS.get(key, "algo quebrou aqui... até os monstros erram!! 🥲👹")
    return m.format(**kwargs)


# ── Modais ────────────────────────────────────────

class VMModalRenomear(discord.ui.Modal, title="✏️ Renomear Sua Call"):
    nome = discord.ui.TextInput(
        label="Novo nome da call",
        placeholder="Ex: 🔥 Call dos Guerreiros",
        min_length=1, max_length=100, required=True
    )

    def __init__(self, cog, channel):
        super().__init__()
        self.cog = cog
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.channel.edit(name=self.nome.value)
            await interaction.response.send_message(
                embed=embed_ok("✏️ Renomeada!!", _vm_msg("renomeada", nome=self.nome.value)), ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=embed_erro("sem permissão pra renomear a call!! 😢"), ephemeral=True)


class VMModalLimite(discord.ui.Modal, title="👥 Limite de Usuários"):
    limite = discord.ui.TextInput(
        label="Limite (0 = sem limite, máx 99)",
        placeholder="Ex: 5", min_length=1, max_length=2, required=True
    )

    def __init__(self, cog, channel):
        super().__init__()
        self.cog = cog
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            n = int(self.limite.value)
            if n < 0 or n > 99:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(embed=embed_erro("coloca um número entre 0 e 99!! 🥲"), ephemeral=True)
            return
        try:
            await self.channel.edit(user_limit=n)
            txt = _vm_msg("limite_removido") if n == 0 else _vm_msg("limite_set", limite=n)
            titulo = "👥 Limite Removido!!" if n == 0 else "👥 Limite Definido!!"
            await interaction.response.send_message(embed=embed_ok(titulo, txt), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=embed_erro("sem permissão pra mudar o limite!! 😢"), ephemeral=True)


class VMModalBitrate(discord.ui.Modal, title="🎙️ Qualidade de Áudio"):
    bitrate = discord.ui.TextInput(
        label="Bitrate em kbps (8–384)",
        placeholder="Ex: 64, 96, 128", min_length=1, max_length=3, required=True
    )

    def __init__(self, cog, channel):
        super().__init__()
        self.cog = cog
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            n = int(self.bitrate.value)
            if n < 8 or n > 384:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(embed=embed_erro("bitrate tem que ser entre 8 e 384 kbps!! 🥲"), ephemeral=True)
            return
        try:
            await self.channel.edit(bitrate=n * 1000)
            await interaction.response.send_message(embed=embed_ok("🎙️ Áudio Atualizado!!", _vm_msg("bitrate_set", bitrate=n)), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=embed_erro("sem permissão pra mudar o bitrate!! 😢"), ephemeral=True)


class VMModalUsuario(discord.ui.Modal):
    """Modal genérico pra ações que pedem nome/menção de usuário (kick, ban, permitir, transferir)."""
    user_input = discord.ui.TextInput(
        label="Nome do usuário",
        placeholder="Ex: guerreiro123", min_length=1, max_length=50, required=True
    )

    def __init__(self, cog, channel, guild, acao: str, titulo: str):
        super().__init__(title=titulo)
        self.cog = cog
        self.channel = channel
        self.guild = guild
        self.acao = acao

    def _find_member(self, pool):
        alvo_nome = self.user_input.value.strip().lstrip("@").lower()
        return discord.utils.find(
            lambda m: m.name.lower() == alvo_nome or m.display_name.lower() == alvo_nome, pool
        )

    async def on_submit(self, interaction: discord.Interaction):
        info = self.cog.vm_channels.get(self.channel.id)
        if info is None:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_gerenciada")), ephemeral=True)
            return

        if self.acao == "kick":
            alvo = self._find_member(self.channel.members)
            if not alvo:
                await interaction.response.send_message(embed=embed_erro(_vm_msg("user_nao_na_call")), ephemeral=True)
                return
            try:
                await alvo.move_to(None, reason="Kickado da call pelo dono — Monstrão VoiceMaster")
                await interaction.response.send_message(embed=embed_ok("👋 Kickado!!", _vm_msg("usuario_kickado", user=alvo.display_name)), ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message(embed=embed_erro("não consegui mover esse usuário!! sem permissão!! 😢"), ephemeral=True)

        elif self.acao in ("ban", "permitir"):
            alvo = self._find_member(self.guild.members)
            if not alvo:
                await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_achou_user")), ephemeral=True)
                return
            ow = self.channel.overwrites_for(alvo)
            if self.acao == "ban":
                ow.connect = False
                await self.channel.set_permissions(alvo, overwrite=ow)
                if alvo in self.channel.members:
                    try:
                        await alvo.move_to(None)
                    except Exception:
                        pass
                info.setdefault("banned", [])
                if alvo.id not in info["banned"]:
                    info["banned"].append(alvo.id)
                await interaction.response.send_message(embed=embed_ok("🚫 Banido!!", _vm_msg("usuario_banido", user=alvo.display_name)), ephemeral=True)
            else:
                ow.connect = True
                ow.view_channel = True
                await self.channel.set_permissions(alvo, overwrite=ow)
                if alvo.id in info.get("banned", []):
                    info["banned"].remove(alvo.id)
                await interaction.response.send_message(embed=embed_ok("✅ Permitido!!", _vm_msg("usuario_permitido", user=alvo.display_name)), ephemeral=True)

        elif self.acao == "transferir":
            alvo = self._find_member(self.channel.members)
            if not alvo:
                await interaction.response.send_message(embed=embed_erro(_vm_msg("user_nao_na_call")), ephemeral=True)
                return
            info["owner"] = alvo.id
            await interaction.response.send_message(embed=embed_ok("👑 Transferido!!", _vm_msg("dono_transferido", user=alvo.display_name)), ephemeral=True)


# ── Painel de Controle da Call ─────────────────────

class VMPainelView(discord.ui.View):
    """Painel persistente de controle da call do Monstrão."""

    def __init__(self, cog: "VoiceMasterCog"):
        super().__init__(timeout=None)
        self.cog = cog

    async def _checar_dono(self, interaction: discord.Interaction):
        user = interaction.user
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_na_call", user=user.mention)), ephemeral=True)
            return None
        ch = user.voice.channel
        info = self.cog.vm_channels.get(ch.id)
        if not info:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_gerenciada")), ephemeral=True)
            return None
        if info["owner"] != user.id:
            await interaction.response.send_message(embed=embed_erro("só o dono da call pode usar isso!! 👑"), ephemeral=True)
            return None
        return ch

    # Linha 0
    @discord.ui.button(label="Renomear", emoji="✏️", style=discord.ButtonStyle.blurple, custom_id="monstrao_vm_renomear", row=0)
    async def btn_renomear(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalRenomear(self.cog, ch))

    @discord.ui.button(label="Limite", emoji="👥", style=discord.ButtonStyle.blurple, custom_id="monstrao_vm_limite", row=0)
    async def btn_limite(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalLimite(self.cog, ch))

    @discord.ui.button(label="Áudio", emoji="🎙️", style=discord.ButtonStyle.blurple, custom_id="monstrao_vm_bitrate", row=0)
    async def btn_bitrate(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalBitrate(self.cog, ch))

    @discord.ui.button(label="Transferir", emoji="👑", style=discord.ButtonStyle.blurple, custom_id="monstrao_vm_transferir", row=0)
    async def btn_transferir(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalUsuario(self.cog, ch, interaction.guild, "transferir", "👑 Transferir Dono"))

    # Linha 1
    @discord.ui.button(label="Trancar", emoji="🔒", style=discord.ButtonStyle.gray, custom_id="monstrao_vm_trancar", row=1)
    async def btn_trancar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        ow = ch.overwrites_for(interaction.guild.default_role)
        ow.connect = False
        await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
        await interaction.response.send_message(embed=embed_ok("🔒 Trancada!!", _vm_msg("trancada")), ephemeral=True)

    @discord.ui.button(label="Destrancar", emoji="🔓", style=discord.ButtonStyle.gray, custom_id="monstrao_vm_destrancar", row=1)
    async def btn_destrancar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        ow = ch.overwrites_for(interaction.guild.default_role)
        ow.connect = None
        await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
        await interaction.response.send_message(embed=embed_ok("🔓 Destrancada!!", _vm_msg("destrancada")), ephemeral=True)

    @discord.ui.button(label="Ocultar", emoji="👻", style=discord.ButtonStyle.gray, custom_id="monstrao_vm_ocultar", row=1)
    async def btn_ocultar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        ow = ch.overwrites_for(interaction.guild.default_role)
        ow.view_channel = False
        await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
        await interaction.response.send_message(embed=embed_ok("👻 Oculta!!", _vm_msg("invisivel")), ephemeral=True)

    @discord.ui.button(label="Mostrar", emoji="👁️", style=discord.ButtonStyle.gray, custom_id="monstrao_vm_mostrar", row=1)
    async def btn_mostrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        ow = ch.overwrites_for(interaction.guild.default_role)
        ow.view_channel = None
        await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
        await interaction.response.send_message(embed=embed_ok("👁️ Visível!!", _vm_msg("visivel")), ephemeral=True)

    # Linha 2
    @discord.ui.button(label="Permanente", emoji="💎", style=discord.ButtonStyle.green, custom_id="monstrao_vm_permanente", row=2)
    async def btn_permanente(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        self.cog.vm_channels[ch.id]["permanent"] = True
        await interaction.response.send_message(embed=embed_ok("💎 Permanente!!", _vm_msg("permanente")), ephemeral=True)

    @discord.ui.button(label="Temporária", emoji="🕐", style=discord.ButtonStyle.green, custom_id="monstrao_vm_temporaria", row=2)
    async def btn_temporaria(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if not ch:
            return
        self.cog.vm_channels[ch.id]["permanent"] = False
        await interaction.response.send_message(embed=embed_ok("🕐 Temporária!!", _vm_msg("temporaria")), ephemeral=True)

    @discord.ui.button(label="Assumir", emoji="👑", style=discord.ButtonStyle.green, custom_id="monstrao_vm_assumir", row=2)
    async def btn_assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_na_call", user=user.mention)), ephemeral=True)
            return
        ch = user.voice.channel
        info = self.cog.vm_channels.get(ch.id)
        if not info:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("nao_gerenciada")), ephemeral=True)
            return
        if info["owner"] == user.id:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("ja_dono")), ephemeral=True)
            return
        dono_atual = ch.guild.get_member(info["owner"])
        if dono_atual and dono_atual in ch.members:
            await interaction.response.send_message(embed=embed_erro(_vm_msg("dono_ainda_na_call")), ephemeral=True)
            return
        info["owner"] = user.id
        await interaction.response.send_message(embed=embed_ok("👑 Assumido!!", _vm_msg("dono_reivindicado")), ephemeral=True)

    # Linha 3
    @discord.ui.button(label="Kick", emoji="👋", style=discord.ButtonStyle.red, custom_id="monstrao_vm_kick", row=3)
    async def btn_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalUsuario(self.cog, ch, interaction.guild, "kick", "👋 Kickar da Call"))

    @discord.ui.button(label="Banir", emoji="🚫", style=discord.ButtonStyle.red, custom_id="monstrao_vm_banir", row=3)
    async def btn_banir(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalUsuario(self.cog, ch, interaction.guild, "ban", "🚫 Banir da Call"))

    @discord.ui.button(label="Permitir", emoji="✅", style=discord.ButtonStyle.red, custom_id="monstrao_vm_permitir", row=3)
    async def btn_permitir(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = await self._checar_dono(interaction)
        if ch:
            await interaction.response.send_modal(VMModalUsuario(self.cog, ch, interaction.guild, "permitir", "✅ Permitir na Call"))


class VoiceMasterCog(commands.Cog, name="MonstraoVoiceMaster"):
    """👹 Sistema de calls temporárias do Monstrão."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vm_channels: dict[int, dict] = {}   # channel_id -> {owner, permanent, banned}

    def _lobby_id(self, guild_id: int):
        return get_config(guild_id).get("vm_lobby_id")

    def _painel_channel_id(self, guild_id: int):
        return get_config(guild_id).get("vm_painel_channel_id")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        lobby_id = self._lobby_id(guild.id)

        # ── Entrou no lobby → cria call nova ──
        if lobby_id and after.channel and after.channel.id == lobby_id:
            categoria = after.channel.category
            try:
                novo = await guild.create_voice_channel(
                    name=f"🔥 Call de {member.display_name}",
                    category=categoria,
                    user_limit=VM_DEFAULT_LIMIT,
                    reason="Monstrão VoiceMaster: nova call"
                )
                await member.move_to(novo)
            except discord.Forbidden:
                return

            self.vm_channels[novo.id] = {"owner": member.id, "permanent": False, "banned": []}

            embed_painel = embed_info(
                "🔥 Sua Call Tá Pronta!!",
                f"e aí, {member.mention}!! essa call é sua!! use os botões abaixo pra comandar ela!! 💪👹",
            )
            painel_view = VMPainelView(self)
            painel_enviado = False

            painel_id = self._painel_channel_id(guild.id)
            if painel_id:
                canal_cfg = guild.get_channel(painel_id)
                if canal_cfg:
                    try:
                        await canal_cfg.send(embed=embed_painel, view=painel_view)
                        painel_enviado = True
                    except Exception:
                        pass

            if not painel_enviado and categoria:
                me = guild.me
                for tc in categoria.text_channels:
                    perms = tc.permissions_for(me)
                    if perms.send_messages and perms.embed_links and perms.view_channel:
                        try:
                            await tc.send(embed=embed_painel, view=painel_view)
                            painel_enviado = True
                        except Exception:
                            pass
                        break

            if not painel_enviado:
                try:
                    await member.send(embed=embed_painel, view=painel_view)
                except Exception:
                    pass

        # ── Saiu de call gerenciada e ficou vazia → deleta ──
        if before.channel and before.channel.id in self.vm_channels:
            ch = before.channel
            info = self.vm_channels[ch.id]
            if not ch.members and not info.get("permanent"):
                await asyncio.sleep(VM_EMPTY_DELAY)
                ch2 = guild.get_channel(ch.id)
                if ch2 and not ch2.members:
                    try:
                        await ch2.delete(reason="Monstrão VoiceMaster: call vazia")
                    except Exception:
                        pass
                    self.vm_channels.pop(ch.id, None)

    @commands.group(name="vm", aliases=["voicemaster", "call"], invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def vm_group(self, ctx: commands.Context):
        embed = embed_info(
            "👹 Monstrão VoiceMaster",
            "`m!vm setup` — configurar lobby (no canal de voz atual ou por categoria)\n"
            "`m!vm reset` — recriar lobby\n"
            "`m!vm setpainel #canal` — canal fixo do painel\n"
            "`m!vm info` — status do sistema"
        )
        await ctx.send(embed=embed)

    @vm_group.command(name="setup")
    @commands.has_permissions(manage_channels=True)
    async def vm_setup(self, ctx: commands.Context, categoria: discord.CategoryChannel = None):
        guild = ctx.guild
        lobby_id = self._lobby_id(guild.id)
        if lobby_id and guild.get_channel(lobby_id):
            await ctx.send(embed=embed_info("🤔 Já existe!!", _vm_msg("setup_existe")))
            return
        try:
            lobby = await guild.create_voice_channel(name=VM_LOBBY_NAME, category=categoria, reason="Monstrão VoiceMaster Setup")
            set_config_value(guild.id, "vm_lobby_id", lobby.id)
            await ctx.send(embed=embed_ok(
                "🎉 VoiceMaster Configurado!!",
                f"lobby criado: {lobby.mention}\n\nentra em **{VM_LOBBY_NAME}** pra ganhar sua própria call!! 🔥👹"
            ))
        except discord.Forbidden:
            await ctx.send(embed=embed_erro("não tenho permissão pra criar canais de voz!! 😢"))

    @vm_group.command(name="reset")
    @commands.has_permissions(manage_channels=True)
    async def vm_reset(self, ctx: commands.Context, categoria: discord.CategoryChannel = None):
        guild = ctx.guild
        lobby_id = self._lobby_id(guild.id)
        if lobby_id:
            old_ch = guild.get_channel(lobby_id)
            if old_ch:
                try:
                    await old_ch.delete(reason="Monstrão VoiceMaster Reset")
                except Exception:
                    pass
        try:
            lobby = await guild.create_voice_channel(name=VM_LOBBY_NAME, category=categoria, reason="Monstrão VoiceMaster Reset")
            set_config_value(guild.id, "vm_lobby_id", lobby.id)
            await ctx.send(embed=embed_ok("✅ VoiceMaster Recriado!!", f"novo lobby: {lobby.mention} 👹🔥"))
        except discord.Forbidden:
            await ctx.send(embed=embed_erro("não tenho permissão pra criar canais!! 😢"))

    @vm_group.command(name="setpainel")
    @commands.has_permissions(manage_channels=True)
    async def vm_setpainel(self, ctx: commands.Context, canal: discord.TextChannel = None):
        set_config_value(ctx.guild.id, "vm_painel_channel_id", canal.id if canal else None)
        if canal:
            await ctx.send(embed=embed_ok("✅ Canal do Painel Definido!!", f"painel vai aparecer sempre em {canal.mention}!! 👹"))
        else:
            await ctx.send(embed=embed_ok("✅ Canal do Painel Resetado!!", "vou escolher automaticamente o primeiro canal disponível!! 👹"))

    @vm_group.command(name="info")
    @commands.has_permissions(manage_channels=True)
    async def vm_info(self, ctx: commands.Context):
        guild = ctx.guild
        lobby_id = self._lobby_id(guild.id)
        painel_id = self._painel_channel_id(guild.id)
        lobby = guild.get_channel(lobby_id) if lobby_id else None
        painel_ch = guild.get_channel(painel_id) if painel_id else None
        embed = embed_info("📊 Monstrão VoiceMaster — Info", "")
        embed.add_field(name="🎙️ Lobby", value=lobby.mention if lobby else "❌ Não configurado", inline=True)
        embed.add_field(name="📞 Calls Ativas", value=f"`{len(self.vm_channels)}`", inline=True)
        embed.add_field(name="⚙️ Delay Exclusão", value=f"`{VM_EMPTY_DELAY}s`", inline=True)
        embed.add_field(name="💬 Canal do Painel", value=painel_ch.mention if painel_ch else "`auto`", inline=True)
        await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════
#  ⚙️  CONFIG — CANAIS DO SERVIDOR
# ══════════════════════════════════════════════════════════════════

class ConfigCog(commands.Cog, name="MonstraoConfig"):
    """👹 Comandos pra configurar os canais que o Monstrão usa."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="setlogvoz")
    @commands.has_permissions(manage_guild=True)
    async def set_log_voz(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "log_call_id", canal.id)
        await ctx.send(embed=embed_ok("✅ Log de Voz Definido!!", f"vou logar entradas/saídas de call em {canal.mention}!! 👹"))

    @commands.command(name="setlogchat")
    @commands.has_permissions(manage_guild=True)
    async def set_log_chat(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "log_chat_id", canal.id)
        await ctx.send(embed=embed_ok("✅ Log de Chat Definido!!", f"vou logar msgs editadas/apagadas em {canal.mention}!! 👹"))

    @commands.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def set_welcome(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "welcome_channel_id", canal.id)
        await ctx.send(embed=embed_ok("✅ Boas-Vindas Definidas!!", f"vou dar as boas-vindas em {canal.mention}!! 👹🔥"))

    @commands.command(name="setconvites")
    @commands.has_permissions(manage_guild=True)
    async def set_convites(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "invite_log_id", canal.id)
        await ctx.send(embed=embed_ok("✅ Log de Convites Definido!!", f"vou registrar quem convidou quem em {canal.mention}!! 👹"))

    @commands.command(name="setaniversario")
    @commands.has_permissions(manage_guild=True)
    async def set_aniversario(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "birthday_channel_id", canal.id)
        await ctx.send(embed=embed_ok(
            "✅ Canal de Aniversários Definido!!",
            f"manda a data assim em {canal.mention}: `15/03` que eu registro!! 🎂👹"
        ))

    @commands.command(name="configinfo")
    @commands.has_permissions(manage_guild=True)
    async def config_info(self, ctx: commands.Context):
        cfg = get_config(ctx.guild.id)

        def fmt(key):
            cid = cfg.get(key)
            ch = ctx.guild.get_channel(cid) if cid else None
            return ch.mention if ch else "❌ não configurado"

        embed = embed_info("⚙️ Config Atual do Monstrão", "")
        embed.add_field(name="📞 Log de Voz", value=fmt("log_call_id"), inline=True)
        embed.add_field(name="📝 Log de Chat", value=fmt("log_chat_id"), inline=True)
        embed.add_field(name="👋 Boas-Vindas", value=fmt("welcome_channel_id"), inline=True)
        embed.add_field(name="💌 Convites", value=fmt("invite_log_id"), inline=True)
        embed.add_field(name="🎂 Aniversários", value=fmt("birthday_channel_id"), inline=True)
        embed.add_field(name="🎙️ Lobby VM", value=fmt("vm_lobby_id"), inline=True)
        await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════
#  📋  LOGS — VOZ E TEXTO
# ══════════════════════════════════════════════════════════════════

class LogCog(commands.Cog, name="MonstraoLogs"):
    """👹 Sistema de logs de voz e texto."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _log_call_channel(self, guild: discord.Guild):
        cid = get_config(guild.id).get("log_call_id")
        return guild.get_channel(cid) if cid else None

    def _log_chat_channel(self, guild: discord.Guild):
        cid = get_config(guild.id).get("log_chat_id")
        return guild.get_channel(cid) if cid else None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        ch = self._log_call_channel(guild)
        if not ch:
            return
        now = datetime.now(timezone.utc)

        if after.channel and not before.channel:
            e = discord.Embed(description=f"🔊 {member.mention} entrou em **{after.channel.name}**", color=COR_OK, timestamp=now)
            e.set_footer(text="👹 Monstrão • Log de Voz")
            await ch.send(embed=e)
        elif before.channel and not after.channel:
            e = discord.Embed(description=f"🔇 {member.mention} saiu de **{before.channel.name}**", color=COR_ERRO, timestamp=now)
            e.set_footer(text="👹 Monstrão • Log de Voz")
            await ch.send(embed=e)
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            e = discord.Embed(description=f"🔀 {member.mention} foi de **{before.channel.name}** pra **{after.channel.name}**", color=COR_DOURADO, timestamp=now)
            e.set_footer(text="👹 Monstrão • Log de Voz")
            await ch.send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        ch = self._log_chat_channel(message.guild)
        if not ch:
            return
        e = discord.Embed(
            description=f"🗑️ Mensagem de {message.author.mention} apagada em {message.channel.mention}",
            color=COR_ERRO, timestamp=datetime.now(timezone.utc)
        )
        if message.content:
            e.add_field(name="Conteúdo", value=message.content[:1000], inline=False)
        e.set_footer(text="👹 Monstrão • Log de Chat")
        await ch.send(embed=e)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        ch = self._log_chat_channel(before.guild)
        if not ch:
            return
        e = discord.Embed(
            description=f"✏️ {before.author.mention} editou uma mensagem em {before.channel.mention}",
            color=COR_DOURADO, timestamp=datetime.now(timezone.utc)
        )
        e.add_field(name="Antes", value=before.content[:500] or "*vazio*", inline=False)
        e.add_field(name="Depois", value=after.content[:500] or "*vazio*", inline=False)
        e.set_footer(text="👹 Monstrão • Log de Chat")
        await ch.send(embed=e)


# ══════════════════════════════════════════════════════════════════
#  👋  BOAS-VINDAS E CONVITES
# ══════════════════════════════════════════════════════════════════

class WelcomeCog(commands.Cog, name="MonstraoWelcome"):
    """👹 Recepção de membros novos e rastreamento de convites."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invite_cache: dict[int, dict[str, int]] = {}   # guild_id -> {code: uses}

    async def _cache_guild_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
        except discord.Forbidden:
            self.invite_cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self.invite_cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        self.invite_cache.get(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = get_config(guild.id)

        # ── Boas-vindas ──
        welcome_id = cfg.get("welcome_channel_id")
        if welcome_id:
            ch = guild.get_channel(welcome_id)
            if ch:
                e = discord.Embed(
                    title="🔥 Mais um guerreiro chegou na CSI!!",
                    description=f"e aí, {member.mention}!! bem-vindo(a) à família CSI!! agora você tem um monstro do seu lado!! 👹💪",
                    color=COR_LARANJA, timestamp=datetime.now(timezone.utc)
                )
                if member.display_avatar:
                    e.set_thumbnail(url=member.display_avatar.url)
                e.set_footer(text=f"👹 Monstrão • agora somos {guild.member_count}")
                try:
                    await ch.send(embed=e)
                except Exception:
                    pass

        # ── Convites ──
        invite_log_id = cfg.get("invite_log_id")
        if invite_log_id:
            log_ch = guild.get_channel(invite_log_id)
            usado = None
            try:
                invites_atuais = await guild.invites()
                cache_antigo = self.invite_cache.get(guild.id, {})
                for inv in invites_atuais:
                    if inv.uses > cache_antigo.get(inv.code, 0):
                        usado = inv
                        break
                self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites_atuais}
            except discord.Forbidden:
                pass

            if log_ch:
                if usado:
                    desc = f"{member.mention} entrou usando o convite de **{usado.inviter}** (código `{usado.code}`, {usado.uses} usos)"
                else:
                    desc = f"{member.mention} entrou, mas não consegui identificar o convite usado!! 🤔"
                e = discord.Embed(description=desc, color=COR_AZUL, timestamp=datetime.now(timezone.utc))
                e.set_footer(text="👹 Monstrão • Convites")
                try:
                    await log_ch.send(embed=e)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfg = get_config(member.guild.id)
        welcome_id = cfg.get("welcome_channel_id")
        if not welcome_id:
            return
        ch = member.guild.get_channel(welcome_id)
        if not ch:
            return
        e = discord.Embed(description=f"💨 **{member}** saiu da CSI... vai com Deus, guerreiro(a)!! 👹", color=COR_ROXO, timestamp=datetime.now(timezone.utc))
        e.set_footer(text="👹 Monstrão")
        try:
            await ch.send(embed=e)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  💬  DIÁLOGO — MONSTRÃO APRENDE A CONVERSAR
# ══════════════════════════════════════════════════════════════════

class DialogueCog(commands.Cog, name="MonstraoDialogo"):
    """👹 Sistema de aprendizado conversacional."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _dados(self, guild_id: int) -> dict:
        todos = _load(DIALOGO_FILE, {})
        return todos.get(str(guild_id), {})

    def _salvar(self, guild_id: int, dados: dict) -> None:
        todos = _load(DIALOGO_FILE, {})
        todos[str(guild_id)] = dados
        _save(DIALOGO_FILE, todos)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        dados = self._dados(message.guild.id)
        if not dados:
            return
        conteudo = message.content.lower()
        for gatilho, respostas in dados.items():
            if re.search(rf"\b{re.escape(gatilho)}\b", conteudo):
                if respostas:
                    await message.channel.send(random.choice(respostas))
                break

    @commands.command(name="ensinar")
    @commands.has_permissions(manage_messages=True)
    async def ensinar(self, ctx: commands.Context, gatilho: str, *, resposta: str):
        dados = self._dados(ctx.guild.id)
        dados.setdefault(gatilho.lower(), [])
        dados[gatilho.lower()].append(resposta)
        self._salvar(ctx.guild.id, dados)
        await ctx.send(embed=embed_ok("🧠 Aprendido!!", f"quando alguém falar **{gatilho}**, posso responder: \"{resposta}\" 👹"))

    @commands.command(name="esquecer")
    @commands.has_permissions(manage_messages=True)
    async def esquecer(self, ctx: commands.Context, gatilho: str):
        dados = self._dados(ctx.guild.id)
        if gatilho.lower() in dados:
            del dados[gatilho.lower()]
            self._salvar(ctx.guild.id, dados)
            await ctx.send(embed=embed_ok("🗑️ Esquecido!!", f"apaguei tudo que eu sabia sobre **{gatilho}** 👹"))
        else:
            await ctx.send(embed=embed_erro("não conheço esse gatilho não!! 🤔"))

    @commands.command(name="gatilhos")
    async def gatilhos(self, ctx: commands.Context):
        dados = self._dados(ctx.guild.id)
        if not dados:
            await ctx.send(embed=embed_info("🧠 Gatilhos", "ainda não aprendi nada nesse servidor!! me ensina com `m!ensinar` 👹"))
            return
        desc = ", ".join(f"`{g}`" for g in dados.keys())
        await ctx.send(embed=embed_info("🧠 O Que Eu Sei", desc))

    @commands.command(name="resposta")
    async def resposta(self, ctx: commands.Context, gatilho: str):
        dados = self._dados(ctx.guild.id)
        respostas = dados.get(gatilho.lower())
        if not respostas:
            await ctx.send(embed=embed_erro("não conheço esse gatilho não!! 🤔"))
            return
        desc = "\n".join(f"• {r}" for r in respostas)
        await ctx.send(embed=embed_info(f"🧠 Respostas pra \"{gatilho}\"", desc))

    @commands.command(name="simular")
    async def simular(self, ctx: commands.Context, *, texto: str):
        dados = self._dados(ctx.guild.id)
        conteudo = texto.lower()
        for gatilho, respostas in dados.items():
            if re.search(rf"\b{re.escape(gatilho)}\b", conteudo) and respostas:
                await ctx.send(random.choice(respostas))
                return
        await ctx.send(embed=embed_info("🤔 Simulação", "eu não responderia nada pra essa frase!!"))


# ══════════════════════════════════════════════════════════════════
#  🎂  ANIVERSÁRIOS
# ══════════════════════════════════════════════════════════════════

class BirthdayCog(commands.Cog, name="MonstraoAniversarios"):
    """👹 Sistema de aniversários da CSI."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ultimo_anuncio: dict[int, str] = {}   # guild_id -> "DD/MM/AAAA" do último dia anunciado
        self.checar_aniversarios.start()

    def cog_unload(self):
        self.checar_aniversarios.cancel()

    def _dados(self, guild_id: int) -> dict:
        todos = _load(ANIVERSARIO_FILE, {})
        return todos.get(str(guild_id), {})

    def _salvar(self, guild_id: int, dados: dict) -> None:
        todos = _load(ANIVERSARIO_FILE, {})
        todos[str(guild_id)] = dados
        _save(ANIVERSARIO_FILE, todos)

    @staticmethod
    def _valida_data(texto: str):
        texto = texto.strip()
        if not re.fullmatch(r"\d{1,2}/\d{1,2}", texto):
            return None
        try:
            datetime.strptime(f"{texto}/2000", "%d/%m/%Y")
            return texto
        except ValueError:
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        cfg = get_config(message.guild.id)
        if message.channel.id != cfg.get("birthday_channel_id"):
            return
        data = self._valida_data(message.content)
        if not data:
            return
        dados = self._dados(message.guild.id)
        dados[str(message.author.id)] = data
        self._salvar(message.guild.id, dados)
        try:
            await message.add_reaction("🎂")
        except Exception:
            pass

    @commands.command(name="meuniver")
    async def meuniver(self, ctx: commands.Context, data: str = None):
        dados = self._dados(ctx.guild.id)
        if data is None:
            atual = dados.get(str(ctx.author.id))
            if atual:
                await ctx.send(embed=embed_info("🎂 Seu Aniversário", f"tá registrado como **{atual}**!!"))
            else:
                await ctx.send(embed=embed_info("🎂 Aniversário", "você ainda não registrou!! usa `m!meuniver DD/MM` 👹"))
            return
        valida = self._valida_data(data)
        if not valida:
            await ctx.send(embed=embed_erro("formato inválido!! usa `DD/MM`, tipo `15/03` 🥲"))
            return
        dados[str(ctx.author.id)] = valida
        self._salvar(ctx.guild.id, dados)
        await ctx.send(embed=embed_ok("🎂 Registrado!!", f"seu aniversário é dia **{valida}**!! vou lembrar disso, guerreiro(a)!! 👹"))

    @commands.command(name="proximosniver")
    async def proximosniver(self, ctx: commands.Context):
        dados = self._dados(ctx.guild.id)
        if not dados:
            await ctx.send(embed=embed_info("🎉 Próximos Aniversários", "ninguém registrou aniversário ainda!! 👹"))
            return

        hoje = datetime.now(timezone.utc).date()
        lista = []
        for uid, data_str in dados.items():
            dia, mes = map(int, data_str.split("/"))
            try:
                prox = datetime(hoje.year, mes, dia).date()
            except ValueError:
                continue
            if prox < hoje:
                prox = datetime(hoje.year + 1, mes, dia).date()
            dias = (prox - hoje).days
            lista.append((dias, data_str, uid))
        lista.sort(key=lambda x: x[0])

        desc = "\n".join(
            f"🎂 **{data_str}** — <@{uid}> (`{dias}` dia{'s' if dias != 1 else ''} restante{'s' if dias != 1 else ''})"
            for dias, data_str, uid in lista[:15]
        )
        await ctx.send(embed=embed_info("🎉 Próximos Aniversários", desc or "ninguém encontrado!!", cor=COR_DOURADO))

    @tasks.loop(hours=24)
    async def checar_aniversarios(self):
        hoje = datetime.now(timezone.utc)
        chave_hoje = hoje.strftime("%d/%m/%Y")
        hoje_dm = hoje.strftime("%d/%m")

        for guild in self.bot.guilds:
            if self._ultimo_anuncio.get(guild.id) == chave_hoje:
                continue
            cfg = get_config(guild.id)
            canal_id = cfg.get("birthday_channel_id")
            if not canal_id:
                continue
            canal = guild.get_channel(canal_id)
            if not canal:
                continue
            dados = self._dados(guild.id)
            aniversariantes = [uid for uid, data_str in dados.items() if data_str == hoje_dm]
            if aniversariantes:
                mencoes = ", ".join(f"<@{uid}>" for uid in aniversariantes)
                e = discord.Embed(
                    title="🎉🎂 Parabéns, Guerreiro(a)!!",
                    description=f"hoje é dia de comemorar!! parabéns {mencoes}!! a CSI toda te deseja o melhor!! 👹🔥🎉",
                    color=COR_DOURADO, timestamp=hoje
                )
                e.set_footer(text="👹 Monstrão • Aniversários")
                try:
                    await canal.send(embed=e)
                except Exception:
                    pass
            self._ultimo_anuncio[guild.id] = chave_hoje

    @checar_aniversarios.before_loop
    async def before_checar(self):
        await self.bot.wait_until_ready()


# ══════════════════════════════════════════════════════════════════
#  🎫  TICKETS — CENTRAL DE SUPORTE CSI
# ══════════════════════════════════════════════════════════════════

def _tickets_dados(guild_id: int) -> dict:
    todos = _load(TICKETS_FILE, {})
    return todos.get(str(guild_id), {})


def _tickets_salvar(guild_id: int, dados: dict) -> None:
    todos = _load(TICKETS_FILE, {})
    todos[str(guild_id)] = dados
    _save(TICKETS_FILE, todos)


class TicketFecharView(discord.ui.View):
    """Botão persistente pra fechar um ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", emoji="🔒", style=discord.ButtonStyle.red, custom_id="monstrao_ticket_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        canal = interaction.channel
        dados = _tickets_dados(interaction.guild.id)
        info = dados.get(str(canal.id))
        if not info:
            await interaction.response.send_message(embed=embed_erro("esse canal não é um ticket controlado pelo Monstrão!!"), ephemeral=True)
            return
        eh_dono = interaction.user.id == info["owner"]
        eh_staff = interaction.user.guild_permissions.manage_channels
        if not (eh_dono or eh_staff):
            await interaction.response.send_message(embed=embed_erro("só quem abriu o ticket ou a staff pode fechar!! 👹"), ephemeral=True)
            return

        await interaction.response.send_message(embed=embed_ok("🔒 Ticket Fechado!!", "esse canal vai sumir em 5 segundinhos!! valeu por passar na CSI!! 👹🔥"))
        info["aberto"] = False
        dados[str(canal.id)] = info
        _tickets_salvar(interaction.guild.id, dados)
        await asyncio.sleep(5)
        try:
            await canal.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception:
            pass


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=chave, description=desc, emoji=emoji)
            for chave, (emoji, label, desc) in TICKET_TIPOS.items()
        ]
        super().__init__(
            placeholder="Selecione uma opção...",
            min_values=1, max_values=1,
            options=options,
            custom_id="monstrao_ticket_select",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        tipo = self.values[0]
        emoji, label, _desc = TICKET_TIPOS[tipo]

        dados = _tickets_dados(guild.id)

        # já tem ticket aberto?
        for cid, info in dados.items():
            if info.get("owner") == member.id and info.get("aberto"):
                canal_existente = guild.get_channel(int(cid))
                if canal_existente:
                    await interaction.response.send_message(
                        embed=embed_erro(f"você já tem um ticket aberto em {canal_existente.mention}!! 👹"), ephemeral=True
                    )
                    return

        cfg = get_config(guild.id)
        categoria_id = cfg.get("ticket_categoria_id") or DEFAULT_TICKET_CATEGORIA_ID
        categoria = guild.get_channel(categoria_id) if categoria_id else None
        if not categoria and categoria_id:
            try:
                categoria = await guild.fetch_channel(categoria_id)
            except Exception:
                categoria = None
        cargo_id = cfg.get("ticket_cargo_id")
        cargo = guild.get_role(cargo_id) if cargo_id else discord.utils.find(
            lambda r: r.name.lower() == "staff", guild.roles
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        nome_canal = f"ticket-{tipo}-{member.name}".lower()[:95]
        try:
            canal = await guild.create_text_channel(
                nome_canal, category=categoria, overwrites=overwrites,
                reason=f"Ticket de {label} aberto por {member}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=embed_erro("sem permissão pra criar o canal do ticket!! 😢"), ephemeral=True)
            return

        dados[str(canal.id)] = {"owner": member.id, "tipo": tipo, "aberto": True}
        _tickets_salvar(guild.id, dados)

        embed = embed_info(
            f"{emoji} Ticket de {label}",
            f"e aí, {member.mention}!! a equipe da CSI já foi avisada!! explica com calma o que precisa que a gente resolve isso rapidinho!! 👹🔥"
        )
        mencao_cargo = cargo.mention if cargo else ""
        try:
            await canal.send(content=f"{member.mention} {mencao_cargo}".strip(), embed=embed, view=TicketFecharView())
        except Exception:
            pass

        await interaction.response.send_message(embed=embed_ok("🎫 Ticket Criado!!", f"seu ticket foi aberto em {canal.mention}!!"), ephemeral=True)


class TicketPainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class TicketCog(commands.Cog, name="MonstraoTickets"):
    """👹 Central de Suporte da CSI — sistema de tickets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _achar_canal_painel(self, guild: discord.Guild, cfg: dict, canal: discord.TextChannel = None):
        """Resolve o canal onde o painel de tickets deve ficar, com fallback pro fetch caso não esteja em cache."""
        if canal:
            return canal
        canal_id = cfg.get("ticket_channel_id") or DEFAULT_TICKET_CHANNEL_ID
        destino = guild.get_channel(canal_id)
        if not destino:
            try:
                destino = await guild.fetch_channel(canal_id)
            except Exception:
                destino = None
        return destino

    async def publicar_painel(self, guild: discord.Guild, canal: discord.TextChannel = None):
        """Monta e envia o embed do painel de tickets, salvando o canal/mensagem pra próxima checagem automática."""
        cfg = get_config(guild.id)
        destino = await self._achar_canal_painel(guild, cfg, canal)
        if not destino:
            return None

        set_config_value(guild.id, "ticket_channel_id", destino.id)

        imagem_url = cfg.get("ticket_imagem_url") or DEFAULT_TICKET_IMG_URL
        thumb_url = cfg.get("ticket_thumb_url") or DEFAULT_TICKET_THUMB_URL

        linhas_tipos = "\n".join(
            f"{emoji} **{label}** — {desc}" for emoji, label, desc in TICKET_TIPOS.values()
        )

        embed = discord.Embed(
            title="🛡️ Central de Suporte CSI 💚🦇",
            description=(
                "e aí, guerreiro(a)!! bateu uma dúvida, quer fechar parceria com a CSI, topa entrar "
                "pra staff ou precisa denunciar alguma zoeira fora da linha? 👹\n\n"
                "abre um ticket ali embaixo que a nossa equipe corre pra te atender!!\n\n"
                f"{linhas_tipos}"
            ),
            color=COR_VERDE,
        )
        embed.set_image(url=imagem_url)
        embed.set_thumbnail(url=thumb_url)
        embed.set_footer(text="🦇 Cuidado Sedutores da Internet")

        try:
            msg = await destino.send(embed=embed, view=TicketPainelView())
        except discord.Forbidden:
            return None

        set_config_value(guild.id, "ticket_panel_message_id", msg.id)
        return msg

    @commands.Cog.listener()
    async def on_ready(self):
        """Lança o painel de tickets sozinho assim que o bot liga — sem precisar rodar m!ticketpainel na mão.
        Só publica de novo se o painel antigo tiver sumido (canal ainda sem painel ou mensagem apagada)."""
        for guild in self.bot.guilds:
            cfg = get_config(guild.id)
            destino = await self._achar_canal_painel(guild, cfg)
            if not destino:
                continue

            msg_id = cfg.get("ticket_panel_message_id")
            painel_ainda_existe = False
            if msg_id:
                try:
                    await destino.fetch_message(msg_id)
                    painel_ainda_existe = True
                except Exception:
                    painel_ainda_existe = False

            if not painel_ainda_existe:
                await self.publicar_painel(guild, destino)

    @commands.command(name="ticketpainel")
    @commands.has_permissions(manage_guild=True)
    async def ticket_painel(self, ctx: commands.Context, canal: discord.TextChannel = None):
        msg = await self.publicar_painel(ctx.guild, canal)
        if not msg:
            await ctx.send(embed=embed_erro("não consegui publicar o painel!! confere se eu tenho permissão de ver/mandar mensagem nesse canal!! 😢"))
            return
        await ctx.send(embed=embed_ok("✅ Painel Publicado!!", f"central de suporte no ar em {msg.channel.mention}!! 🎫👹"))

    @commands.command(name="setticketcategoria")
    @commands.has_permissions(manage_guild=True)
    async def set_ticket_categoria(self, ctx: commands.Context, categoria: discord.CategoryChannel):
        set_config_value(ctx.guild.id, "ticket_categoria_id", categoria.id)
        await ctx.send(embed=embed_ok("✅ Categoria de Tickets Definida!!", f"os tickets vão nascer dentro de **{categoria.name}**!! 👹"))

    @commands.command(name="setcargosuporte")
    @commands.has_permissions(manage_guild=True)
    async def set_cargo_suporte(self, ctx: commands.Context, cargo: discord.Role):
        set_config_value(ctx.guild.id, "ticket_cargo_id", cargo.id)
        await ctx.send(embed=embed_ok("✅ Cargo de Suporte Definido!!", f"{cargo.mention} vai poder ver e responder todos os tickets!! 👹"))

    @commands.command(name="setticketimagens")
    @commands.has_permissions(manage_guild=True)
    async def set_ticket_imagens(self, ctx: commands.Context, url_grande: str, url_pequena: str = None):
        set_config_value(ctx.guild.id, "ticket_imagem_url", url_grande)
        if url_pequena:
            set_config_value(ctx.guild.id, "ticket_thumb_url", url_pequena)
        await ctx.send(embed=embed_ok(
            "✅ Imagens Atualizadas!!",
            "as próximas vezes que você mandar `m!ticketpainel` vão usar essas imagens novas!! 👹\n"
            "(útil se o link antigo expirar, já que links do CDN do Discord vencem depois de um tempo)"
        ))


# ══════════════════════════════════════════════════════════════════
#  🐲  EVENTOS GLOBAIS DO BOT
# ══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"\n{'═'*52}")
    print("  👹  MONSTRÃO BOT — ONLINE")
    print(f"  Logado como: {bot.user} ({bot.user.id})")
    print(f"  Servidores: {len(bot.guilds)}")
    print(f"{'═'*52}\n")

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="a CSI de olho, sempre alerta 👹🔥")
    )

    for guild in bot.guilds:
        cfg = get_config(guild.id)
        ch = guild.get_channel(cfg.get("log_chat_id")) if cfg.get("log_chat_id") else None
        if ch:
            embed = discord.Embed(
                description=(
                    "```\n"
                    "╔══════════════════════════════════════╗\n"
                    "║        👹  MONSTRÃO BOT  🔥          ║\n"
                    "║          — v1.0  ONLINE —            ║\n"
                    "║      Bot Oficial da CSI               ║\n"
                    "╚══════════════════════════════════════╝\n"
                    "```"
                ),
                color=COR_ROXO, timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(name="MONSTRÃO • Sistemas Iniciados", icon_url=bot.user.display_avatar.url)
            embed.add_field(name="✅ Módulos Ativos", inline=False, value=(
                "🎙️ VoiceMaster — Calls Temporárias\n"
                "📋 Logs de Voz — entradas/saídas de call\n"
                "📝 Logs de Chat — msgs editadas/apagadas\n"
                "👋 Boas-Vindas — recepção de membros\n"
                "💌 Log de Convites — quem convidou quem\n"
                "🎂 Aniversários — parabéns automático\n"
                "💬 Diálogo — aprendizado conversacional"
            ))
            embed.set_footer(text="👹 Monstrão Bot • use m!configinfo pra ver os canais")
            try:
                await ch.send(embed=embed)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════
#  📋  COMANDOS GERAIS
# ══════════════════════════════════════════════════════════════════

@bot.command(name="help", aliases=["ajuda", "h"])
async def monstrao_help(ctx: commands.Context):
    embed = embed_info(
        "👹 Monstrão Bot — Ajuda",
        "e aí, guerreiro(a)!! sou o Monstrão, bot oficial da CSI!! olha tudo que eu sei fazer!! 🔥",
        cor=COR_ROXO
    )
    embed.add_field(name="🎙️ VoiceMaster (Calls)", inline=False, value=(
        "`m!vm setup [categoria]` — configura o lobby\n"
        "`m!vm reset [categoria]` — recria o lobby\n"
        "`m!vm setpainel #canal` — canal fixo do painel\n"
        "`m!vm info` — status do sistema\n"
        "*(use os botões do painel pra gerenciar sua call)*"
    ))
    embed.add_field(name="⚙️ Configuração", inline=False, value=(
        "`m!setlogvoz #canal` · `m!setlogchat #canal`\n"
        "`m!setwelcome #canal` · `m!setconvites #canal`\n"
        "`m!setaniversario #canal` · `m!configinfo`"
    ))
    embed.add_field(name="🎂 Aniversários", inline=False, value=(
        "manda `DD/MM` no canal configurado pra registrar\n"
        "`m!meuniver [DD/MM]` · `m!proximosniver`"
    ))
    embed.add_field(name="💬 Diálogo & Aprendizado", inline=False, value=(
        "`m!ensinar <gatilho> <resposta>` · `m!esquecer <gatilho>`\n"
        "`m!gatilhos` · `m!resposta <gatilho>` · `m!simular <texto>`"
    ))
    embed.add_field(name="📋 Logs", inline=False, value="automático, assim que os canais forem configurados!!")
    embed.add_field(name="🎫 Tickets (Central de Suporte)", inline=False, value=(
        "`m!ticketpainel [#canal]` — publica/atualiza o painel de tickets\n"
        "`m!setticketcategoria <categoria>` — onde os tickets nascem\n"
        "`m!setcargosuporte @cargo` — cargo que enxerga todos os tickets\n"
        "`m!setticketimagens <url_grande> [url_pequena]` — troca as imagens do painel"
    ))
    embed.set_footer(text="👹 Monstrão Bot • prefixo: m!")
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    latencia = round(bot.latency * 1000)
    cor = COR_OK if latencia < 100 else (COR_DOURADO if latencia < 200 else COR_ERRO)
    await ctx.send(embed=discord.Embed(title="🏓 Pong!!", description=f"latência: `{latencia}ms` 👹🔥", color=cor))


@bot.command(name="monstro", aliases=["monstrao"])
async def monstrao_info(ctx: commands.Context):
    embed = embed_info(
        "👹 Oi!! Sou o Monstrão!!",
        "o monstro oficial da CSI!! 🔥💪\n\n"
        "cuido das calls, guardo os logs, dou as boas-vindas e vou aprendendo a conversar com vocês aos poucos!! 👹\n\n"
        "manda `m!help` pra ver tudo que eu sei fazer!!",
        cor=COR_ROXO
    )
    await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════
#  🚀  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════

async def _main():
    async with bot:
        await bot.add_cog(VoiceMasterCog(bot))
        await bot.add_cog(ConfigCog(bot))
        await bot.add_cog(LogCog(bot))
        await bot.add_cog(WelcomeCog(bot))
        await bot.add_cog(DialogueCog(bot))
        await bot.add_cog(BirthdayCog(bot))
        await bot.add_cog(TicketCog(bot))

        # Registra as views persistentes (sobrevivem a restarts)
        bot.add_view(VMPainelView(bot.cogs["MonstraoVoiceMaster"]))
        bot.add_view(TicketPainelView())
        bot.add_view(TicketFecharView())

        if not TOKEN:
            print("❌ ERRO: token não encontrado! Crie um .env com MONSTRAO_TOKEN=seu_token")
            return
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(_main())
