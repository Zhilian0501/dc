import discord
from discord.ext import commands
import sqlite3
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# SQLite 初始化
conn = sqlite3.connect("database.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS violations (user_id TEXT PRIMARY KEY, count INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suggestions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, content TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id TEXT, target_id TEXT, description TEXT)")
conn.commit()

# 黑名單詞彙載入
with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = set([line.strip().lower() for line in f if line.strip()])

# ----- 不當言語監測 -----
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if any(word in message.content.lower() for word in blacklist):
        await message.delete()
        await message.channel.send(f"{message.author.mention} 請注意言詞，此訊息含有不當內容。", delete_after=5)

        # 更新違規次數
        user_id = str(message.author.id)
        c.execute("SELECT count FROM violations WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if row:
            count = row[0] + 1
            c.execute("UPDATE violations SET count = ? WHERE user_id = ?", (count, user_id))
        else:
            count = 1
            c.execute("INSERT INTO violations (user_id, count) VALUES (?, ?)", (user_id, count))
        conn.commit()

        # 警告或禁言
        if count == 3:
            await message.channel.send(f"{message.author.mention} 警告：已違規 3 次，請停止不當發言。")
        elif count >= 5:
            await message.author.timeout(duration=300, reason="過多不當發言")
            await message.channel.send(f"{message.author.mention} 已被暫時禁言 5 分鐘。")

    await bot.process_commands(message)

# ----- 檢舉 -----
@bot.command()
async def report(ctx, member: discord.Member, *, description):
    channel = await ctx.guild.create_text_channel(name=f"檢舉-{ctx.author.name}", category=None)
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await channel.set_permissions(ctx.author, read_messages=True)
    await channel.set_permissions(bot.user, read_messages=True)

    c.execute("INSERT INTO reports (reporter_id, target_id, description) VALUES (?, ?, ?)",
              (str(ctx.author.id), str(member.id), description))
    conn.commit()

    await channel.send(f"📣 **檢舉通知**\n舉報人：{ctx.author.mention}\n被檢舉人：{member.mention}\n原因：{description}")
    await ctx.send("✅ 檢舉已提交，管理員將儘快處理。")

# ----- 客服 -----
@bot.command()
async def support(ctx):
    channel = await ctx.guild.create_text_channel(name=f"客服-{ctx.author.name}")
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await channel.set_permissions(ctx.author, read_messages=True)
    await channel.set_permissions(bot.user, read_messages=True)
    await channel.send(
        f"{ctx.author.mention} 🎧 歡迎使用客服系統\n請簡述您遇到的問題，我們將盡快協助您。"
    )
    await ctx.send("✅ 客服頻道已建立。")

# ----- 建議 -----
@bot.command()
async def suggest(ctx, *, content):
    c.execute("INSERT INTO suggestions (user_id, content) VALUES (?, ?)", (str(ctx.author.id), content))
    conn.commit()
    channel = discord.utils.get(ctx.guild.text_channels, name="建議區")  # 建議頻道名稱
    if channel:
        await channel.send(f"💡 **來自 {ctx.author.display_name} 的建議：**\n{content}")
    await ctx.send("✅ 感謝您的寶貴建議！")

# ----- 啟動 -----
@bot.event
async def on_ready():
    print(f"🤖 Bot 已上線：{bot.user}")

bot.run("YOUR_BOT_TOKEN")  # ← 換成你的 Discord Bot Token
