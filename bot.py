import discord
from discord.ext import commands, tasks
import aiohttp
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

# Mapping fixe des catégories vers les IDs de channels (à ne pas changer sauf si tu veux modifier)
CHANNEL_IDS = {
    'CryptoNFTs': 1452339946558980409,
    'devise': 1452340005895802910,
    'Indice': 1452340116117782622,
    'etf': 1452340158140649757,
    'Actions': 1452340198535991516,
    'MatierePremiere': 1452340245680095414,
    'tous le reste': 1452365741579042956  # Par défaut, on peut utiliser le même que MatierePremiere ou un autre
}

CATEGORIES = list(CHANNEL_IDS.keys())

KEYWORDS = {
    'CryptoNFTs': ['crypto', 'bitcoin', 'ethereum', 'nft', 'blockchain', 'defi', 'hack', 'regulation', 'launch',
                   'cryptomonnaie', 'bitcoins', 'ethéréum', 'nft', 'blockchain', 'defi', 'régulation', 'lancement'],
    'devise': ['forex', 'currency', 'exchange rate', 'usd', 'eur', 'yen', 'gbp',
               'forex', 'devise', 'taux de change', 'dollar', 'euro', 'yen', 'livre sterling'],
    'Indice': ['index', 's&p', 'nasdaq', 'dow jones', 'ftse', 'nikkei',
               'indice', 'cac 40', 's&p', 'nasdaq', 'dow jones', 'ftse', 'nikkei'],
    'etf': ['etf', 'exchange traded fund',
            'etf', 'fonds négocié en bourse', 'fonds indiciel coté'],
    'Actions': ['stock', 'share', 'ipo', 'earnings', 'dividend',
                'action', 'bourse', 'introduction en bourse', 'résultats', 'bénéfices', 'dividende'],
    'MatierePremiere': ['commodity', 'oil', 'gold', 'silver', 'crude', 'wheat', 'copper',
                        'matière première', 'pétrole', 'or', 'argent', 'brut', 'blé', 'cuivre']
}

LAST_NEWS_FILE = 'last_news.json'

intents = discord.Intents.default()
intents.message_content = True  # Pour les commandes si tu en ajoutes plus tard

bot = commands.Bot(command_prefix='!', intents=intents)

def load_last():
    if os.path.exists(LAST_NEWS_FILE):
        with open(LAST_NEWS_FILE, 'r') as f:
            return json.load(f)
    return {cat: '2000-01-01T00:00:00Z' for cat in CATEGORIES}

def save_last(last_times):
    with open(LAST_NEWS_FILE, 'w') as f:
        json.dump(last_times, f)

@bot.event
async def on_ready():
    fetch_news.start()
    print(f'{bot.user} has connected to Discord!')

@tasks.loop(minutes=10)
async def fetch_news():
    # Retiré les domaines généraux comme bfmtv.com, lemonde.fr, france24.com pour éviter les articles non pertinents (sports, politique, etc.)
    # Gardé uniquement les domaines axés sur la finance et l'économie
    url = f'https://newsapi.org/v2/everything?q=(economy OR finance OR business OR stock OR crypto OR commodity OR etf OR regulation OR hack OR économie OR finances OR affaires OR bourse OR cryptomonnaie OR matière première OR régulation OR piratage)&domains=coindesk.com,cointelegraph.com,wsj.com,cnbc.com,bloomberg.com,reuters.com,lesechos.fr,boursorama.com,latribune.fr,capital.fr&sortBy=publishedAt&apiKey={NEWSAPI_KEY}&pageSize=20&language=fr'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f'Error fetching news: {resp.status} - {await resp.text()}')
                return
            data = await resp.json()
            articles = data.get('articles', [])
    
    last_times = load_last()
    new_last = last_times.copy()
    
    for article in articles:
        pub_time_str = article['publishedAt']
        try:
            pub_time = datetime.fromisoformat(pub_time_str.replace('Z', '+00:00'))
        except ValueError:
            continue
        
        text = ((article.get('title', '') + ' ' + article.get('description', '') + ' ' + article.get('content', ''))).lower()
        
        matching_cats = [cat for cat, kws in KEYWORDS.items() if any(kw.lower() in text for kw in kws)]
        if not matching_cats:
            continue  # Ne poste pas les articles qui ne correspondent à aucune catégorie spécifique pour éviter le bruit
        
        for cat in matching_cats:
            last_time_str = last_times.get(cat, '2000-01-01T00:00:00Z')
            try:
                last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
            except ValueError:
                last_time = datetime(2000, 1, 1, tzinfo=datetime.now().tzinfo)
            
            if pub_time > last_time:
                channel_id = CHANNEL_IDS.get(cat)
                if channel_id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        embed = discord.Embed(
                            title=article.get('title', 'No Title'),
                            description=article.get('description', 'No Description'),
                            url=article.get('url'),
                            color=discord.Color.blue()
                        )
                        embed.set_author(name=article['source'].get('name', 'Unknown Source'))
                        embed.set_footer(text=pub_time_str)
                        await channel.send(embed=embed)
                    else:
                        print(f"Channel {channel_id} not found for category {cat}")
                new_last[cat] = max(new_last.get(cat, '2000-01-01T00:00:00Z'), pub_time_str)
    
    save_last(new_last)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Command error: {error}")

bot.run(TOKEN)