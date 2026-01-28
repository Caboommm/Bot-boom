import discord
import asyncio 
import mercadopago # Biblioteca do MP
import io
import base64
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 

# --- CONFIGURAÇÕES DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ==============================================================================
# ⚠️ ÁREA DE CONFIGURAÇÃO (PREENCHA AQUI) ⚠️

# 1. COLOQUE O TOKEN DO MERCADO PAGO AQUI (Começa com APP_USR-...)

# 2. CONFIGURAÇÃO DAS CATEGORIAS (IDs que tu mandou)
ID_CATEGORIA_ABERTOS = 1465840660237258925
ID_CATEGORIA_PAGOS = 1465840575029706793

# 3. DADOS DO PRODUTO
NOME_PRODUTO = "Otimização Básica"
PRECO_UNITARIO = 0.05
ESTOQUE = "Ilimitado"

# 4. IMAGENS E LINKS
IMAGEM_LOJA = "https://cdn.discordapp.com/attachments/1463967623233667311/1465808392026067077/Design_sem_nome.png?ex=697a73f2&is=69792272&hm=53eec98d91136d80f668177c3c62fa63ea1891e1be99b661cc121b7da9d15961&"
# ==============================================================================

# Inicializa o SDK do Mercado Pago
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- FUNÇÃO DO TIMER DE INATIVIDADE ---
async def monitorar_ticket(channel):
    await asyncio.sleep(420) # 7 minutos
    try:
        ticket_atualizado = bot.get_channel(channel.id)
        # Se não tiver "aprovado" no nome, deleta
        if ticket_atualizado and "aprovado" not in ticket_atualizado.name:
            await ticket_atualizado.send("⏰ **Tempo esgotado!** O ticket será fechado.")
            await asyncio.sleep(5)
            await ticket_atualizado.delete()
    except:
        pass 

# --- FUNÇÃO QUE VERIFICA O PAGAMENTO SOZINHO (LOOP) ---
async def verificar_pagamento(payment_id, channel, user):
    tentativas = 0
    # Tenta verificar por 10 minutos (120 x 5 segundos)
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

                # 2. Manda o embed de sucesso
                embed_sucesso = discord.Embed(
                    title="🎉 PAGAMENTO APROVADO!",
                    description="O sistema do Mercado Pago confirmou seu PIX automaticamente!",
                    color=0x8708f7
                )
                embed_sucesso.add_field(name="Status", value="✅ Confirmado", inline=True)
                embed_sucesso.set_footer(text="Aguarde um admin para realizar o serviço.")
                
                # Marca a Staff
                await channel.send(f"{user.mention} || <@&1465012346794676253> || **PAGAMENTO CONFIRMADO!**", embed=embed_sucesso)
                return # Para o loop
            
            elif status == "cancelled" or status == "rejected":
                await channel.send("❌ O pagamento foi cancelado ou recusado.")
                return

        except Exception as e:
            print(f"Erro verificando: {e}")

        await asyncio.sleep(5) # Espera 5 segundos
        tentativas += 1

# --- MODAL DE QUANTIDADE ---
class QuantidadeModal(discord.ui.Modal, title="Alterar Quantidade"):
    quantidade = discord.ui.TextInput(
        label="Quantas otimizações tu quer?", 
        placeholder="Ex: 2", 
        min_length=1, 
        max_length=2,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qtd = int(self.quantidade.value)
            if qtd < 1: qtd = 1
        except ValueError:
            qtd = 1
        
        novo_total = qtd * PRECO_UNITARIO
        embed_atualizado = interaction.message.embeds[0]
        embed_atualizado.clear_fields()
        embed_atualizado.add_field(name="Produto", value=f"{qtd}x {NOME_PRODUTO}", inline=False)
        embed_atualizado.add_field(name="Total a Pagar", value=f"**R$ {novo_total:.2f}**", inline=False)
        await interaction.response.edit_message(embed=embed_atualizado)

# --- VIEWS (BOTÕES) ---

class PagamentoView(discord.ui.View):
    def __init__(self, valor_total):
        super().__init__(timeout=None)
        self.valor_total = valor_total 

    @discord.ui.button(label="Gerar PIX", style=discord.ButtonStyle.success, emoji="💠")
    async def pagar_pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer() # Avisa o Discord que o bot tá pensando
        
        user = interaction.user
        
        # Cria a preferência de pagamento no MP
        payment_data = {
            "transaction_amount": float(self.valor_total),
            "description": f"Compra {NOME_PRODUTO} - {user.name}",
            "payment_method_id": "pix",
            "payer": {
                "email": "cliente@generico.com", # MP exige email, usamos um genérico
                "first_name": user.name
            }
        }

        try:
            # Chama a API
            payment_response = sdk.payment().create(payment_data)
            payment = payment_response["response"]
            
            payment_id = payment["id"]
            qr_code_copia_cola = payment["point_of_interaction"]["transaction_data"]["qr_code"]
            qr_code_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]

            # Transforma o base64 em arquivo de imagem pro Discord
            img_bytes = base64.b64decode(qr_code_base64)
            arquivo_img = discord.File(io.BytesIO(img_bytes), filename="qr_pix.png")

            embed_pix = discord.Embed(
                title="💠 QR Code Gerado!",
                description="**Aprovação Automática:** Assim que você pagar, o bot libera o ticket na hora!",
                color=0x8708f7
            )
            embed_pix.add_field(name="Valor", value=f"**R$ {self.valor_total:.2f}**", inline=False)
            embed_pix.set_image(url="attachment://qr_pix.png")
            embed_pix.set_footer(text=f"ID da Transação: {payment_id}")

            # Envia imagem + copia e cola
            await interaction.followup.send(embed=embed_pix, file=arquivo_img)
            await interaction.followup.send(f"**Copia e Cola:**\n```{qr_code_copia_cola}```", ephemeral=True)

            # Inicia o loop de verificação em segundo plano
            bot.loop.create_task(verificar_pagamento(payment_id, interaction.channel, user))
            
            # Remove o botão pra ele não gerar outro pix no mesmo ticket
            self.stop() 

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao conectar com Mercado Pago: {e}", ephemeral=True)
            print(e)

    @discord.ui.button(label="Cancelar compra", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class CarrinhoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Finalizar Compra", style=discord.ButtonStyle.green, emoji="➡️")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        texto_valor = embed.fields[1].value.replace("**", "").replace("R$ ", "")
        try:
            valor_final = float(texto_valor)
        except:
            valor_final = PRECO_UNITARIO

        guild = interaction.guild
        user = interaction.user
        nome_ticket = f"compra-{user.name.lower()}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
            # Cria o canal na categoria "COMPRAS ABERTAS"
            categoria_abertos = guild.get_channel(ID_CATEGORIA_ABERTOS)
            ticket_channel = await guild.create_text_channel(nome_ticket, overwrites=overwrites, category=categoria_abertos)
            
            # Liga o Timer de 7 min
            bot.loop.create_task(monitorar_ticket(ticket_channel))

            embed_pag = discord.Embed(
                title="💳 Checkout", 
                description="Clique abaixo para gerar seu PIX Automático.", 
                color=0x8708f7
            )
            embed_pag.add_field(name="Total a Pagar", value=f"**R$ {valor_final:.2f}**", inline=False)
            
            await ticket_channel.send(content=user.mention, embed=embed_pag, view=PagamentoView(valor_final))
            await interaction.response.send_message(f"✅ Ticket criado: {ticket_channel.mention}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro (Verifique os IDs das categorias): {e}", ephemeral=True)

    @discord.ui.button(label="Alterar quantidade", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def alterar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuantidadeModal())

class BotaoCompra(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Adicionar ao carrinho", style=discord.ButtonStyle.grey, emoji="🛒")
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_carrinho = discord.Embed(title="🛒 Carrinho", color=0x8708f7)
        embed_carrinho.add_field(name="Produto", value=f"1x {NOME_PRODUTO}", inline=False)
        embed_carrinho.add_field(name="Total a Pagar", value=f"**R$ {PRECO_UNITARIO:.2f}**", inline=False)
        
        await interaction.response.send_message(embed=embed_carrinho, view=CarrinhoView(), ephemeral=True)

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f'🔥 {bot.user} tá ON e fodendo todos! lucas cala a boca')

@bot.command()
async def anuncio(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="💣 CABOOM'S OPTIMIZATION", description="**A EXPLOSÃO DE FPS QUE TU PRECISA**", color=0x8708f7)
    texto = """

Cansado de perder trocação porque o PC deu aquela engasgada na hora H? 😤

🔥 Vem com a Caboom's Optimization!

🚀 Transformamos tua BOMBA (PC fraco) pra rodar liso.
☢️ Turbinamos tua BOMBA NUCLEAR (PC forte) pro competitivo.

O que tu ganha:
✅ Mais FPS
✅ Menor Input Lag
✅ Windows Otimizado
✅ PC Formatado

👇 Brota aqui no <#1465012347386069031> e faça seu pedido!
    """
    embed.add_field(name="⠀", value=texto, inline=False)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1465821639647166665/1465821796266676316/Logo_otimi.jpg?ex=697a806d&is=69792eed&hm=085fd68d744f54e7d060ff7dd1302dc0e2f798a5ccef824ba73c57861683000b&")
    embed.set_thumbnail(url="")
    await ctx.send(embed=embed)

@bot.command()
async def loja(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title=f"✨ {NOME_PRODUTO}", description="```Para comprar basta clicar no botão abaixo...```", color=0x8708f7)
    embed.add_field(name="💰 Preço", value=f"**R$ {PRECO_UNITARIO:.2f}**", inline=True)
    if IMAGEM_LOJA.startswith("http"):
        embed.set_image(url=IMAGEM_LOJA)
    embed.set_footer(text="Caboom's Store")
    await ctx.send(embed=embed, view=BotaoCompra())


import os

bot.run(os.getenv("TOKEN"))