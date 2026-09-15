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
CENTRAIS_CUSTOM_FILE = os.path.join(DATA_DIR, "monstrao_centrais_custom.json")

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

# Canal e categoria padrão da central de Recrutamento (segundo painel, separado do de suporte)
DEFAULT_RECRUTAMENTO_CHANNEL_ID   = 1547787977562783845
DEFAULT_RECRUTAMENTO_CATEGORIA_ID = 1499002717526556682

# Canal padrão de boas-vindas (usado quando m!setwelcome ainda não foi configurado)
DEFAULT_WELCOME_CHANNEL_ID = 1499002798434680944

# Canal padrão de log de tickets (usado quando m!setlogtickets ainda não foi configurado) —
# recebe o log detalhado de TODOS os eventos de ticket (abertura, reivindicação e fechamento),
# de TODAS as centrais (suporte, recrutamento e qualquer central customizada).
DEFAULT_TICKET_LOG_CHANNEL_ID = 1547789898919182426

# Cargo que, ao ser concedido a um membro, dispara uma mensagem de boas-vindas
# especial (com imagem) no canal definido logo abaixo.
CARGO_BOAS_VINDAS_ESPECIAL_ID = 1499002622881828924
CANAL_BOAS_VINDAS_ESPECIAL_ID = 1499002824627847299
IMAGEM_BOAS_VINDAS_ESPECIAL_URL = "https://cdn.discordapp.com/attachments/926913851172204577/1547980609769709699/ChatGPT_Image_11_de_set._de_2026_11_42_01.png?ex=6aa564c9&is=6aa41349&hm=9dd59c0c3fd0c1b4755d8eb3f835ff34abd12b7d944fb150d66880c589e25124"

# Cargo que, ao ser concedido a um membro, dispara uma mensagem de PARCERIA
# (com imagem) no canal configurado com m!setparceria #canal.
CARGO_PARCERIA_ID = 1499002646651080794
IMAGEM_PARCERIA_URL = "https://cdn.discordapp.com/attachments/926913851172204577/1549443648444309584/ChatGPT_Image_15_de_set._de_2026_12_35_40.png?ex=6aaab759&is=6aa965d9&hm=3b2b98ff2fcde5f71857d4630f34aa955124df623da1ded84a2219d6ea7d06d0"

# Cargos que sempre podem ver e reivindicar os tickets da central de Recrutamento
# (independente de qual cargo estiver configurado com m!setcargoticket recrutamento @cargo)
RECRUTAMENTO_STAFF_ROLE_IDS = [
    1499002605194706995,
    1547958453530525747,
    1547958619268714569,
    1547958651459870741,
]

# ══════════════════════════════════════════════════════════════════
#  🎫  CENTRAIS DE TICKET — cada chave é um painel independente,
#      com seu próprio canal, categoria e opções no select.
# ══════════════════════════════════════════════════════════════════
TICKET_CENTRAIS = {
    "suporte": {
        "nome_config":  "ticket",   # prefixo usado nas chaves salvas em CONFIG_FILE
        "titulo":       "🛡️ Central de Suporte CSI 💚🦇",
        "intro": (
            "e aí, guerreiro(a)!! bateu uma dúvida, quer fechar parceria com a CSI, topa entrar "
            "pra staff ou precisa denunciar alguma zoeira fora da linha? 👹\n\n"
            "abre um ticket ali embaixo que a nossa equipe corre pra te atender!!"
        ),
        "canal_padrao_id":    DEFAULT_TICKET_CHANNEL_ID,
        "categoria_padrao_id": DEFAULT_TICKET_CATEGORIA_ID,
        "usar_imagens": True,   # usa as imagens padrão/configuráveis do painel principal
        # tipo -> (emoji, label, descrição curta pro select)
        "tipos": {
            "suporte":     ("🛟", "Suporte",     "Dúvidas, ajuda geral e problemas no servidor"),
            "parceria":    ("🤝", "Parceria",    "Quer fechar uma parceria com a CSI"),
            "reclamacao":  ("⚠️", "Reclamação", "Denúncias e quebra de regras"),
            "seja_staff":  ("🧑‍💼", "Seja Staff", "Quer entrar pra equipe de staff da CSI"),
        },
    },
    "recrutamento": {
        "nome_config":  "ticket_recrutamento",
        "titulo":       "📋 Recrutamento CSI 🦇",
        "intro": (
            "topa fazer parte da equipe da CSI?? 👹🔥\n\n"
            "abre um ticket de recrutamento ali embaixo que a staff vem falar com você!!"
        ),
        "canal_padrao_id":    DEFAULT_RECRUTAMENTO_CHANNEL_ID,
        "categoria_padrao_id": DEFAULT_RECRUTAMENTO_CATEGORIA_ID,
        "usar_imagens": False,
        "tipos": {
            "recrutamento": ("📋", "Recrutamento", "Quer se candidatar pra entrar na equipe da CSI"),
            "recrutamento2": ("📋", "Recrutamento 2", "Quer se candidatar pra entrar na equipe da CSI"),
            "mudanca_nick": ("✏️", "Mudança de Nick", "Quer pedir uma mudança de nick"),
        },
    },
}

# Tipos da central de Recrutamento que devem receber a Ficha de Recrutamento
# automática 10s depois de abrir o ticket. "Mudança de Nick" usa a mesma central
# (mesma staff, mesmo painel) mas NÃO é uma candidatura, então fica de fora daqui.
TIPOS_QUE_RECEBEM_FICHA_RECRUTAMENTO = {"recrutamento", "recrutamento2"}


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
#  🎫  CENTRAIS CUSTOM — permite criar novas centrais de ticket
#      (além de Suporte/Recrutamento) sem editar o código.
# ══════════════════════════════════════════════════════════════════

def _centrais_custom(guild_id: int) -> dict:
    todos = _load(CENTRAIS_CUSTOM_FILE, {})
    return todos.get(str(guild_id), {})


def _centrais_custom_salvar(guild_id: int, dados: dict) -> None:
    todos = _load(CENTRAIS_CUSTOM_FILE, {})
    todos[str(guild_id)] = dados
    _save(CENTRAIS_CUSTOM_FILE, todos)


def get_todas_centrais(guild_id: int) -> dict:
    """Centrais fixas (suporte/recrutamento) + as customizadas criadas nesse servidor."""
    todas = dict(TICKET_CENTRAIS)
    todas.update(_centrais_custom(guild_id))
    return todas


def get_central(guild_id: int, central_key: str):
    return get_todas_centrais(guild_id).get(central_key)


def resolver_central_para_view(central_key: str):
    """Usada só na hora de registrar as Views persistentes (antes/sem saber a guild
    certa). Procura primeiro nas centrais fixas, depois em qualquer servidor que
    já tenha uma central custom com essa chave."""
    if central_key in TICKET_CENTRAIS:
        return TICKET_CENTRAIS[central_key]
    todos_customs = _load(CENTRAIS_CUSTOM_FILE, {})
    for centrais_da_guild in todos_customs.values():
        if central_key in centrais_da_guild:
            return centrais_da_guild[central_key]
    return None


def todas_chaves_centrais_existentes() -> set:
    chaves = set(TICKET_CENTRAIS.keys())
    todos_customs = _load(CENTRAIS_CUSTOM_FILE, {})
    for centrais_da_guild in todos_customs.values():
        chaves.update(centrais_da_guild.keys())
    return chaves


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

    @commands.command(name="setparceria")
    @commands.has_permissions(manage_guild=True)
    async def set_parceria(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "parceria_channel_id", canal.id)
        await ctx.send(embed=embed_ok(
            "✅ Canal de Parcerias Definido!!",
            f"toda vez que alguém ganhar o cargo de parceria eu vou comemorar em {canal.mention}!! 🤝👹"
        ))

    @commands.command(name="configinfo")
    @commands.has_permissions(manage_guild=True)
    async def config_info(self, ctx: commands.Context):
        cfg = get_config(ctx.guild.id)

        def fmt(key, default_id: int = None):
            cid = cfg.get(key) or default_id
            ch = ctx.guild.get_channel(cid) if cid else None
            if ch:
                return f"{ch.mention}" + (" `(padrão)`" if not cfg.get(key) and default_id else "")
            return "❌ não configurado"

        embed = embed_info("⚙️ Config Atual do Monstrão", "")
        embed.add_field(name="📞 Log de Voz", value=fmt("log_call_id"), inline=True)
        embed.add_field(name="📝 Log de Chat", value=fmt("log_chat_id"), inline=True)
        embed.add_field(name="👋 Boas-Vindas", value=fmt("welcome_channel_id", DEFAULT_WELCOME_CHANNEL_ID), inline=True)
        embed.add_field(name="💌 Convites", value=fmt("invite_log_id"), inline=True)
        embed.add_field(name="🎂 Aniversários", value=fmt("birthday_channel_id"), inline=True)
        embed.add_field(name="🤝 Parcerias", value=fmt("parceria_channel_id"), inline=True)
        embed.add_field(name="🎙️ Lobby VM", value=fmt("vm_lobby_id"), inline=True)
        embed.add_field(name="🎫 Log de Tickets", value=fmt("ticket_log_channel_id", DEFAULT_TICKET_LOG_CHANNEL_ID), inline=True)
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
        welcome_id = cfg.get("welcome_channel_id") or DEFAULT_WELCOME_CHANNEL_ID
        if welcome_id:
            ch = guild.get_channel(welcome_id)
            if not ch:
                try:
                    ch = await guild.fetch_channel(welcome_id)
                except Exception:
                    ch = None
            if ch:
                e = discord.Embed(
                    title="🦇💚 Ain, chegou gente nova!!",
                    description=(
                        f"oiii {member.mention}, seja muito bem-vindo(a) à família CSI!! 🥰🔥\n\n"
                        f"a gente fica super feliz de ter você por aqui!! dá uma olhada nos canais "
                        f"pra se ambientar e, qualquer dúvida, é só chamar a staff!!\n\n"
                        f"ah, e se um dia bater aquela vontade de fazer parte da equipe, tem um "
                        f"ticket de recrutamento em <#{DEFAULT_RECRUTAMENTO_CHANNEL_ID}> 💚🦇"
                    ),
                    color=COR_VERDE, timestamp=datetime.now(timezone.utc)
                )
                if member.display_avatar:
                    e.set_thumbnail(url=member.display_avatar.url)
                e.set_footer(text=f"👹 Monstrão • agora somos {guild.member_count}")
                try:
                    await ch.send(content=member.mention, embed=e)
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

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # ── Cargo especial → manda boas-vindas com imagem no canal dedicado ──
        cargos_antes = {r.id for r in before.roles}
        cargos_depois = {r.id for r in after.roles}

        # só dispara quando o cargo é GANHO agora (não tinha antes e tem depois)
        if CARGO_BOAS_VINDAS_ESPECIAL_ID in cargos_depois and CARGO_BOAS_VINDAS_ESPECIAL_ID not in cargos_antes:
            guild = after.guild
            canal = guild.get_channel(CANAL_BOAS_VINDAS_ESPECIAL_ID)
            if not canal:
                try:
                    canal = await guild.fetch_channel(CANAL_BOAS_VINDAS_ESPECIAL_ID)
                except Exception:
                    canal = None

            if canal:
                e = discord.Embed(
                    title="🎉🦇 Ain, olha quem subiu de nível!!",
                    description=(
                        f"parabéns, {after.mention}!! você acabou de conquistar um cargo novo "
                        f"aqui na família CSI!! 💚🔥\n\nque venham muitas outras conquistas, "
                        f"guerreiro(a)!! a gente tá muito feliz com você por aqui!! 👹"
                    ),
                    color=COR_VERDE, timestamp=datetime.now(timezone.utc)
                )
                e.set_image(url=IMAGEM_BOAS_VINDAS_ESPECIAL_URL)
                e.set_footer(text="👹 Monstrão • CSI")
                try:
                    await canal.send(content=after.mention, embed=e)
                except Exception:
                    pass

        # ── Cargo de parceria → comemora a nova parceria fechada com a CSI ──
        if CARGO_PARCERIA_ID in cargos_depois and CARGO_PARCERIA_ID not in cargos_antes:
            guild = after.guild
            canal_id = get_config(guild.id).get("parceria_channel_id")
            canal = guild.get_channel(canal_id) if canal_id else None
            if not canal and canal_id:
                try:
                    canal = await guild.fetch_channel(canal_id)
                except Exception:
                    canal = None

            if canal:
                e = discord.Embed(
                    title="🤝🦇 Nova Parceria Fechada!!",
                    description=(
                        f"aeeeee, {after.mention}!! é com o maior orgulho que anunciamos: fechamos "
                        f"parceria com vocês!! 🔥💚\n\n"
                        f"a partir de hoje, CSI e vocês caminham lado a lado — uma força a mais pra "
                        f"gente crescer junto, trocar ideia e fazer a network bombar!! 👹🤝\n\n"
                        f"que essa parceria renda muita coisa boa pros dois lados e dure pra sempre, "
                        f"guerreiro(a)!! seja muito bem-vindo(a) à família CSI!! 🦇💜"
                    ),
                    color=COR_VERDE, timestamp=datetime.now(timezone.utc)
                )
                e.set_image(url=IMAGEM_PARCERIA_URL)
                e.set_footer(text="👹 Monstrão • CSI")
                try:
                    await canal.send(content=after.mention, embed=e)
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
#  🎫  TICKETS — CENTRAIS DE SUPORTE E RECRUTAMENTO DA CSI
# ══════════════════════════════════════════════════════════════════

def _tickets_dados(guild_id: int) -> dict:
    todos = _load(TICKETS_FILE, {})
    return todos.get(str(guild_id), {})


def _tickets_salvar(guild_id: int, dados: dict) -> None:
    todos = _load(TICKETS_FILE, {})
    todos[str(guild_id)] = dados
    _save(TICKETS_FILE, todos)


# ── Ficha automática de Recrutamento ───────────────

FICHA_RECRUTAMENTO_INTRO = (
    "{mention}, chegou a hora!! preenche a ficha abaixo certinho que, assim que você "
    "terminar, é só aguardar que um staff da CSI vem finalizar seu atendimento com "
    "você!! 👹🔥"
)


def embed_ficha_recrutamento() -> discord.Embed:
    e = discord.Embed(
        title="Ficha de Recrutamento🦇💚",
        description=(
            "> **User do Discord:** \n"
            "> **User do roblox:** \n"
            "> **Nome de exibição do roblox:** \n"
            "> **Idade:** \n"
            "> **Quanto tempo joga Roblox:** \n"
            "> **Quanto tempo tem sua conta do discord:** \n\n"
            "> **Já Participou de outros clãs? se sim diga quais:** \n\n"
            "> *Por fim, nossas cores são preto e verde, concorda e aceita mesmo assim, "
            "e então se tornar um sedutor da Internet??*\n\n"
            "> **Sim [ ]  Não [ ]**"
        ),
        color=COR_VERDE,
    )
    e.set_footer(text="🦇 Cuidado Sedutores da Internet")
    return e


# ── Log detalhado de tickets ───────────────────────
#
# Cada evento importante do ciclo de vida de um ticket (abertura, reivindicação
# e fechamento) gera um embed rico e cai no canal configurado com
# `m!setlogtickets #canal` — ou, se nada for configurado, direto no
# DEFAULT_TICKET_LOG_CHANNEL_ID. Funciona pra QUALQUER central (suporte,
# recrutamento ou uma central customizada criada com `m!novacentral`).

def _fmt_duracao(segundos: float) -> str:
    """Formata uma duração em segundos como algo tipo '1d 2h 14min'."""
    segundos = max(0, int(segundos))
    dias, resto = divmod(segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, _ = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos or not partes:
        partes.append(f"{minutos}min")
    return " ".join(partes)


def _contar_tickets_central(guild_id: int, central_key: str) -> int:
    """Quantos tickets (histórico completo, abertos + fechados) essa central já teve."""
    dados = _tickets_dados(guild_id)
    return sum(1 for info in dados.values() if info.get("central") == central_key)


async def log_ticket_evento(guild: discord.Guild, embed: discord.Embed) -> None:
    """Manda um embed de log de ticket pro canal configurado com `m!setlogtickets`
    (ou pro DEFAULT_TICKET_LOG_CHANNEL_ID, se nada foi configurado ainda)."""
    cfg = get_config(guild.id)
    canal_id = cfg.get("ticket_log_channel_id") or DEFAULT_TICKET_LOG_CHANNEL_ID
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if not canal:
        try:
            canal = await guild.fetch_channel(canal_id)
        except Exception:
            return
    try:
        await canal.send(embed=embed)
    except Exception:
        pass


def _central_label(central_key: str, central: dict = None) -> str:
    if central:
        return f"`{central_key}` — {central.get('titulo', central_key)}"
    return f"`{central_key}`"


def embed_log_ticket_criado(member: discord.Member, canal: discord.TextChannel, central_key: str, central: dict, tipo: str) -> discord.Embed:
    emoji, label, _desc = central["tipos"].get(tipo, ("🎫", tipo, ""))
    total = _contar_tickets_central(canal.guild.id, central_key)
    ts = int(datetime.now(timezone.utc).timestamp())

    e = discord.Embed(
        title=f"{emoji} Ticket Aberto",
        color=COR_OK,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_author(name=f"{member} • abriu um ticket", icon_url=member.display_avatar.url)
    e.add_field(name="👤 Aberto por", value=f"{member.mention}\n`{member.id}`", inline=True)
    e.add_field(name="📁 Central", value=_central_label(central_key, central), inline=True)
    e.add_field(name="🏷️ Tipo", value=f"{emoji} {label}", inline=True)
    e.add_field(name="💬 Canal", value=f"{canal.mention}\n`#{canal.name}`", inline=True)
    e.add_field(name="🕒 Quando", value=f"<t:{ts}:F>\n<t:{ts}:R>", inline=True)
    e.add_field(name="📊 Nº nessa central", value=f"`{total}º` ticket", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=f"👹 Monstrão • Log de Tickets • ID do canal: {canal.id}")
    return e


def embed_log_ticket_reivindicado(member: discord.Member, canal: discord.TextChannel, info: dict, central: dict = None) -> discord.Embed:
    ts = int(datetime.now(timezone.utc).timestamp())
    e = discord.Embed(
        title="🙋 Ticket Reivindicado",
        color=COR_DOURADO,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_author(name=f"{member} • assumiu o atendimento", icon_url=member.display_avatar.url)
    e.add_field(name="🙋 Reivindicado por", value=f"{member.mention}\n`{member.id}`", inline=True)
    e.add_field(name="👤 Dono do Ticket", value=f"<@{info.get('owner')}>", inline=True)
    e.add_field(name="📁 Central", value=_central_label(info.get("central", "?"), central), inline=True)
    e.add_field(name="🏷️ Tipo", value=f"`{info.get('tipo', '—')}`", inline=True)
    e.add_field(name="💬 Canal", value=f"{canal.mention}\n`#{canal.name}`", inline=True)
    e.add_field(name="🕒 Quando", value=f"<t:{ts}:F>\n<t:{ts}:R>", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=f"👹 Monstrão • Log de Tickets • ID do canal: {canal.id}")
    return e


def embed_log_ticket_fechado(member: discord.Member, canal: discord.TextChannel, info: dict, central: dict = None) -> discord.Embed:
    ts = int(datetime.now(timezone.utc).timestamp())

    duracao_txt = "desconhecida"
    aberto_em_str = info.get("aberto_em")
    if aberto_em_str:
        try:
            aberto_em = datetime.fromisoformat(aberto_em_str)
            duracao_txt = _fmt_duracao((datetime.now(timezone.utc) - aberto_em).total_seconds())
        except Exception:
            pass

    e = discord.Embed(
        title="🔒 Ticket Fechado",
        color=COR_ERRO,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_author(name=f"{member} • fechou o ticket", icon_url=member.display_avatar.url)
    e.add_field(name="🔒 Fechado por", value=f"{member.mention}\n`{member.id}`", inline=True)
    e.add_field(name="👤 Dono do Ticket", value=f"<@{info.get('owner')}>", inline=True)

    claimed_by = info.get("claimed_by")
    e.add_field(name="🙋 Reivindicado por", value=f"<@{claimed_by}>" if claimed_by else "*ninguém reivindicou*", inline=True)

    e.add_field(name="📁 Central", value=_central_label(info.get("central", "?"), central), inline=True)
    e.add_field(name="🏷️ Tipo", value=f"`{info.get('tipo', '—')}`", inline=True)
    e.add_field(name="⏱️ Tempo Aberto", value=duracao_txt, inline=True)
    e.add_field(name="💬 Canal", value=f"`#{canal.name}`\n`{canal.id}`", inline=True)
    e.add_field(name="🕒 Fechado em", value=f"<t:{ts}:F>\n<t:{ts}:R>", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=f"👹 Monstrão • Log de Tickets • ID do canal: {canal.id}")
    return e


class TicketFecharView(discord.ui.View):
    """Botão persistente pra fechar um ticket (funciona pra qualquer central)."""

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
        info["fechado_por"] = interaction.user.id
        info["fechado_em"] = datetime.now(timezone.utc).isoformat()
        dados[str(canal.id)] = info
        _tickets_salvar(interaction.guild.id, dados)

        # 📋 Log detalhado do fechamento
        try:
            central = get_central(interaction.guild.id, info.get("central", "suporte"))
            await log_ticket_evento(interaction.guild, embed_log_ticket_fechado(interaction.user, canal, info, central))
        except Exception:
            pass

        await asyncio.sleep(5)
        try:
            await canal.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception:
            pass


class TicketFecharReivindicarView(discord.ui.View):
    """Fechar + Reivindicar — usado nos tickets da central de Recrutamento, pros
    cargos definidos em RECRUTAMENTO_STAFF_ROLE_IDS conseguirem assumir o atendimento."""

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
        info["fechado_por"] = interaction.user.id
        info["fechado_em"] = datetime.now(timezone.utc).isoformat()
        dados[str(canal.id)] = info
        _tickets_salvar(interaction.guild.id, dados)

        # 📋 Log detalhado do fechamento
        try:
            central = get_central(interaction.guild.id, info.get("central", "recrutamento"))
            await log_ticket_evento(interaction.guild, embed_log_ticket_fechado(interaction.user, canal, info, central))
        except Exception:
            pass

        await asyncio.sleep(5)
        try:
            await canal.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception:
            pass

    @discord.ui.button(label="Reivindicar", emoji="🙋", style=discord.ButtonStyle.green, custom_id="monstrao_ticket_reivindicar")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        canal = interaction.channel
        guild = interaction.guild
        dados = _tickets_dados(guild.id)
        info = dados.get(str(canal.id))
        if not info:
            await interaction.response.send_message(embed=embed_erro("esse canal não é um ticket controlado pelo Monstrão!!"), ephemeral=True)
            return

        membro = interaction.user
        tem_cargo = any(r.id in RECRUTAMENTO_STAFF_ROLE_IDS for r in membro.roles)
        if not (tem_cargo or membro.guild_permissions.manage_channels):
            await interaction.response.send_message(embed=embed_erro("só a staff de recrutamento pode reivindicar esse ticket!! 👹"), ephemeral=True)
            return

        if info.get("claimed_by"):
            dono_atual = guild.get_member(info["claimed_by"])
            nome_atual = dono_atual.mention if dono_atual else "alguém"
            await interaction.response.send_message(embed=embed_erro(f"esse ticket já foi reivindicado por {nome_atual}!! 🤔"), ephemeral=True)
            return

        info["claimed_by"] = membro.id
        dados[str(canal.id)] = info
        _tickets_salvar(guild.id, dados)
        await interaction.response.send_message(embed=embed_ok("🙋 Reivindicado!!", f"{membro.mention} vai cuidar desse atendimento a partir de agora!! 👹🔥"))

        # 📋 Log detalhado da reivindicação
        try:
            central = get_central(guild.id, info.get("central", "recrutamento"))
            await log_ticket_evento(guild, embed_log_ticket_reivindicado(membro, canal, info, central))
        except Exception:
            pass


class TicketSelect(discord.ui.Select):
    """Select genérico — cada central de ticket (suporte, recrutamento, etc.) usa uma instância
    própria, identificada por central_key, apontando pro TICKET_CENTRAIS (ou pra uma central
    custom) correspondente."""

    def __init__(self, central_key: str, central_para_options: dict = None):
        self.central_key = central_key
        central = central_para_options or resolver_central_para_view(central_key) or {"tipos": {}}
        tipos = central.get("tipos") or {"placeholder": ("❔", "Sem opções", "Ainda não há opções configuradas")}
        options = [
            discord.SelectOption(label=label, value=chave, description=desc, emoji=emoji)
            for chave, (emoji, label, desc) in tipos.items()
        ]
        super().__init__(
            placeholder="Selecione uma opção...",
            min_values=1, max_values=1,
            options=options,
            custom_id=f"monstrao_ticket_select_{central_key}",
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        central = get_central(guild.id, self.central_key)
        if not central:
            await interaction.response.send_message(embed=embed_erro("essa central de ticket não existe mais!! avisa a staff!! 🤔"), ephemeral=True)
            return
        prefixo = central["nome_config"]
        tipo = self.values[0]
        if tipo not in central["tipos"]:
            await interaction.response.send_message(embed=embed_erro("essa opção não existe mais nessa central!! tenta de novo!! 🤔"), ephemeral=True)
            return
        emoji, label, _desc = central["tipos"][tipo]

        dados = _tickets_dados(guild.id)

        # sem limite de "um ticket por vez" — o mesmo usuário pode abrir quantos
        # tickets quiser na mesma central, mesmo com outro(s) já aberto(s).

        cfg = get_config(guild.id)
        categoria_id = cfg.get(f"{prefixo}_categoria_id") or central["categoria_padrao_id"]
        categoria = guild.get_channel(categoria_id) if categoria_id else None
        if not categoria and categoria_id:
            try:
                categoria = await guild.fetch_channel(categoria_id)
            except Exception:
                categoria = None

        cargo_id = cfg.get(f"{prefixo}_cargo_id") or cfg.get("ticket_cargo_id")
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

        # Central de Recrutamento: os cargos fixos definidos em RECRUTAMENTO_STAFF_ROLE_IDS
        # sempre enxergam esses tickets e podem reivindicar, além do cargo configurado (se houver).
        eh_recrutamento = self.central_key == "recrutamento"
        if eh_recrutamento:
            for role_id in RECRUTAMENTO_STAFF_ROLE_IDS:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        nome_canal = f"ticket-{tipo}-{member.name}".lower()[:95]
        try:
            canal = await guild.create_text_channel(
                nome_canal, category=categoria, overwrites=overwrites,
                reason=f"Ticket de {label} aberto por {member}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=embed_erro("sem permissão pra criar o canal do ticket!! 😢"), ephemeral=True)
            return

        dados[str(canal.id)] = {
            "owner": member.id,
            "tipo": tipo,
            "aberto": True,
            "central": self.central_key,
            "claimed_by": None,
            "aberto_em": datetime.now(timezone.utc).isoformat(),
        }
        _tickets_salvar(guild.id, dados)

        embed = embed_info(
            f"{emoji} Ticket de {label}",
            f"e aí, {member.mention}!! a equipe da CSI já foi avisada!! explica com calma o que precisa que a gente resolve isso rapidinho!! 👹🔥"
        )
        mencao_cargo = cargo.mention if cargo else ""
        view_ticket = TicketFecharReivindicarView() if eh_recrutamento else TicketFecharView()
        try:
            await canal.send(content=f"{member.mention} {mencao_cargo}".strip(), embed=embed, view=view_ticket)
        except Exception:
            pass

        # 📋 Log detalhado — registra a abertura do ticket no canal de logs
        try:
            await log_ticket_evento(guild, embed_log_ticket_criado(member, canal, self.central_key, central, tipo))
        except Exception:
            pass

        # Central de Recrutamento: manda a Ficha de Recrutamento automaticamente 10s depois
        # — mas só pra quem tá de fato se candidatando (Recrutamento / Recrutamento 2).
        # "Mudança de Nick" usa a mesma central/staff, mas não é uma candidatura, então
        # não faz sentido mandar a ficha de recrutamento nesse caso.
        if eh_recrutamento and tipo in TIPOS_QUE_RECEBEM_FICHA_RECRUTAMENTO:
            async def _enviar_ficha():
                await asyncio.sleep(10)
                try:
                    await canal.send(
                        content=FICHA_RECRUTAMENTO_INTRO.format(mention=member.mention),
                        embed=embed_ficha_recrutamento(),
                    )
                except Exception:
                    pass
            asyncio.create_task(_enviar_ficha())

        await interaction.response.send_message(embed=embed_ok("🎫 Ticket Criado!!", f"seu ticket foi aberto em {canal.mention}!!"), ephemeral=True)


class TicketPainelView(discord.ui.View):
    def __init__(self, central_key: str = "suporte", central_para_options: dict = None):
        super().__init__(timeout=None)
        self.central_key = central_key
        self.add_item(TicketSelect(central_key, central_para_options))


class TicketCog(commands.Cog, name="MonstraoTickets"):
    """👹 Centrais de Suporte, Recrutamento e outras (customizadas) da CSI — sistema de tickets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Trava pra publicar os painéis só 1x por processo. O discord.py pode disparar
        # on_ready mais de uma vez na vida do bot (ex: depois de uma reconexão) — sem essa
        # trava, cada reconexão rodava o loop de publicação de novo, o que (junto com
        # qualquer falhazinha de rede/timing no fetch_message) é a receita pra ir
        # acumulando painéis duplicados no canal a cada restart/reconexão.
        self._paineis_publicados = False

    async def _achar_canal_painel(self, guild: discord.Guild, cfg: dict, central: dict, canal: discord.TextChannel = None):
        """Resolve o canal onde o painel dessa central deve ficar, com fallback pro fetch caso não esteja em cache."""
        if canal:
            return canal
        canal_id = cfg.get(f"{central['nome_config']}_channel_id") or central.get("canal_padrao_id")
        if not canal_id:
            return None
        destino = guild.get_channel(canal_id)
        if not destino:
            try:
                destino = await guild.fetch_channel(canal_id)
            except Exception:
                destino = None
        return destino

    def _montar_embed(self, guild: discord.Guild, central: dict) -> discord.Embed:
        cfg = get_config(guild.id)
        linhas_tipos = "\n".join(
            f"{emoji} **{label}** — {desc}" for emoji, label, desc in central["tipos"].values()
        ) or "*(nenhuma opção configurada ainda)*"

        embed = discord.Embed(
            title=central["titulo"],
            description=f"{central['intro']}\n\n{linhas_tipos}",
            color=COR_VERDE,
        )
        if central.get("usar_imagens"):
            imagem_url = cfg.get("ticket_imagem_url") or DEFAULT_TICKET_IMG_URL
            thumb_url = cfg.get("ticket_thumb_url") or DEFAULT_TICKET_THUMB_URL
            embed.set_image(url=imagem_url)
            embed.set_thumbnail(url=thumb_url)
        embed.set_footer(text="🦇 Cuidado Sedutores da Internet")
        return embed

    async def publicar_painel(self, guild: discord.Guild, central_key: str, canal: discord.TextChannel = None):
        """Publica (ou ATUALIZA, se já existir) o painel de uma central específica.

        1) Se já tem uma mensagem de painel salva em CONFIG_FILE e ela ainda existe no
           Discord, o Monstrão EDITA ela em vez de mandar uma nova.
        2) Depois de garantir a mensagem certa, varre as últimas mensagens do canal e
           apaga qualquer OUTRO painel dessa mesma central que tenha sobrado por lá
           (de execuções antigas antes desse fix, ou de qualquer falhazinha) — assim
           só fica UM painel publicado, sempre, mesmo que já tenha duplicado antes."""
        central = get_central(guild.id, central_key)
        if not central:
            return None
        prefixo = central["nome_config"]
        cfg = get_config(guild.id)
        destino = await self._achar_canal_painel(guild, cfg, central, canal)
        if not destino:
            return None

        embed = self._montar_embed(guild, central)
        view = TicketPainelView(central_key, central)

        msg_id = cfg.get(f"{prefixo}_panel_message_id")
        msg_final = None

        if msg_id:
            try:
                msg_existente = await destino.fetch_message(msg_id)
                # já existe e tá no mesmo canal -> edita em vez de duplicar
                await msg_existente.edit(embed=embed, view=view)
                set_config_value(guild.id, f"{prefixo}_channel_id", destino.id)
                msg_final = msg_existente
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # painel antigo sumiu (ou mudou de canal) -> cai pra criar um novo

        if msg_final is None:
            set_config_value(guild.id, f"{prefixo}_channel_id", destino.id)
            try:
                msg_final = await destino.send(embed=embed, view=view)
            except discord.Forbidden:
                return None
            set_config_value(guild.id, f"{prefixo}_panel_message_id", msg_final.id)

        # 🧹 limpeza: apaga qualquer outro painel dessa central que tenha sobrado no
        # canal (mensagens do próprio bot com o mesmo título de embed), garantindo
        # que só fica UM painel no ar mesmo que já tenha duplicado antes desse fix.
        try:
            async for msg in destino.history(limit=50):
                if msg.id == msg_final.id or msg.author.id != guild.me.id:
                    continue
                if msg.embeds and msg.embeds[0].title == central["titulo"]:
                    try:
                        await msg.delete()
                    except Exception:
                        pass
        except Exception:
            pass

        return msg_final

    @commands.Cog.listener()
    async def on_ready(self):
        """Lança todos os painéis de ticket (fixos + customizados) sozinho assim que o bot
        liga — sem precisar rodar os comandos na mão. publicar_painel já cuida de editar
        em vez de duplicar caso o painel ainda exista (e limpa duplicatas antigas).

        Roda só uma vez por processo (ver self._paineis_publicados): o discord.py pode
        chamar on_ready de novo depois de reconexões, e sem essa trava esse loop rodava
        toda vez, o que era a causa dos painéis sendo remandados."""
        if self._paineis_publicados:
            return
        self._paineis_publicados = True
        for guild in self.bot.guilds:
            for central_key in get_todas_centrais(guild.id):
                await self.publicar_painel(guild, central_key)

    @commands.command(name="ticketpainel")
    @commands.has_permissions(manage_guild=True)
    async def ticket_painel(self, ctx: commands.Context, canal: discord.TextChannel = None):
        msg = await self.publicar_painel(ctx.guild, "suporte", canal)
        if not msg:
            await ctx.send(embed=embed_erro("não consegui publicar o painel!! confere se eu tenho permissão de ver/mandar mensagem nesse canal!! 😢"))
            return
        await ctx.send(embed=embed_ok("✅ Painel Atualizado!!", f"central de suporte no ar em {msg.channel.mention}!! 🎫👹"))

    @commands.command(name="ticketpainelrecrutamento", aliases=["painelrecrutamento"])
    @commands.has_permissions(manage_guild=True)
    async def ticket_painel_recrutamento(self, ctx: commands.Context, canal: discord.TextChannel = None):
        msg = await self.publicar_painel(ctx.guild, "recrutamento", canal)
        if not msg:
            await ctx.send(embed=embed_erro("não consegui publicar o painel!! confere se eu tenho permissão de ver/mandar mensagem nesse canal!! 😢"))
            return
        await ctx.send(embed=embed_ok("✅ Painel Atualizado!!", f"central de recrutamento no ar em {msg.channel.mention}!! 📋👹"))

    # ── Sistema genérico de centrais (crie quantas quiser!) ──────

    @commands.command(name="novacentral")
    @commands.has_permissions(manage_guild=True)
    async def nova_central(self, ctx: commands.Context, chave: str, *, titulo_e_intro: str):
        """Cria uma nova central de ticket do zero.
        Uso: m!novacentral <chave> <Título> | <texto de introdução>
        Ex.: m!novacentral eventos 🎉 Central de Eventos CSI | topa organizar um evento com a gente?? abre um ticket ali embaixo!!
        """
        chave = chave.lower().strip()
        if not re.fullmatch(r"[a-z0-9_]+", chave):
            await ctx.send(embed=embed_erro("a chave só pode ter letras minúsculas, números e `_` (sem espaço/acento)!! ex: `eventos`, `denuncia_staff` 🥲"))
            return
        if chave in get_todas_centrais(ctx.guild.id):
            await ctx.send(embed=embed_erro(f"já existe uma central com a chave `{chave}`!! usa outra ou apaga ela primeiro com `m!removercentral {chave}` 🤔"))
            return

        if "|" in titulo_e_intro:
            titulo, intro = titulo_e_intro.split("|", 1)
        else:
            titulo, intro = titulo_e_intro, "abre um ticket ali embaixo que a equipe da CSI já vem te atender!! 👹"

        nova = {
            "nome_config": f"ticket_{chave}",
            "titulo": titulo.strip(),
            "intro": intro.strip(),
            "canal_padrao_id": None,
            "categoria_padrao_id": None,
            "usar_imagens": False,
            "tipos": {},
        }
        customs = _centrais_custom(ctx.guild.id)
        customs[chave] = nova
        _centrais_custom_salvar(ctx.guild.id, customs)
        self.bot.add_view(TicketPainelView(chave, nova))  # já registra a view pra funcionar depois de restart

        await ctx.send(embed=embed_ok(
            "🎉 Central Criada!!",
            f"central **`{chave}`** criada!! agora:\n"
            f"1️⃣ `m!addtipoticket {chave} <tipo> <emoji> <label> | <descrição>` — adiciona pelo menos uma opção\n"
            f"2️⃣ `m!setcategoriaticket {chave} <categoria>` — categoria onde os canais nascem\n"
            f"3️⃣ `m!publicarcentral {chave} #canal` — publica o painel!! 👹🔥"
        ))

    @commands.command(name="addtipoticket")
    @commands.has_permissions(manage_guild=True)
    async def add_tipo_ticket(self, ctx: commands.Context, chave: str, tipo_id: str, emoji: str, *, label_e_desc: str):
        """Adiciona uma opção (tipo) ao select de uma central.
        Uso: m!addtipoticket <chave> <tipo_id> <emoji> <Label> | <descrição curta>
        """
        chave = chave.lower().strip()
        tipo_id = tipo_id.lower().strip()
        central = get_central(ctx.guild.id, chave)
        if not central:
            await ctx.send(embed=embed_erro(f"não existe central com a chave `{chave}`!! confere com `m!listarcentrais` 🤔"))
            return

        if "|" in label_e_desc:
            label, desc = label_e_desc.split("|", 1)
        else:
            label, desc = label_e_desc, "Selecione essa opção pra abrir esse tipo de ticket"

        if chave in TICKET_CENTRAIS:
            # centrais fixas ficam só em memória (não persistidas) — ok pro uso do dia a dia,
            # mas se reiniciar o bot elas voltam ao padrão do código.
            TICKET_CENTRAIS[chave]["tipos"][tipo_id] = (emoji, label.strip(), desc.strip())
        else:
            customs = _centrais_custom(ctx.guild.id)
            customs[chave]["tipos"][tipo_id] = (emoji, label.strip(), desc.strip())
            _centrais_custom_salvar(ctx.guild.id, customs)

        self.bot.add_view(TicketPainelView(chave, get_central(ctx.guild.id, chave)))
        await ctx.send(embed=embed_ok(
            "✅ Opção Adicionada!!",
            f"`{tipo_id}` adicionado na central **`{chave}`**!! roda `m!publicarcentral {chave}` pra atualizar o painel!! 👹"
        ))

    @commands.command(name="removertipoticket")
    @commands.has_permissions(manage_guild=True)
    async def remover_tipo_ticket(self, ctx: commands.Context, chave: str, tipo_id: str):
        chave, tipo_id = chave.lower().strip(), tipo_id.lower().strip()
        central = get_central(ctx.guild.id, chave)
        if not central or tipo_id not in central["tipos"]:
            await ctx.send(embed=embed_erro("não achei essa central/opção!! confere com `m!listarcentrais` 🤔"))
            return
        if chave in TICKET_CENTRAIS:
            del TICKET_CENTRAIS[chave]["tipos"][tipo_id]
        else:
            customs = _centrais_custom(ctx.guild.id)
            del customs[chave]["tipos"][tipo_id]
            _centrais_custom_salvar(ctx.guild.id, customs)
        await ctx.send(embed=embed_ok("🗑️ Opção Removida!!", f"`{tipo_id}` removido da central **`{chave}`**!! roda `m!publicarcentral {chave}` pra atualizar o painel!! 👹"))

    @commands.command(name="removercentral")
    @commands.has_permissions(manage_guild=True)
    async def remover_central(self, ctx: commands.Context, chave: str):
        chave = chave.lower().strip()
        if chave in TICKET_CENTRAIS:
            await ctx.send(embed=embed_erro("as centrais `suporte` e `recrutamento` são fixas e não podem ser removidas, só editadas!! 🤔"))
            return
        customs = _centrais_custom(ctx.guild.id)
        if chave not in customs:
            await ctx.send(embed=embed_erro(f"não existe central custom com a chave `{chave}`!! 🤔"))
            return
        del customs[chave]
        _centrais_custom_salvar(ctx.guild.id, customs)
        await ctx.send(embed=embed_ok("🗑️ Central Removida!!", f"central **`{chave}`** apagada!! (o painel antigo publicado precisa ser apagado manualmente no canal) 👹"))

    @commands.command(name="listarcentrais")
    async def listar_centrais(self, ctx: commands.Context):
        todas = get_todas_centrais(ctx.guild.id)
        if not todas:
            await ctx.send(embed=embed_info("📋 Centrais de Ticket", "nenhuma central configurada ainda!!"))
            return
        desc = "\n".join(
            f"• **`{chave}`** — {central['titulo']} (`{len(central['tipos'])}` opção(ões))"
            for chave, central in todas.items()
        )
        await ctx.send(embed=embed_info("📋 Centrais de Ticket", desc))

    @commands.command(name="publicarcentral")
    @commands.has_permissions(manage_guild=True)
    async def publicar_central(self, ctx: commands.Context, chave: str, canal: discord.TextChannel = None):
        """Publica (ou atualiza) o painel de QUALQUER central — fixa ou customizada."""
        chave = chave.lower().strip()
        central = get_central(ctx.guild.id, chave)
        if not central:
            await ctx.send(embed=embed_erro(f"não existe central com a chave `{chave}`!! confere com `m!listarcentrais` 🤔"))
            return
        if not central["tipos"]:
            await ctx.send(embed=embed_erro(f"a central `{chave}` ainda não tem nenhuma opção!! usa `m!addtipoticket {chave} ...` primeiro 🤔"))
            return
        msg = await self.publicar_painel(ctx.guild, chave, canal)
        if not msg:
            await ctx.send(embed=embed_erro("não consegui publicar!! confere se eu tenho permissão nesse canal (ou se você já rodou `m!setcategoriaticket`)!! 😢"))
            return
        await ctx.send(embed=embed_ok("✅ Painel Atualizado!!", f"central **`{chave}`** no ar em {msg.channel.mention}!! 👹🔥"))

    @commands.command(name="setcategoriaticket")
    @commands.has_permissions(manage_guild=True)
    async def set_categoria_ticket(self, ctx: commands.Context, chave: str, categoria: discord.CategoryChannel):
        """Funciona pra qualquer central (suporte, recrutamento ou uma custom)."""
        chave = chave.lower().strip()
        central = get_central(ctx.guild.id, chave)
        if not central:
            await ctx.send(embed=embed_erro(f"não existe central com a chave `{chave}`!! 🤔"))
            return
        set_config_value(ctx.guild.id, f"{central['nome_config']}_categoria_id", categoria.id)
        await ctx.send(embed=embed_ok("✅ Categoria Definida!!", f"os tickets de **`{chave}`** vão nascer dentro de **{categoria.name}**!! 👹"))

    @commands.command(name="setcargoticket")
    @commands.has_permissions(manage_guild=True)
    async def set_cargo_ticket(self, ctx: commands.Context, chave: str, cargo: discord.Role):
        """Funciona pra qualquer central (suporte, recrutamento ou uma custom)."""
        chave = chave.lower().strip()
        central = get_central(ctx.guild.id, chave)
        if not central:
            await ctx.send(embed=embed_erro(f"não existe central com a chave `{chave}`!! 🤔"))
            return
        set_config_value(ctx.guild.id, f"{central['nome_config']}_cargo_id", cargo.id)
        await ctx.send(embed=embed_ok("✅ Cargo Definido!!", f"{cargo.mention} vai poder ver e responder os tickets de **`{chave}`**!! 👹"))

    # ── Comandos antigos (mantidos por compatibilidade) ──────────

    @commands.command(name="setticketcategoria")
    @commands.has_permissions(manage_guild=True)
    async def set_ticket_categoria(self, ctx: commands.Context, categoria: discord.CategoryChannel):
        set_config_value(ctx.guild.id, "ticket_categoria_id", categoria.id)
        await ctx.send(embed=embed_ok("✅ Categoria de Tickets Definida!!", f"os tickets de **suporte** vão nascer dentro de **{categoria.name}**!! 👹"))

    @commands.command(name="setcategoriarecrutamento")
    @commands.has_permissions(manage_guild=True)
    async def set_categoria_recrutamento(self, ctx: commands.Context, categoria: discord.CategoryChannel):
        set_config_value(ctx.guild.id, "ticket_recrutamento_categoria_id", categoria.id)
        await ctx.send(embed=embed_ok("✅ Categoria de Recrutamento Definida!!", f"os tickets de **recrutamento** vão nascer dentro de **{categoria.name}**!! 👹"))

    @commands.command(name="setcargosuporte")
    @commands.has_permissions(manage_guild=True)
    async def set_cargo_suporte(self, ctx: commands.Context, cargo: discord.Role):
        set_config_value(ctx.guild.id, "ticket_cargo_id", cargo.id)
        await ctx.send(embed=embed_ok("✅ Cargo de Suporte Definido!!", f"{cargo.mention} vai poder ver e responder os tickets (suporte e, se não houver um cargo específico, recrutamento também)!! 👹"))

    @commands.command(name="setcargorecrutamento")
    @commands.has_permissions(manage_guild=True)
    async def set_cargo_recrutamento(self, ctx: commands.Context, cargo: discord.Role):
        set_config_value(ctx.guild.id, "ticket_recrutamento_cargo_id", cargo.id)
        await ctx.send(embed=embed_ok("✅ Cargo de Recrutamento Definido!!", f"{cargo.mention} vai poder ver e responder os tickets de recrutamento!! 👹"))

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

    @commands.command(name="setlogtickets")
    @commands.has_permissions(manage_guild=True)
    async def set_log_tickets(self, ctx: commands.Context, canal: discord.TextChannel):
        set_config_value(ctx.guild.id, "ticket_log_channel_id", canal.id)
        await ctx.send(embed=embed_ok("✅ Log de Tickets Definido!!", f"vou registrar abertura, fechamento e reivindicação de TODOS os tickets (qualquer central) em {canal.mention}!! 📋👹"))


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
        "`m!setaniversario #canal` · `m!setparceria #canal`\n"
        "`m!configinfo`"
    ))
    embed.add_field(name="🎂 Aniversários", inline=False, value=(
        "manda `DD/MM` no canal configurado pra registrar\n"
        "`m!meuniver [DD/MM]` · `m!proximosniver`"
    ))
    embed.add_field(name="🤝 Parcerias", inline=False, value=(
        "`m!setparceria #canal` — define onde comemorar novas parcerias\n"
        "*(assim que o cargo de parceria é dado a alguém, eu já mando a mensagem "
        "com a imagem automaticamente!!)*"
    ))
    embed.add_field(name="💬 Diálogo & Aprendizado", inline=False, value=(
        "`m!ensinar <gatilho> <resposta>` · `m!esquecer <gatilho>`\n"
        "`m!gatilhos` · `m!resposta <gatilho>` · `m!simular <texto>`"
    ))
    embed.add_field(name="📋 Logs", inline=False, value="automático, assim que os canais forem configurados!!")
    embed.add_field(name="🎫 Tickets — Suporte & Recrutamento", inline=False, value=(
        "`m!ticketpainel [#canal]` — publica/atualiza o painel de suporte\n"
        "`m!ticketpainelrecrutamento [#canal]` — publica/atualiza o de recrutamento\n"
        "`m!setticketcategoria <categoria>` · `m!setcategoriarecrutamento <categoria>`\n"
        "`m!setcargosuporte @cargo` · `m!setcargorecrutamento @cargo`\n"
        "`m!setticketimagens <url_grande> [url_pequena]`\n"
        "`m!setlogtickets #canal` — canal que recebe o log detalhado de TODOS os tickets\n"
        "*(recrutamento manda a Ficha de Recrutamento automaticamente 10s depois de abrir, "
        "e os cargos fixos configurados podem ver e reivindicar esses tickets)*"
    ))
    embed.add_field(name="🆕 Tickets — Crie Suas Próprias Centrais!!", inline=False, value=(
        "`m!novacentral <chave> <Título> | <intro>` — cria uma central nova do zero\n"
        "`m!addtipoticket <chave> <tipo> <emoji> <Label> | <desc>` — adiciona uma opção\n"
        "`m!removertipoticket <chave> <tipo>` · `m!removercentral <chave>`\n"
        "`m!setcategoriaticket <chave> <categoria>` · `m!setcargoticket <chave> @cargo`\n"
        "`m!publicarcentral <chave> [#canal]` — publica/atualiza o painel\n"
        "`m!listarcentrais` — lista todas as centrais existentes\n"
        "*(todos os painéis sobem sozinhos quando o bot liga, sem duplicar — e todas as "
        "centrais, incluindo as suas customizadas, também caem no log de tickets)*"
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
        for central_key in todas_chaves_centrais_existentes():
            bot.add_view(TicketPainelView(central_key, resolver_central_para_view(central_key)))
        bot.add_view(TicketFecharView())
        bot.add_view(TicketFecharReivindicarView())

        if not TOKEN:
            print("❌ ERRO: token não encontrado! Crie um .env com MONSTRAO_TOKEN=seu_token")
            return
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(_main())
