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

CATEGORIES = ['CryptoNFTs', 'devise', 'Indice', 'etf', 'Actions', 'MatierePremiere', 'tous le reste']

KEYWORDS = {
    'CryptoNFTs': ['crypto', 'bitcoin', 'ethereum', 'nft', 'blockchain', 'defi', 'hack', 'regulation', 'launch'],
    'devise': ['forex', 'currency', 'exchange rate', 'usd', 'eur', 'yen', 'gbp'],
    'Indice': ['index', 's&p', 'nasdaq', 'dow jones', 'ftse', 'nikkei'],
    'etf': ['etf', 'exchange traded fund'],
    'Actions': ['stock', 'share', 'equity', 'ipo', 'earnings', 'dividend'],
    'MatierePremiere': ['commodity', 'oil', 'gold', 'silver', 'crude', 'wheat', 'copper']
}

CHANNELS_FILE = 'channels.json'
LAST_NEWS_FILE = 'last_news.json'

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_channels(channels):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(channels, f)

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
    global CHANNELS
    CHANNELS = load_channels()
    fetch_news.start()
    print(f'{bot.user} has connected to Discord!')

@tasks.loop(minutes=10)
async def fetch_news():
    url = f'https://newsapi.org/v2/everything?q=economy OR finance OR business OR stock OR crypto OR commodity OR etf OR regulation OR hack&domains=coindesk.com,cointelegraph.com,wsj.com,cnbc.com,bloomberg.com,reuters.com&sortBy=publishedAt&apiKey={NEWSAPI_KEY}&pageSize=20&language=en'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f'Error fetching news: {resp.status}')
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
            continue  # Skip invalid dates
        
        text = ((article.get('title', '') + ' ' + article.get('description', '') + ' ' + article.get('content', ''))).lower()
        
        matching_cats = [cat for cat, kws in KEYWORDS.items() if any(kw.lower() in text for kw in kws)]
        if not matching_cats:
            matching_cats = ['tous le reste']
        
        for cat in matching_cats:
            last_time_str = last_times.get(cat, '2000-01-01T00:00:00Z')
            try:
                last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
            except ValueError:
                last_time = datetime(2000, 1, 1, tzinfo=datetime.now().tzinfo)
            
            if pub_time > last_time:
                if cat in CHANNELS:
                    channel = bot.get_channel(CHANNELS[cat])
                    if channel:
                        embed = discord.Embed(title=article.get('title', 'No Title'), description=article.get('description', 'No Description'), url=article.get('url'))
                        embed.set_author(name=article['source'].get('name', 'Unknown Source'))
                        embed.set_footer(text=pub_time_str)
                        await channel.send(embed=embed)
                new_last[cat] = max(new_last.get(cat, '2000-01-01T00:00:00Z'), pub_time_str)
    
    save_last(new_last)

@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, category: str, channel: discord.TextChannel):
    if category not in CATEGORIES:
        await ctx.send(f'Catégorie "{category}" non trouvée. Disponibles : {", ".join(CATEGORIES)}')
        return
    CHANNELS[category] = channel.id
    save_channels(CHANNELS)
    await ctx.send(f'Catégorie "{category}" définie sur {channel.mention}')

bot.run(TOKEN)
