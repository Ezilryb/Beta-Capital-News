import discord
from discord.ext import commands, tasks
import os
import requests
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

# IDs des channels (remplacez par les vôtres)
CHANNELS = {
    'crypto_nfts': 123456789012345678,  # Exemple d'ID
    'devises': 123456789012345678,
    'indices': 123456789012345678,
    'etf': 123456789012345678,
    'actions': 123456789012345678,
    'matieres_premieres': 123456789012345678,
    'autres': 123456789012345678
}

# Mots-clés pour catégorisation
KEYWORDS = {
    'crypto_nfts': ['crypto', 'bitcoin', 'ethereum', 'nft', 'blockchain'],
    'devises': ['forex', 'dollar', 'euro', 'yen', 'currency', 'exchange rate'],
    'indices': ['dow jones', 's&p 500', 'nasdaq', 'index', 'cac 40'],
    'etf': ['etf', 'exchange traded fund'],
    'actions': ['stock', 'share', 'equity', 'apple', 'tesla', 'market cap'],
    'matieres_premieres': ['commodity', 'oil', 'gold', 'silver', 'wheat', 'energy']
}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Si besoin pour rôles

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user}')
    fetch_news.start()  # Démarre la tâche périodique

@tasks.loop(minutes=10)  # Polling toutes les 10 minutes
async def fetch_news():
    url = f'https://newsapi.org/v2/everything?q=economy+OR+finance+OR+crypto&apiKey={NEWSAPI_KEY}&language=fr'  # Focus sur news économiques, en français si possible
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json()['articles'][:5]  # Limite à 5 pour éviter spam
        for article in articles:
            title = article['title'].lower()
            description = article['description'].lower() if article['description'] else ''
            content = title + ' ' + description
            category = 'autres'  # Par défaut
            for cat, keys in KEYWORDS.items():
                if any(key in content for key in keys):
                    category = cat
                    break
            channel_id = CHANNELS.get(category)
            if channel_id:
                channel = bot.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(title=article['title'], description=article['description'], url=article['url'])
                    embed.set_thumbnail(url=article['urlToImage'] if article['urlToImage'] else '')
                    await channel.send(embed=embed)
    else:
        print('Erreur API NewsAPI')

# Commande exemple pour abonnement (optionnel : assigne rôle)
@bot.command(name='subscribe')
async def subscribe(ctx, category: str):
    if category in CHANNELS:
        role_name = f'Sub_{category}'
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            role = await ctx.guild.create_role(name=role_name)
        await ctx.author.add_roles(role)
        await ctx.send(f'Vous êtes abonné à {category}!')
    else:
        await ctx.send('Catégorie invalide.')

bot.run(TOKEN)
