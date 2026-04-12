import discord
from discord.ext import commands
from discord import app_commands
import json
import base64
import io
import asyncio
from typing import Optional
from database import (
    get_guild_setting, set_guild_setting,
    get_raid_settings, set_raid_channel, set_raid_role, set_raid_days, set_raid_enabled, set_raid_times, set_raid_postpone,
    get_attendance_settings, set_attendance_voice_channel, set_attendance_role, set_attendance_report_channel, set_attendance_times, set_attendance_enabled,
    get_ticket_config, set_ticket_config,
    get_all_reaction_roles, add_reaction_role, remove_reaction_role,
    get_all_wiki_entries, add_wiki_entry, delete_wiki_entry,
    get_all_ign_links, set_ign_link, delete_ign_link,
    get_excused_absences, add_excused_absence, delete_excused_absence,
    get_all_warnings, add_warning, clear_warnings,
    get_all_temp_roles, add_temp_role, remove_temp_role,
    get_all_attendance_records, save_attendance_record,
    get_all_active_tickets, create_active_ticket, delete_active_ticket,
    get_all_reg_tickets, create_reg_ticket, delete_reg_ticket,
    get_all_appeal_tickets, create_appeal_ticket, delete_appeal_ticket,
    get_all_attendance_records_for_export, import_attendance_records,
    init_db
)

class ConfigBackup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="export_config", description="Экспортировать все настройки и историю бота в TXT файл")
    @app_commands.default_permissions(administrator=True)
    async def export_config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        data = {"guild_id": guild.id}

        # guild_settings
        data["prefix"] = await get_guild_setting(guild.id, "prefix") or "!"
        data["filter_enabled"] = await get_guild_setting(guild.id, "filter_enabled") or True
        data["log_channel_id"] = await get_guild_setting(guild.id, "log_channel_id")
        data["auto_role_id"] = await get_guild_setting(guild.id, "auto_role_id")
        data["welcome_channel_id"] = await get_guild_setting(guild.id, "welcome_channel_id")
        data["verify_role_id"] = await get_guild_setting(guild.id, "verify_role_id")

        raid = await get_raid_settings(guild.id)
        data["raid"] = raid if raid else None

        att = await get_attendance_settings(guild.id)
        data["attendance"] = att if att else None

        ticket = await get_ticket_config(guild.id)
        data["ticket"] = ticket if ticket else None

        data["reaction_roles"] = await get_all_reaction_roles(guild.id) or []
        data["wiki"] = await get_all_wiki_entries(guild.id) or []
        data["ign_links"] = [{"user_id": uid, "ign": ign} for uid, ign in (await get_all_ign_links(guild.id)).items()]

        excused = await get_excused_absences(guild.id)
        data["excused"] = [{"user_id": e["user_id"], "start_date": e["start_date"], "end_date": e["end_date"], "reason": e["reason"]} for e in excused]

        warnings = await get_all_warnings(guild.id)
        data["warnings"] = [{"user_id": w["user_id"], "count": w["count"]} for w in warnings]

        temp_roles = await get_all_temp_roles(guild.id)
        data["temp_roles"] = [{"user_id": tr["user_id"], "role_id": tr["role_id"], "until": tr["until"]} for tr in temp_roles]

        attendance_records = await get_all_attendance_records(guild.id)
        data["attendance_records"] = attendance_records

        active_tickets = await get_all_active_tickets(guild.id)
        data["active_tickets"] = [{"user_id": t["user_id"], "channel_id": t["channel_id"], "created_at": t["created_at"]} for t in active_tickets]

        reg_tickets = await get_all_reg_tickets(guild.id)
        data["reg_tickets"] = [{"user_id": t["user_id"], "channel_id": t["channel_id"], "created_at": t["created_at"]} for t in reg_tickets]

        appeal_tickets = await get_all_appeal_tickets(guild.id)
        data["appeal_tickets"] = [{"user_id": t["user_id"], "channel_id": t["channel_id"], "created_at": t["created_at"], "status": t["status"]} for t in appeal_tickets]

        json_str = json.dumps(data, ensure_ascii=False, default=str)
        b64 = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
        file = discord.File(io.BytesIO(b64.encode()), filename=f"config_{guild.id}.txt")
        await interaction.followup.send("📦 Полный экспорт конфигурации и истории.", file=file, ephemeral=True)

    @app_commands.command(name="import_config", description="Импортировать конфигурацию из прикреплённого TXT файла")
    @app_commands.default_permissions(administrator=True)
    async def import_config(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        if not file.filename.endswith('.txt'):
            await interaction.followup.send("❌ Пожалуйста, прикрепите файл с расширением .txt, полученный через /export_config.", ephemeral=True)
            return
        try:
            content = await file.read()
            b64 = content.decode('utf-8').strip()
            json_str = base64.b64decode(b64).decode('utf-8')
            data = json.loads(json_str)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка чтения файла: {e}", ephemeral=True)
            return

        guild = interaction.guild
        if data.get("guild_id") != guild.id:
            await interaction.followup.send("❌ Конфигурация предназначена для другого сервера.", ephemeral=True)
            return

        await set_guild_setting(guild.id, "prefix", data.get("prefix", "!"))
        await set_guild_setting(guild.id, "filter_enabled", data.get("filter_enabled", True))
        await set_guild_setting(guild.id, "log_channel_id", data.get("log_channel_id"))
        await set_guild_setting(guild.id, "auto_role_id", data.get("auto_role_id"))
        await set_guild_setting(guild.id, "welcome_channel_id", data.get("welcome_channel_id"))
        await set_guild_setting(guild.id, "verify_role_id", data.get("verify_role_id"))

        raid = data.get("raid")
        if raid:
            if raid.get("channel_id"): await set_raid_channel(guild.id, raid["channel_id"])
            if raid.get("role_id"): await set_raid_role(guild.id, raid["role_id"])
            if raid.get("days"): await set_raid_days(guild.id, raid["days"])
            if raid.get("times"): await set_raid_times(guild.id, raid["times"])
            await set_raid_enabled(guild.id, raid.get("enabled", False))
            if raid.get("postpone_until"): await set_raid_postpone(guild.id, raid["postpone_until"])

        att = data.get("attendance")
        if att:
            if att.get("voice_channel_id"): await set_attendance_voice_channel(guild.id, att["voice_channel_id"])
            if att.get("role_id"): await set_attendance_role(guild.id, att["role_id"])
            if att.get("report_channel_id"): await set_attendance_report_channel(guild.id, att["report_channel_id"])
            if att.get("times"): await set_attendance_times(guild.id, att["times"])
            await set_attendance_enabled(guild.id, att.get("enabled", False))

        ticket = data.get("ticket")
        if ticket:
            await set_ticket_config(guild.id,
                                    channel_id=ticket.get("channel_id"),
                                    category_id=ticket.get("category_id"),
                                    admin_role_id=ticket.get("admin_role_id"),
                                    message_id=ticket.get("message_id"))

        for rr in data.get("reaction_roles", []):
            await add_reaction_role(rr["message_id"], rr["emoji"], rr["role_id"])
        for wiki in data.get("wiki", []):
            await add_wiki_entry(guild.id, wiki["item_id"], wiki["info"])
        for link in data.get("ign_links", []):
            await set_ign_link(link["user_id"], guild.id, link["ign"])
        for exc in data.get("excused", []):
            await add_excused_absence(guild.id, exc["user_id"], exc["start_date"], exc["end_date"], exc["reason"], 0, 0)

        for w in data.get("warnings", []):
            for _ in range(w["count"]):
                await add_warning(w["user_id"], guild.id)
        for tr in data.get("temp_roles", []):
            await add_temp_role(tr["user_id"], guild.id, tr["role_id"], tr["until"])
        for rec in data.get("attendance_records", []):
            await save_attendance_record(guild.id, rec["date"], rec["check_time"], rec["stage"], rec["present"], rec["absent"])
        for at in data.get("active_tickets", []):
            await create_active_ticket(guild.id, at["user_id"], at["channel_id"])
        for rt in data.get("reg_tickets", []):
            await create_reg_ticket(guild.id, rt["user_id"], rt["channel_id"])
        for ap in data.get("appeal_tickets", []):
            await create_appeal_ticket(guild.id, ap["user_id"], ap["channel_id"])

        await self.recreate_ticket_messages(guild)
        await interaction.followup.send("✅ Конфигурация и история полностью восстановлены. Сообщения с кнопками пересозданы.", ephemeral=True)

    async def recreate_ticket_messages(self, guild: discord.Guild):
        ticket = await get_ticket_config(guild.id)
        if not ticket or not ticket.get("channel_id"):
            return
        channel = guild.get_channel(ticket["channel_id"])
        if not channel:
            return
        if ticket.get("message_id"):
            try:
                old_msg = await channel.fetch_message(ticket["message_id"])
                await old_msg.delete()
            except:
                pass
        from cogs.ticket_registration import RegistrationTicketView
        embed = discord.Embed(
            title="📜 Откровение",
            description=("**И прогневался Господь, увидев, как человечество погрязло во грехе...**\n\n"
                         "Если ты желаешь вступить в братство и разделить страдание, нажми на кнопку ниже и создай свиток покаяния.\n"
                         "Господь видит каждого. Не лги."),
            color=discord.Color.dark_red()
        )
        view = RegistrationTicketView()
        new_msg = await channel.send(embed=embed, view=view)
        await set_ticket_config(guild.id, message_id=new_msg.id)

        from cogs.ticket_appeal import AppealTicketView
        embed2 = discord.Embed(
            title="📜 Покаяние",
            description=("**Если тебя отлучили от братства и ты желаешь оспорить это решение, нажми на кнопку ниже.**\n"
                         "Создай свиток покаяния и изложи свою исповедь. Митрополит рассмотрит твоё дело."),
            color=discord.Color.dark_red()
        )
        view2 = AppealTicketView()
        await channel.send(embed=embed2, view=view2)

async def setup(bot):
    await bot.add_cog(ConfigBackup(bot))