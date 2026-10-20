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
import io
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
CONVITES_FILE    = os.path.join(DATA_DIR, "monstrao_convites.json")   # contagem de convites (persistente)
VOZ_TEMPO_FILE   = os.path.join(DATA_DIR, "monstrao_voz_tempo.json")  # tempo total em call por membro (persistente)

# Ranking de tempo em call (.vercallmembros / m!vercallmembros)
RANKING_CALL_TOP        = 10    # quantos membros aparecem no ranking
RANKING_CALL_APAGAR_EM  = 300   # segundos até apagar a mensagem do ranking (5 minutos)

# Ranking FIXO (ao vivo): uma mensagem que fica sempre no canal abaixo e é editada a cada minuto.
# Diferente do comando, ela nunca é apagada. Pode ser trocado com m!setrankingcall #canal
DEFAULT_RANKING_CALL_CHANNEL_ID = 1559420312552996915
RANKING_FIXO_TOP                = 25    # quantos membros aparecem no ranking fixo

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

# Canal padrão do log de convites (usado quando m!setconvites ainda não foi configurado)
DEFAULT_INVITE_LOG_CHANNEL_ID = 1554532119865200670

# Canal padrão de log de tickets (usado quando m!setlogtickets ainda não foi configurado) —
# recebe o log detalhado de TODOS os eventos de ticket (abertura, reivindicação e fechamento),
# de TODAS as centrais (suporte, recrutamento e qualquer central customizada).
DEFAULT_TICKET_LOG_CHANNEL_ID = 1547789898919182426

# Canal que recebe o alerta do comando m!investigar (contas suspeitas de serem a mesma pessoa/IP)
CANAL_INVESTIGAR_ID = 1304658654292869206

# Fuso usado nos horários DENTRO do arquivo de transcript (Brasília = UTC-3)
FUSO_BR = timezone(timedelta(hours=-3))

# Máximo de mensagens lidas pro transcript (proteção pra tickets gigantes)
TRANSCRIPT_LIMITE_MENSAGENS = 5000

# Se True, também manda o transcript na DM de quem abriu o ticket
ENVIAR_TRANSCRIPT_DM_DONO = False

# Guarda os tickets que já estão sendo fechados (evita clique duplo no botão)
_TICKETS_FECHANDO: set = set()

# Cargo que, ao ser concedido a um membro, dispara uma mensagem de boas-vindas
# especial (com imagem) no canal definido logo abaixo.
CARGO_BOAS_VINDAS_ESPECIAL_ID = 1522444449651626024
CANAL_BOAS_VINDAS_ESPECIAL_ID = 1499002824627847299
IMAGEM_BOAS_VINDAS_ESPECIAL_URL = "https://cdn.discordapp.com/attachments/926913851172204577/1547980609769709699/ChatGPT_Image_11_de_set._de_2026_11_42_01.png?ex=6aa564c9&is=6aa41349&hm=9dd59c0c3fd0c1b4755d8eb3f835ff34abd12b7d944fb150d66880c589e25124"

# Cargo de Visitante — ao ser concedido, dispara sua própria mensagem de
# boas-vindas (com imagem) sempre no canal fixo definido abaixo.
CARGO_VISITANTE_ID = 1499002622881828924
CANAL_VISITANTE_ID = 1499002824627847299
IMAGEM_VISITANTE_URL = "https://cdn.discordapp.com/attachments/926913851172204577/1553980703362777138/ChatGPT_Image_28_de_set._de_2026_01_04_15.png?ex=6abb38cf&is=6ab9e74f&hm=21fb4f6e0bd8a1b15fcfd52692a4b2739ccde2558d8f3440bcb22a74fa3dae4e"

# Cargo que, ao ser concedido a um membro, dispara uma mensagem de PARCERIA
# (com imagem) sempre no canal fixo definido abaixo.
CARGO_PARCERIA_ID = 1499002646651080794
CANAL_PARCERIA_ID = 1499002824627847299
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
            "seja_staff":  ("🧑💼", "Seja Staff", "Quer entrar pra equipe de staff da CSI"),
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
            "convidados":   ("🎟️", "Convidados!", "Foi convidado(a) por alguém da CSI"),
            "parceria":     ("🤝", "Parceria", "Quer fechar uma parceria com a CSI"),
        },
    },
}

# Tipos da central de Recrutamento que devem receber a Ficha de Recrutamento
# automática 10s depois de abrir o ticket. "Mudança de Nick" usa a mesma central
# (mesma staff, mesmo painel) mas NÃO é uma candidatura, então fica de fora daqui.
TIPOS_QUE_RECEBEM_FICHA_RECRUTAMENTO = {"recrutamento", "recrutamento2"}

# Tipos da central de Recrutamento que recebem a Ficha de Parceria automática
# 10s depois de abrir o ticket.
TIPOS_QUE_RECEBEM_FICHA_PARCERIA = {"parceria"}

# Tipos da central de Recrutamento que recebem a Ficha de Convidados automática
# 10s depois de abrir o ticket.
TIPOS_QUE_RECEBEM_FICHA_CONVIDADOS = {"convidados"}


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
    # Escrita atômica: grava num arquivo temporário e troca no final. Assim, se o bot cair
    # no meio do salvamento, o arquivo antigo continua íntegro (nada de JSON cortado/zerado).
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


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
#  💌  CONVITES — contagem persistente (fica no /data, não zera ao reiniciar)
# ══════════════════════════════════════════════════════════════════

def _convites_dados(guild_id: int) -> dict:
    todos = _load(CONVITES_FILE, {})
    d = todos.get(str(guild_id), {})
    d.setdefault("contagem", {})   # inviter_id -> total de convites
    d.setdefault("membros", {})    # member_id  -> {"inviter": id, "code": "abc"}
    return d


def _convites_salvar(guild_id: int, dados: dict) -> None:
    todos = _load(CONVITES_FILE, {})
    todos[str(guild_id)] = dados
    _save(CONVITES_FILE, todos)


def registrar_convite(guild_id: int, member_id: int, inviter_id: int, code: str) -> int:
    """Salva no /data quem convidou quem e devolve o total atual do convidador.
    Se o mesmo membro sair e voltar pelo convite da mesma pessoa, não conta duas vezes."""
    dados = _convites_dados(guild_id)
    anterior = dados["membros"].get(str(member_id))
    if not (anterior and anterior.get("inviter") == inviter_id):
        dados["contagem"][str(inviter_id)] = dados["contagem"].get(str(inviter_id), 0) + 1
    dados["membros"][str(member_id)] = {"inviter": inviter_id, "code": code}
    _convites_salvar(guild_id, dados)
    return dados["contagem"].get(str(inviter_id), 0)


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
        embed.add_field(name="💌 Convites", value=fmt("invite_log_id", DEFAULT_INVITE_LOG_CHANNEL_ID), inline=True)
        embed.add_field(name="🎂 Aniversários", value=fmt("birthday_channel_id"), inline=True)
        embed.add_field(name="🤝 Parcerias", value=fmt("parceria_channel_id"), inline=True)
        embed.add_field(name="🎙️ Lobby VM", value=fmt("vm_lobby_id"), inline=True)
        embed.add_field(name="🎫 Log de Tickets", value=fmt("ticket_log_channel_id", DEFAULT_TICKET_LOG_CHANNEL_ID), inline=True)
        embed.add_field(name="🏆 Ranking de Call", value=fmt("ranking_call_channel_id", DEFAULT_RANKING_CALL_CHANNEL_ID), inline=True)
        await ctx.send(embed=embed)


# ══════════════════════════════════════════════════════════════════
#  🏆  RANKING DE TEMPO EM CALL
# ══════════════════════════════════════════════════════════════════

def _fmt_tempo_call(segundos: float) -> str:
    """Formata segundos como '12h 05min' (ou '5min 30s' pra tempos curtos)."""
    segundos = max(0, int(segundos))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h}h {m:02d}min"
    if m:
        return f"{m}min {s:02d}s"
    return f"{s}s"


class CallRankingCog(commands.Cog, name="MonstraoCallRanking"):
    """👹 Conta o tempo que cada membro passa em call e monta o ranking."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # (guild_id, user_id) -> timestamp (epoch) de quando começamos a contar o tempo atual
        self.entrada: dict[tuple[int, int], float] = {}
        self._seeded = False
        self._canais_invalidos: set = set()   # (guild_id, channel_id) que não deu pra acessar
        self._lock_ranking = asyncio.Lock()
        self.salvar_tempo_periodico.start()

    def cog_unload(self):
        self.salvar_tempo_periodico.cancel()
        # ao desligar o bot, grava o que estava em andamento (não perde nem o último minuto)
        try:
            self._flush_sessoes()
        except Exception as ex:
            print(f"[ranking call] f... (113 KB restante(s))
