import discord
import requests
import re
import os
import json
import asyncio
from lxml import html
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- Carregar variáveis de ambiente ---
load_dotenv()

# --- CONFIGURAÇÕES ---
# Lê do arquivo .env
TOKEN = os.getenv("TOKEN")
ID_CANAL_ENTRADA = int(os.getenv("ID_CANAL_ENTRADA")) 
ID_CANAL_SAIDA = int(os.getenv("ID_CANAL_SAIDA"))

# --- Configuração do Bot ---
intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# --- Banco de Dados ---
pasta_data = os.path.join("src", "data")
arquivo_banco_dados = os.path.join(pasta_data, "historico_bans.json")
os.makedirs(pasta_data, exist_ok=True)

def carregar_historico():
    urls_ja_banidas = set()
    if os.path.exists(arquivo_banco_dados):
        try:
            with open(arquivo_banco_dados, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for item in dados:
                    urls_ja_banidas.add(item['url'])
        except:
            pass
    return urls_ja_banidas

def salvar_no_historico(novo_registro):
    dados_existentes = []
    if os.path.exists(arquivo_banco_dados):
        try:
            with open(arquivo_banco_dados, 'r', encoding='utf-8') as f:
                dados_existentes = json.load(f)
        except:
            pass
    dados_existentes.append(novo_registro)
    with open(arquivo_banco_dados, 'w', encoding='utf-8') as f:
        json.dump(dados_existentes, f, indent=4, ensure_ascii=False)

# --- Verificação da Steam ---
def verificar_link_steam(url):
    historico = carregar_historico()
    if url in historico:
        return None 

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        resposta = requests.get(url, headers=headers, timeout=5)
        if resposta.status_code == 200:
            arvore = html.fromstring(resposta.content)
            
            xpath_ban = '//div[contains(@class, "profile_ban")]'
            xpath_nome = '//span[contains(@class, "actual_persona_name")]'
            xpath_foto = '//div[contains(@class, "playerAvatarAutoSizeInner")]/img/@src'

            elementos_ban = arvore.xpath(xpath_ban)

            if len(elementos_ban) > 0:
                elementos_nome = arvore.xpath(xpath_nome)
                nome_perfil = elementos_nome[0].text_content().strip() if elementos_nome else "Nome Desconhecido"
                
                foto_perfil = arvore.xpath(xpath_foto)
                url_foto = foto_perfil[0] if foto_perfil else None

                texto_completo = elementos_ban[0].text_content()
                
                tipo_ban = "Desconhecido"
                if "VAC ban" in texto_completo:
                    tipo_ban = "VAC (Valve Anti-Cheat)"
                elif "game ban" in texto_completo:
                    tipo_ban = "Game Ban (Desenvolvedor)"
                
                data_formatada = "Data desconhecida"
                match = re.search(r'(\d+)\s+day\(s\)\s+since\s+last\s+ban', texto_completo)
                
                if match:
                    dias = int(match.group(1))
                    data_calc = datetime.now() - timedelta(days=dias)
                    data_formatada = data_calc.strftime("%d/%m/%Y")
                elif "0 day(s)" in texto_completo:
                    data_formatada = datetime.now().strftime("%d/%m/%Y")

                registro = {
                    "nome": nome_perfil,
                    "url": url,
                    "tipo_ban": tipo_ban,
                    "data_ban": data_formatada,
                    "data_verificacao": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                salvar_no_historico(registro)
                return registro, url_foto

    except Exception as e:
        print(f"Erro ao verificar {url}: {e}")
    
    return None

# --- Scan de Perfil ---
async def escanear_historico():
    print("🔎 Executando a varredura do histórico...")
    
    canal_entrada = client.get_channel(ID_CANAL_ENTRADA)
    canal_saida = client.get_channel(ID_CANAL_SAIDA)

    if not canal_entrada or not canal_saida:
        print("❌ Erro: Não foi possivel encontrar os canais. Verifique os IDs no .env")
        return

    contador = 0
    # Lê as últimas 100 mensagens
    async for message in canal_entrada.history(limit=100):
        if message.author == client.user: continue
        
        mensagem = message.content.strip()
        
        if "steamcommunity.com/profiles/" in mensagem or "steamcommunity.com/id/" in mensagem:
            palavras = mensagem.split()
            link_para_testar = next((p for p in palavras if "steamcommunity.com" in p), None)

            if link_para_testar:
                resultado = verificar_link_steam(link_para_testar)

                if resultado:
                    dados, foto = resultado
                    
                    # --- EMBED LIMPO (SCANNER) ---
                    embed = discord.Embed(
                        title="🚨 BANIMENTO DETECTADO 🚨",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="👤 Jogador", value=dados['nome'], inline=True)
                    embed.add_field(name="⚖️ Tipo", value=dados['tipo_ban'], inline=True)
                    embed.add_field(name="📅 Data do Ban", value=dados['data_ban'], inline=False)
                    embed.add_field(name="🔗 Link do Perfil", value=dados['url'], inline=False)
                    
                    if foto: embed.set_thumbnail(url=foto)
                    
                    embed.set_footer(text="Detectado via Varredura Automática")

                    await canal_saida.send(embed=embed)
                    print(f"✅ REPORTADO: {dados['nome']}")
                
                await asyncio.sleep(1)
        
        contador += 1
    
    print(f"🏁 Varredura concluída. {contador} mensagens analisadas.")

# --- TAREFA (LOOP DE 10 MIN) ---
async def tarefa_repetitiva():
    await client.wait_until_ready()
    
    while not client.is_closed():
        await escanear_historico()
        print("⏳ Aguardando 10 minutos (600s) para a próxima varredura...")
        await asyncio.sleep(600) 

# --- EVENTOS ---
@client.event
async def on_ready():
    print(f'🤖 Bot conectado como {client.user}')
    client.loop.create_task(tarefa_repetitiva())

@client.event
async def on_message(message):
    if message.author == client.user: return
    if message.channel.id != ID_CANAL_ENTRADA: return

    if "steamcommunity.com" in message.content:
        link = next((p for p in message.content.split() if "steamcommunity.com" in p), None)
        if link:
            resultado = verificar_link_steam(link)
            if resultado:
                dados, foto = resultado
                canal_alerta = client.get_channel(ID_CANAL_SAIDA)
                if canal_alerta:
                    
                    # --- EMBED LIMPO (TEMPO REAL) ---
                    embed = discord.Embed(
                        title="🚨 BANIMENTO DETECTADO 🚨",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="👤 Jogador", value=dados['nome'], inline=True)
                    embed.add_field(name="⚖️ Tipo", value=dados['tipo_ban'], inline=True)
                    embed.add_field(name="📅 Data do Ban", value=dados['data_ban'], inline=False)
                    embed.add_field(name="🔗 Link do Perfil", value=dados['url'], inline=False)
                    
                    if foto: embed.set_thumbnail(url=foto)
                    
                    embed.set_footer(text="Detectado em Tempo Real")
                    
                    await canal_alerta.send(embed=embed)

# Verifica se o TOKEN foi carregado corretamente antes de rodar
if TOKEN:
    client.run(TOKEN)
else:
    print("❌ Erro: O TOKEN não foi encontrado no arquivo .env")