import discord
import asyncio 
import mercadopago # Biblioteca do MP
import io
import os
import base64
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 

# --- CONFIGURAÇÕES DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # OBRIGATÓRIO PARA DAR CARGOS
bot = commands.Bot(command_prefix='!', intents=intents)

# ==============================================================================
# ⚠️ ÁREA DE CONFIGURAÇÃO (PREENCHA AQUI) ⚠️

# 1. TOKEN DO MERCADO PAGO
MP_ACCESS_TOKEN = os.getenv("TOKENMP")

# 2. CATEGORIAS (IDs)
ID_CATEGORIA_ABERTOS = 1465840660237258925
ID_CATEGORIA_PAGOS = 1465840575029706793

# 3. PRODUTO
NOME_PRODUTO = "Otimização Básica"
PRECO_UNITARIO = 35.00
ESTOQUE = "Ilimitado"

# 4. CARGOS (IDs) - ATENÇÃO AQUI 👇
# ID do cargo que a pessoa ganha quando ENTRA no servidor
ID_AUTOROLE_ENTRADA = 1465012346794676253 

# ID do cargo que a pessoa ganha quando COMPRA (Paga o Pix)
ID_CARGO_CLIENTE = 1465012346794676253 # <--- TROQUE PELO ID DO CARGO "CLIENTE"

# 5. IMAGENS
IMAGEM_LOJA = "https://cdn.discordapp.com/attachments/1463967623233667311/1465808392026067077/Design_sem_nome.png?ex=697a73f2&is=69792272&hm=53eec98d91136d80f668177c3c62fa63ea1891e1be99b661cc121b7da9d15961&"
# ==============================================================================

# Inicializa o SDK
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- FUNÇÃO DO TIMER ---
async def monitorar_ticket(channel):
    await asyncio.sleep(420) # 7 minutos
    try:
        ticket_atualizado = bot.get_channel(channel.id)
        if ticket_atualizado and "aprovado" not in ticket_atualizado.name:
            await ticket_atualizado.send("⏰ **Tempo esgotado!** O ticket será fechado.")
            await asyncio.sleep(5)
            await ticket_atualizado.delete()
    except:
        pass 

# --- FUNÇÃO QUE VERIFICA O PAGAMENTO E DÁ O CARGO ---
async def verificar_pagamento(payment_id, channel, user):
    tentativas = 0
    while tentativas < 120:
        try:
            payment_info = sdk.payment().get(payment_id)
            status = payment_info["response"]["status"]
            
            if status == "approved":
                # === PAGAMENTO APROVADO! ===
                
                # 1. Muda o nome e a categoria
                novo_nome = f"✅-aprovado-{user.name.lower()}"
                categoria_pagos = channel.guild.get_channel(ID_CATEGORIA_PAGOS)
                
                if categoria_pagos:
                    await channel.edit(name=novo_nome, category=categoria_pagos)
                else:
                    await channel.edit(name=novo_nome)

                # 2. DÁ O CARGO DE CLIENTE (NOVO CÓDIGO AQUI 👇)
                guild = channel.guild
                role_cliente = guild.get_role(ID_CARGO_CLIENTE)
                if role_cliente:
                    try:
                        await user.add_roles(role_cliente)
                        msg_cargo = f"✅ Cargo {role_cliente.mention} adicionado!"
                    except:
                        msg_cargo = "⚠️ Não consegui dar o cargo (verifique minhas permissões)."
                else:
                    msg_cargo = "⚠️ ID do cargo de cliente não encontrado."

                # 3. Manda o embed de sucesso
                embed_sucesso = discord.Embed(
                    title="🎉 PAGAMENTO APROVADO!",
                    description="O sistema confirmou seu PIX automaticamente!",
                    color=0x8708f7
                )
                embed_sucesso.add_field(name="Status", value="✅ Confirmado", inline=True)
                embed_sucesso.add_field(name="Entrega", value=msg_cargo, inline=False)
                embed_sucesso.set_footer(text="Aguarde um admin para realizar o serviço.")
                
                await channel.send(f"{user.mention} || <@&1465012346794676253> || **PAGAMENTO CONFIRMADO!**", embed=embed_sucesso)
                return 
            
            elif status == "cancelled" or status == "rejected":
                await channel.send("❌ O pagamento foi cancelado ou recusado.")
                return

        except Exception as e:
            print(f"Erro verificando: {e}")

        await asyncio.sleep(5)
        tentativas += 1

# --- RESTO DO CÓDIGO (Igual) ---
class QuantidadeModal(discord.ui.Modal, title="Alterar Quantidade"):
    quantidade = discord.ui.TextInput(label="Quantas otimizações?", placeholder="Ex: 2", min_length=1, max_length=2, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try: qtd = int(self.quantidade.value)
        except: qtd = 1
        if qtd < 1: qtd = 1
        novo_total = qtd * PRECO_UNITARIO
        embed = interaction.message.embeds[0]
        embed.clear_fields()
        embed.add_field(name="Produto", value=f"{qtd}x {NOME_PRODUTO}", inline=False)
        embed.add_field(name="Total a Pagar", value=f"**R$ {novo_total:.2f}**", inline=False)
        await interaction.response.edit_message(embed=embed)

class PagamentoView(discord.ui.View):
    def __init__(self, valor_total):
        super().__init__(timeout=None)
        self.valor_total = valor_total 
    @discord.ui.button(label="Gerar PIX", style=discord.ButtonStyle.success, emoji="💠")
    async def pagar_pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user = interaction.user
        payment_data = {
            "transaction_amount": float(self.valor_total),
            "description": f"Compra {NOME_PRODUTO} - {user.name}",
            "payment_method_id": "pix",
            "payer": {"email": "cliente@generico.com", "first_name": user.name}
        }
        try:
            payment = sdk.payment().create(payment_data)["response"]
            payment_id = payment["id"]
            qr_code = payment["point_of_interaction"]["transaction_data"]["qr_code"]
            qr_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
            img_bytes = base64.b64decode(qr_base64)
            arquivo_img = discord.File(io.BytesIO(img_bytes), filename="qr_pix.png")
            embed_pix = discord.Embed(title="💠 QR Code Gerado!", description="Aprovação Automática.", color=0x8708f7)
            embed_pix.add_field(name="Valor", value=f"**R$ {self.valor_total:.2f}**", inline=False)
            embed_pix.set_image(url="attachment://qr_pix.png")
            embed_pix.set_footer(text=f"ID: {payment_id}")
            await interaction.followup.send(embed=embed_pix, file=arquivo_img)
            await interaction.followup.send(f"**Copia e Cola:**\n```{qr_code}```", ephemeral=True)
            bot.loop.create_task(verificar_pagamento(payment_id, interaction.channel, user))
            self.stop() 
        except Exception as e:
            await interaction.followup.send(f"❌ Erro MP: {e}", ephemeral=True)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class CarrinhoView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Finalizar Compra", style=discord.ButtonStyle.green, emoji="➡️")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        try: valor_final = float(embed.fields[1].value.replace("**", "").replace("R$ ", ""))
        except: valor_final = PRECO_UNITARIO
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        try:
            cat = guild.get_channel(ID_CATEGORIA_ABERTOS)
            ticket = await guild.create_text_channel(f"compra-{user.name.lower()}", overwrites=overwrites, category=cat)
            bot.loop.create_task(monitorar_ticket(ticket))
            embed_pag = discord.Embed(title="💳 Checkout", description="Clique abaixo para pagar.", color=0x8708f7)
            embed_pag.add_field(name="Total", value=f"**R$ {valor_final:.2f}**", inline=False)
            await ticket.send(user.mention, embed=embed_pag, view=PagamentoView(valor_final))
            await interaction.response.send_message(f"✅ Ticket: {ticket.mention}", ephemeral=True)
        except Exception as e: await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)
    @discord.ui.button(label="Alterar Qtd", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def alterar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuantidadeModal())

class BotaoCompra(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Adicionar ao carrinho", style=discord.ButtonStyle.grey, emoji="🛒")
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 Carrinho", color=0x8708f7)
        embed.add_field(name="Produto", value=f"1x {NOME_PRODUTO}", inline=False)
        embed.add_field(name="Total", value=f"**R$ {PRECO_UNITARIO:.2f}**", inline=False)
        await interaction.response.send_message(embed=embed, view=CarrinhoView(), ephemeral=True)

# --- EVENTO DE AUTO-ROLE (ENTROU NO SERVIDOR) ---
@bot.event
async def on_member_join(member):
    role = member.guild.get_role(ID_AUTOROLE_ENTRADA)
    if role:
        try: await member.add_roles(role)
        except: pass

@bot.event
async def on_ready():
    print(f'🔥 {bot.user} tá ON! lucas cala a boca')

@bot.command()
async def anuncio(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="💣 CABOOM'S OPTIMIZATION", description="**A EXPLOSÃO DE FPS QUE TU PRECISA**", color=0x8708f7)
    embed.add_field(name="⠀", value="Cansado de PC lento? Vem com a Caboom!\n👇 Compre abaixo!", inline=False)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1465821639647166665/1465821796266676316/Logo_otimi.jpg?ex=697a806d&is=69792eed&hm=085fd68d744f54e7d060ff7dd1302dc0e2f798a5ccef824ba73c57861683000b&")
    await ctx.send(embed=embed)

@bot.command()
async def loja(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title=f"✨ {NOME_PRODUTO}", description="```Clique no botão para comprar```", color=0x8708f7)
    embed.add_field(name="💰 Preço", value=f"**R$ {PRECO_UNITARIO:.2f}**", inline=True)
    if IMAGEM_LOJA.startswith("http"): embed.set_image(url=IMAGEM_LOJA)
    embed.set_footer(text="Caboom's Store")
    await ctx.send(embed=embed, view=BotaoCompra())

bot.run(os.getenv("TOKEN"))
