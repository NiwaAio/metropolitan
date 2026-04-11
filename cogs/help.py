import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class HelpView(discord.ui.View):
    def __init__(self, embeds, author_id, timeout=60):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current = 0
        self.author_id = author_id
        self.message = None

    async def update(self, interaction: discord.Interaction):
        embed = self.embeds[self.current]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для вас.", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
            await self.update(interaction)

    @discord.ui.button(label="Вперёд ▶️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для вас.", ephemeral=True)
            return
        if self.current < len(self.embeds) - 1:
            self.current += 1
            await self.update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Показать список всех команд бота")
    async def slash_help(self, interaction: discord.Interaction):
        commands_by_category = {}

        for cmd in self.bot.tree.get_commands():
            category = "⚙️ Общие"
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    name = f"/{cmd.name} {sub.name}"
                    desc = sub.description or "Нет описания"
                    if cmd.name == "rr":
                        category = "🎭 Реакционные роли"
                    elif cmd.name == "raid":
                        category = "📢 Уведомления о сборе"
                    elif cmd.name == "attendance":
                        category = "📊 Посещаемость"
                    else:
                        category = "🔧 Администрирование"
                    commands_by_category.setdefault(category, []).append((name, desc))
            else:
                name = f"/{cmd.name}"
                desc = cmd.description or "Нет описания"
                if cmd.name in ["mute", "kick", "ban", "tempban", "warn", "clearwarns", "filter"]:
                    category = "🛡️ Модерация"
                elif cmd.name in ["raid_channel", "raid_role", "raid_days", "raid_times", "raid_reset_times", "raid_enable", "raid_postpone", "raid_cancel_postpone", "raid_settings"]:
                    category = "📢 Уведомления о сборе"
                elif cmd.name in ["attendance_voice", "attendance_role", "attendance_report", "attendance_times", "attendance_enable", "attendance_settings", "attendance_test"]:
                    category = "📊 Посещаемость"
                elif cmd.name in ["rr_add", "rr_remove", "rr_list"]:
                    category = "🎭 Реакционные роли"
                elif cmd.name in ["temprole", "removetemp"]:
                    category = "⏳ Временные роли"
                elif cmd.name in ["setautorole", "setwelcomechannel", "setlogchannel"]:
                    category = "⚙️ Настройки сервера"
                elif cmd.name in ["userinfo", "serverinfo"]:
                    category = "ℹ️ Информация"
                elif cmd.name in ["remind", "poll", "roll", "coinflip", "roulette", "meme"]:
                    category = "🎲 Развлечения"
                elif cmd.name in ["wiki", "wiki_add", "wiki_remove"]:
                    category = "📚 Вики"
                elif cmd.name == "sync":
                    category = "🔧 Администрирование"
                else:
                    category = "⚙️ Общие"
                commands_by_category.setdefault(category, []).append((name, desc))

        categories = sorted(commands_by_category.keys())
        for cat in categories:
            commands_by_category[cat].sort(key=lambda x: x[0])

        pages = []
        current_page = []
        current_length = 0

        for category in categories:
            header = f"\n**{category}**\n"
            header_len = len(header)
            commands_block = ""
            for cmd_name, cmd_desc in commands_by_category[category]:
                line = f"• `{cmd_name}` — {cmd_desc}\n"
                if current_length + header_len + len(commands_block) + len(line) > 1800:
                    if commands_block:
                        current_page.append(header + commands_block)
                    else:
                        current_page.append(header + commands_block)
                    pages.append("\n".join(current_page))
                    current_page = []
                    current_length = 0
                    commands_block = line
                else:
                    commands_block += line
            if commands_block:
                current_page.append(header + commands_block)
                current_length += header_len + len(commands_block)
            else:
                if current_page:
                    pages.append("\n".join(current_page))
                    current_page = []
                    current_length = 0

        if current_page:
            pages.append("\n".join(current_page))

        if not pages:
            pages = ["Нет доступных команд."]

        embeds = []
        for i, content in enumerate(pages, 1):
            embed = discord.Embed(
                title="📖 Справка по командам",
                description=content,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Страница {i} из {len(pages)}")
            embeds.append(embed)

        view = HelpView(embeds, interaction.user.id, timeout=60)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(Help(bot))