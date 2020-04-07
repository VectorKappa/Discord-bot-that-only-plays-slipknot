from __future__ import unicode_literals
import asyncio
import discord
import youtube_dl
import credentials
from discord.ext import tasks, commands
import datetime
import time

youtube_dl.utils.bug_reports_message = lambda: ''

token = credentials.getToken()

ytdl_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)



class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['j'])
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command(aliases=['p', 'add'])
    async def play(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(
                'Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command(aliases=['live'])
    async def stream(self, ctx, *, url):

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(
                'Player error: %s' % e) if e else None)

        await ctx.send('Now streaming: {}'.format(player.title))

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to any channel")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command(aliases=['s'])
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                # blad_dolaczania
                await ctx.send("You're not connected to any channel.")
                raise commands.CommandError("Message author is not connected to any channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


class logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author == bot.user:
            return
        else:
            print(
                f"[{datetime.datetime.now()}]  {ctx.author} sent {ctx.content} on {ctx.channel}")


class maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def time(self, ctx):
        await ctx.send(f"Current RTC is: {time.time()}s")
    
    @commands.command()
    async def remindme(self, ctx, time, *, message):
        await ctx.send(f"K, I'll remind you about\"{message}\" in {time}s")
        await asyncio.sleep(int(time))
        await ctx.author.send(f"I'm reminding you about {message}")


    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"Pong! {int(bot.latency*1000)}ms")


bot = commands.Bot(command_prefix=commands.when_mentioned_or("&"),
                   description=None, help_command=None)

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('-------------------------------------------------------------------')


# bot.add_cog(slipknot_listener(bot))
bot.add_cog(music(bot))
bot.add_cog(maintenance(bot))
bot.add_cog(logger(bot))

bot.run(token)
