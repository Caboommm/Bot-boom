import discord
import asyncio 
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput # Importando o Modal

# --- CONFIGURAÇÕES DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ==============================================================================
# ⚠️ ÁREA DE CONFIGURAÇÃO DAS CATEGORIAS (PREENCHA AQUI) ⚠️
# Ative o Modo Desenvolvedor no Discord -> Clique com botão direito na Categoria -> Copiar ID
ID_CATEGORIA_ABERTOS = 1465840660237258925  # <--- COLA O ID DA CATEGORIA "COMPRAS" AQUI
ID_CATEGORIA_PAGOS = 1465840575029706793    # <--- COLA O ID DA CATEGORIA "PAGAMENTOS" AQUI
# ==============================================================================

# --- DADOS DO PRODUTO ---
NOME_PRODUTO = "Otimização Básica"
PRECO_UNITARIO = 35.00 # Coloca numero puro aqui pra fazer conta (sem R$)
ESTOQUE = "Ilimitado"

# IMAGENS E LINKS
IMAGEM_LOJA = "https://cdn.discordapp.com/attachments/1463967623233667311/1465808392026067077/Design_sem_nome.png?ex=697a73f2&is=69792272&hm=53eec98d91136d80f668177c3c62fa63ea1891e1be99b661cc121b7da9d15961&"
IMAGEM_QR_CODE = "https://cdn.discordapp.com/attachments/1465012347386069025/1465810934546170001/image.png?ex=697a7650&is=697924d0&hm=3a41269e73600bd27b936d2dbeb8c2656da56e258f00ae2b7ac7a410756bcd0d&" 
PIX_COPIA_COLA = "00020126360014BR.GOV.BCB.PIX0114+552299879181452040000530398654040.015802BR5919Davi Azevedo Cabral6009SAO PAULO62140510cbKNi7cOjm630460CD" 
LINK_MERCADO_PAGO = "https://mercadopago.com.br" 

# --- MODAL DE QUANTIDADE (A JANELINHA POP-UP) ---
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
            if qtd < 1:
                qtd = 1
        except ValueError:
            qtd = 1 # Se o cara digitar letra, assume 1
        
        # Calcula o novo total
        novo_total = qtd * PRECO_UNITARIO
        
        # Atualiza o Embed do carrinho
        embed_atualizado = interaction.message.embeds[0]
        embed_atualizado.clear_fields() # Limpa os campos velhos
        embed_atualizado.add_field(name="Produto", value=f"{qtd}x {NOME_PRODUTO}", inline=False)
        embed_atualizado.add_field(name="Total a Pagar", value=f"**R$ {novo_total:.2f}**", inline=False)
        
        # Atualiza a mensagem
        await interaction.response.edit_message(embed=embed_atualizado)

# --- FUNÇÃO DO TIMER ---
async def monitorar_ticket(channel):
    await asyncio.sleep(420) 
    try:
        ticket_atualizado = bot.get_channel(channel.id)
        if ticket_atualizado and "pago" not in ticket_atualizado.name:
            await ticket_atualizado.send("⏰ **Tempo esgotado!** O ticket será fechado.")
            await asyncio.sleep(5)
            await ticket_atualizado.delete()
    except:
        pass 

# --- VIEWS (BOTÕES) ---

class PixView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Link Mercado Pago", style=discord.ButtonStyle.link, url=LINK_MERCADO_PAGO))

    @discord.ui.button(label="Pix Copia e Cola", style=discord.ButtonStyle.grey, emoji="📋")
    async def copia_cola(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```{PIX_COPIA_COLA}```", ephemeral=True)

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar_pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        channel = interaction.channel
        guild = interaction.guild
        
        # --- ATUALIZAÇÃO: MOVE PARA A CATEGORIA DE PAGOS ---
        novo_nome = f"✅-pago-{user.name.lower()}"
        categoria_pagos = guild.get_channel(ID_CATEGORIA_PAGOS)
        
        if categoria_pagos:
            await channel.edit(name=novo_nome, category=categoria_pagos)
        else:
            await channel.edit(name=novo_nome) # Se não achar a categoria, só muda o nome
        # ---------------------------------------------------
        
        embed_sucesso = discord.Embed(
            title="✅ Pagamento Registrado!",
            description="Seu ticket foi movido para o atendimento, por favor envie seu comprovante e aguarde!",
            color=0x8708f7
        )
        embed_sucesso.set_footer(text="Não feche esse ticket!")
        
        button.disabled = True
        button.label = "Aguardando Aprovação"
        
        await interaction.response.edit_message(view=self) 
        # MARCA A STAFF
        await channel.send(f"{user.mention} 🔔 <@&1465012346794676253> **Novo pagamento!**", embed=embed_sucesso)

    @discord.ui.button(label="Cancelar compra", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class PagamentoView(discord.ui.View):
    def __init__(self, valor_total):
        super().__init__(timeout=None)
        self.valor_total = valor_total # Guarda o valor pra passar pro pix

    @discord.ui.button(label="Pagar com Pix", style=discord.ButtonStyle.grey, emoji="💠")
    async def pagar_pix(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_pix = discord.Embed(
            title="🛒 Pagamento via PIX",
            description="Escaneie o QR Code ou use o Copia e Cola.",
            color=0x8708f7
        )
        # Mostra o valor certo que veio do carrinho
        embed_pix.add_field(name="Valor Final", value=f"**R$ {self.valor_total:.2f}**", inline=False)
        embed_pix.set_image(url=IMAGEM_QR_CODE)
        
        await interaction.response.edit_message(embed=embed_pix, view=PixView())

    @discord.ui.button(label="Pagar com Saldo", style=discord.ButtonStyle.grey, emoji="💳")
    async def pagar_saldo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Sem saldo. Vai de Pix!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.danger, emoji="🔙")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class CarrinhoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Finalizar Compra", style=discord.ButtonStyle.green, emoji="➡️")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Pega o valor total atualizado do Embed (lê o que tá escrito lá)
        embed = interaction.message.embeds[0]
        # Pega o texto do campo "Total" (ex: "R$ 70.00")
        texto_valor = embed.fields[1].value.replace("**", "").replace("R$ ", "")
        try:
            valor_final = float(texto_valor)
        except:
            valor_final = PRECO_UNITARIO # Se der erro, usa o padrão

        guild = interaction.guild
        user = interaction.user
        nome_ticket = f"compra-{user.name.lower()}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
            # --- ATUALIZAÇÃO: CRIA DENTRO DA CATEGORIA DE ABERTOS ---
            categoria_abertos = guild.get_channel(ID_CATEGORIA_ABERTOS)
            
            # category=categoria_abertos é o que faz ele nascer no lugar certo
            ticket_channel = await guild.create_text_channel(nome_ticket, overwrites=overwrites, category=categoria_abertos)
            # --------------------------------------------------------
            
            bot.loop.create_task(monitorar_ticket(ticket_channel))

            embed_pag = discord.Embed(
                title="💳 Escolha seu método",
                description="Selecione como deseja pagar.",
                color=0x8708f7
            )
            embed_pag.add_field(name="Total a Pagar", value=f"**R$ {valor_final:.2f}**", inline=False)
            
            # Passa o valor atualizado pra próxima tela
            await ticket_channel.send(content=user.mention, embed=embed_pag, view=PagamentoView(valor_final))
            await interaction.response.send_message(f"✅ Ticket criado: {ticket_channel.mention}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro (Verifique os IDs das categorias): {e}", ephemeral=True)

    # BOTÃO ATUALIZADO COM O MODAL
    @discord.ui.button(label="Alterar quantidade", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def alterar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Abre o pop-up pro cara digitar
        await interaction.response.send_modal(QuantidadeModal())

class BotaoCompra(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Adicionar ao carrinho", style=discord.ButtonStyle.grey, emoji="🛒")
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_carrinho = discord.Embed(
            title="🛒 Carrinho",
            color=0x8708f7
        )
        embed_carrinho.add_field(name="Produto", value=f"1x {NOME_PRODUTO}", inline=False)
        embed_carrinho.add_field(name="Total a Pagar", value=f"**R$ {PRECO_UNITARIO:.2f}**", inline=False)
        
        await interaction.response.send_message(embed=embed_carrinho, view=CarrinhoView(), ephemeral=True)

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f'🔥 {bot.user} tá ON!')

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
    # COLOQUE AQUI A IMAGEM DO ANUNCIO (BAKUGO)
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


#token
import os

bot.run(os.getenv("TOKEN"))