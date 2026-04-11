import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import config
import database
from config import INTENTS

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=INTENTS)
        self.remove_command('help')

    async def setup_hook(self):
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.reaction_roles")
        await self.load_extension("cogs.temp_roles")
        await self.load_extension("cogs.help")
        await self.load_extension("cogs.antinuke")
        await self.load_extension("cogs.logging")
        await self.load_extension("cogs.verification")
        await self.load_extension("cogs.wiki")
        await self.load_extension("cogs.gambling")
        await self.load_extension("cogs.images")
        await self.load_extension("cogs.autoroles_greetings")
        await self.load_extension("cogs.info")
        await self.load_extension("cogs.reminders")
        await self.load_extension("cogs.poll")
        await self.load_extension("cogs.raid_notify")
        await self.load_extension("cogs.attendance")
        await self.load_extension("cogs.ticket_absence")
        await self.load_extension("cogs.ocr_attendance")
        await self.load_extension("cogs.ticket_registration")
        await self.load_extension("cogs.report_generator")

        await database.init_db()

        self.loop.create_task(self.check_temp_roles())

    async def check_temp_roles(self):
        await self.wait_until_ready()
        while not self.is_closed():
            now = asyncio.get_event_loop().time()
            expired = await database.get_expired_temp_roles(now)
            for user_id, guild_id, role_id in expired:
                guild = self.get_guild(guild_id)
                if guild:
                    member = guild.get_member(user_id)
                    if member:
                        role = guild.get_role(role_id)
                        if role and role in member.roles:
                            try:
                                await member.remove_roles(role, reason="Временная роль истекла")
                            except:
                                pass
                    await database.remove_temp_role(user_id, guild_id, role_id)
            await asyncio.sleep(30)

bot = MyBot()

@bot.tree.command(name="sync", description="Принудительная синхронизация команд (только владелец)")
@app_commands.default_permissions(administrator=True)
async def slash_sync(interaction: discord.Interaction):
    if hasattr(config, 'OWNER_IDS') and interaction.user.id not in config.OWNER_IDS:
        await interaction.response.send_message("У вас нет прав на использование этой команды.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Синхронизировано {len(synced)} команд.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка синхронизации: {e}", ephemeral=True)

@bot.command(name="sync")
@commands.is_owner()
async def text_sync(ctx: commands.Context):
    async with ctx.typing():
        try:
            bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f'✅ Синхронизировано {len(synced)} команд для сервера **{ctx.guild.name}**.')
        except Exception as e:
            await ctx.send(f'❌ Ошибка: {e}')
    await asyncio.sleep(5)
    await ctx.message.delete()

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    await bot.change_presence(activity=discord.Game(name="Используй /help"))

if __name__ == "__main__":
    bot.run(config.TOKEN)