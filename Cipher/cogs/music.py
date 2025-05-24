import discord
import asyncio
import yt_dlp
from discord import app_commands
from discord.ext import commands
from collections import deque

class Song:
    def __init__(self, title, url, requested_by, source=None):
        self.title = title
        self.url = url
        self.requested_by = requested_by
        self.source = source

class SearchView(discord.ui.View):
    def __init__(self, search_results, requester, cog):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.search_results = search_results
        self.requester = requester
        self.cog = cog  # Reference to the cog for accessing its methods

    @discord.ui.button(label="1️⃣", style=discord.ButtonStyle.grey, row=0)
    async def select_first(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, 0)

    @discord.ui.button(label="2️⃣", style=discord.ButtonStyle.grey, row=0)
    async def select_second(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, 1)

    @discord.ui.button(label="3️⃣", style=discord.ButtonStyle.grey, row=0)
    async def select_third(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, 2)

    @discord.ui.button(label="4️⃣", style=discord.ButtonStyle.grey, row=1)
    async def select_fourth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, 3)

    @discord.ui.button(label="5️⃣", style=discord.ButtonStyle.grey, row=1)
    async def select_fifth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, 4)

    async def process_selection(self, interaction: discord.Interaction, index: int):
        # Check if the interaction user is the original requester
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("You didn't initiate this search!", ephemeral=True)
            return

        # Ensure the index is valid
        if 0 <= index < len(self.search_results):
            selected_song = self.search_results[index]
            
            # Process the song using the cog's methods
            await interaction.response.defer(thinking=True)
            
            # Use the cog's play_song logic
            await self.cog.process_song_request(interaction, selected_song['url'])

            # Disable all buttons after selection
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.send_message("Invalid selection!", ephemeral=True)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue = deque()
        self.guild_voice_clients = {}
        self.music_channels = {}
        self.currently_playing = {}
        
        # YouTube download options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'source_address': '0.0.0.0'
        }

    async def cog_load(self):
       pass

    # Helper methods
    async def get_audio_source(self, url, interaction=None):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'url': info.get('url')
                }
        except Exception as e:
            error_msg = f"Error extracting audio source: {str(e)}"
            if interaction:
                await interaction.followup.send(f"❌ {error_msg}")
            print(error_msg)
            raise

    async def play_next(self, guild_id):
        if not self.music_queue:
            if guild_id in self.currently_playing:
                self.currently_playing[guild_id] = None
            return
            
        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            self.music_queue.clear()
            return
            
        next_song = self.music_queue.popleft()

        self.currently_playing[guild_id] = next_song

        try:
            audio = discord.FFmpegPCMAudio(
                next_song.source['url'],
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn -bufsize 1024k"
            )
            audio = discord.PCMVolumeTransformer(audio, volume=0.5)

            voice_client = self.guild_voice_clients[guild_id]
            voice_client.play(
                audio,
                after=lambda e: self.handle_playback_error(e, guild_id)
            )

            if guild_id in self.music_channels:
                channel = self.bot.get_channel(self.music_channels[guild_id])
                if channel:
                    await channel.send(f"🎵 Now playing: **{next_song.title}** (requested by {next_song.requested_by.mention})")

        except Exception as e:
            print(f"Error playing song: {str(e)}")
            asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)

    def handle_playback_error(self, error, guild_id):
        if error:
            print(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)

    async def process_song_request(self, interaction, url):
        """Process a song request for both direct URLs and search results"""
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return False

        guild_id = interaction.guild.id

        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("You need to be in a voice channel to use this command!")
                return False
                
            voice_channel = interaction.user.voice.channel
        except Exception as e:
            print(f"Error checking voice state: {e}")
            await interaction.followup.send("You need to be in a voice channel to use this command!")
            return False
        
        try:
            source = await self.get_audio_source(url, interaction)
        except Exception as e:
            await interaction.followup.send(f"Error retrieving the song: {str(e)}")
            return False

        song = Song(source['title'], url, interaction.user, source)

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            try:
                voice_client = await voice_channel.connect()
                self.guild_voice_clients[guild_id] = voice_client
            except discord.errors.ClientException as e:
                await interaction.followup.send(f"Error connecting to voice channel: {str(e)}")
                return False

        self.music_queue.append(song)

        if guild_id not in self.currently_playing or self.currently_playing[guild_id] is None:
            await self.play_next(guild_id)
            await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
        else:
            await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")
            
        return True
    
    music = app_commands.Group(name="music", description="All music related commands.")
    
    # Commands
    @music.command(name="play", description="Play a song from YouTube URL")
    @app_commands.describe(url="YouTube URL of the song to play")
    async def playsong(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        await self.process_song_request(interaction, url)

    @music.command(name="search", description="Search for a song on YouTube")
    @app_commands.describe(query="Search term for the song")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)

        # Use yt_dlp to perform a YouTube search
        search_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch5:',  # search for top 5 results
        }

        try:
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                result = ydl.extract_info(query, download=False)
                
                # Ensure we got search results
                if 'entries' not in result or not result['entries']:
                    await interaction.followup.send("No results found for your search.")
                    return

                # Prepare search results
                search_results = []
                for entry in result['entries'][:5]:
                    search_results.append({
                        'title': entry.get('title', 'Unknown Title'),
                        'url': entry.get('webpage_url', ''),
                        'uploader': entry.get('uploader', 'Unknown Uploader')
                    })

                # Create search results message
                search_text = "🔍 **Search Results:**\n\n"
                for i, result in enumerate(search_results, 1):
                    search_text += f"{i}️⃣ **{result['title']}**\n*By {result['uploader']}*\n\n"

                # Create view with selection buttons
                view = SearchView(search_results, interaction.user, self)

                await interaction.followup.send(search_text, view=view)

        except Exception as e:
            print(f"Search error: {str(e)}")
            await interaction.followup.send(f"An error occurred while searching: {str(e)}")

    @music.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("I'm not playing anything right now!")
            return

        if guild_id not in self.currently_playing or self.currently_playing[guild_id] is None:
            await interaction.response.send_message("Nothing is playing right now!")
            return

        self.guild_voice_clients[guild_id].stop()

        await interaction.response.send_message("⏭️ Skipped to the next song!")

    @music.command(name="stop", description="Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("I'm not playing anything right now!")
            return

        self.music_queue.clear()
        self.guild_voice_clients[guild_id].stop()

        self.currently_playing[guild_id] = None

        await interaction.response.send_message("⏹️ Playback stopped and queue cleared!")

    @music.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("❌ I'm not playing anything right now!")
            return

        try:
            voice_client = self.guild_voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.pause()
                await interaction.response.send_message("⏸️ Playback paused!")
            else:
                await interaction.response.send_message("❌ Nothing is playing right now!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to pause: {str(e)}")

    @music.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("❌ I'm not connected to a voice channel!")
            return

        try:
            voice_client = self.guild_voice_clients[guild_id]
            if voice_client.is_paused():
                voice_client.resume()
                await interaction.response.send_message("▶️ Playback resumed!")
            else:
                await interaction.response.send_message("❌ Playback is not paused!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to resume: {str(e)}")

    @music.command(name="volume", description="Set the playback volume (0-100)")
    @app_commands.describe(level="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("❌ I'm not playing anything right now!")
            return

        if level < 0 or level > 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100!")
            return

        try:
            voice_client = self.guild_voice_clients[guild_id]
            if hasattr(voice_client.source, 'volume'):
                voice_client.source.volume = level / 100.0
                await interaction.response.send_message(f"🔊 Volume set to {level}%")
            else:
                await interaction.response.send_message("❌ Cannot adjust volume for current source!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to set volume: {str(e)}")

    @app_commands.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if not self.music_queue and (guild_id not in self.currently_playing or self.currently_playing[guild_id] is None):
            await interaction.response.send_message("The queue is empty!")
            return

        queue_text = "🎵 **Current Queue:**\n"

        if guild_id in self.currently_playing and self.currently_playing[guild_id]:
            current_song = self.currently_playing[guild_id]
            queue_text += f"▶️ **Now Playing**: {current_song.title} (requested by {current_song.requested_by.display_name})\n\n"

        if self.music_queue:
            queue_text += "📋 **Up Next**:\n"
            for i, song in enumerate(self.music_queue, 1):
                queue_text += f"{i}. {song.title} (requested by {song.requested_by.display_name})\n"
        else:
            queue_text += "📋 **Up Next**: Nothing in queue!"

        await interaction.response.send_message(queue_text)

    @app_commands.command(name="disconnect", description="Disconnect the bot from voice channel")
    async def disconnect(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return
            
        guild_id = interaction.guild.id

        if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
            await interaction.response.send_message("I'm not in a voice channel!")
            return

        self.music_queue.clear()
        self.currently_playing[guild_id] = None

        await self.guild_voice_clients[guild_id].disconnect()
        del self.guild_voice_clients[guild_id]

        await interaction.response.send_message("👋 Disconnected from voice channel!")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
