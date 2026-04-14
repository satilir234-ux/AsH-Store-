import os
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone
from collections import defaultdict

# ─── AYARLAR ───────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")  # Tokeni Railway'den çekecek
PREFIX = "."
# ────────────────────────────────────────────────────────────────────────────────

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Mesaj sayacı: {guild_id: {user_id: {"gunluk": int, "toplam": int}}}
mesaj_sayaci = defaultdict(lambda: defaultdict(lambda: {"gunluk": 0, "toplam": 0}))
bugun = datetime.now(timezone.utc).date()


# ─── OLAYLAR ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak giriş yapıldı.")
    await bot.change_presence(activity=discord.Game(name=".yardım | Moderasyon Botu"))


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    global bugun
    global mesaj_sayaci

    # Her gün sayacı sıfırla
    simdi = datetime.now(timezone.utc).date()
    if simdi != bugun:
        bugun = simdi
        for g in mesaj_sayaci:
            for u in mesaj_sayaci[g]:
                mesaj_sayaci[g][u]["gunluk"] = 0

    guild_id = message.guild.id if message.guild else 0
    user_id = message.author.id
    mesaj_sayaci[guild_id][user_id]["gunluk"] += 1
    mesaj_sayaci[guild_id][user_id]["toplam"] += 1

    # AFK kontrolü
    if message.author.id in afk_listesi:
        sebep, zaman = afk_listesi.pop(message.author.id)
        fark = datetime.now(timezone.utc) - zaman
        dakika = int(fark.total_seconds() // 60)
        embed = discord.Embed(
            description=f"✅ {message.author.mention} AFK modundan çıktı. ({dakika} dakika AFK'ydı)",
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed, delete_after=5)
        try:
            isim = message.author.display_name.replace("[AFK] ", "")
            await message.author.edit(nick=isim)
        except:
            pass

    for bahsedilen in message.mentions:
        if bahsedilen.id in afk_listesi:
            sebep, zaman = afk_listesi[bahsedilen.id]
            embed = discord.Embed(
                description=f"💤 {bahsedilen.mention} şu anda AFK. Sebep: **{sebep}**",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed, delete_after=8)

    await bot.process_commands(message)

    mesaj = message.content.strip()
    if mesaj in ["sa", "Sa"]:
        await message.channel.send(f"{message.author.mention} **Aleykümselam, hoş geldin!**")

    await bot.process_commands(message)

# ─── YARDIM KOMUTU ─────────────────────────────────────────────────────────────

@bot.command(name="yardım", aliases=["yardim", "help"])
async def yardim(ctx):
    embed = discord.Embed(
        title="📋 Komut Listesi",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    komutlar = {
        ".ping": "Botun gecikmesini gösterir.",
        ".avatar [@kullanıcı]": "Kullanıcının avatarını gösterir.",
        ".banner [@kullanıcı]": "Kullanıcının bannerini gösterir.",
        ".afk [sebep]": "AFK moduna geçer.",
        ".ship @kullanıcı1 @kullanıcı2": "İki kişinin uyumunu hesaplar.",
        ".m [@kullanıcı]": "Mesaj sayısını gösterir.",
        ".lock": "Kanalı kilitler.",
        ".unlock": "Kanalı açar.",
        ".ban @kullanıcı [sebep]": "Kullanıcıyı banlar.",
        ".unban [kullanıcı ID]": "ID ile banı kaldırır.",
        ".kick @kullanıcı [sebep]": "Kullanıcıyı sunucudan atar.",
        ".mute @kullanıcı [süre] [sebep]": "Kullanıcıyı susturur.",
        ".unmute @kullanıcı": "Susturmayı kaldırır.",
        ".nuke": "Kanalı sıfırlar.",
        ".uyar @kullanıcı [sebep]": "Kullanıcıyı uyarır.",
        ".sil [miktar]": "Mesajları siler.",
    }
    for k, v in komutlar.items():
        embed.add_field(name=k, value=v, inline=False)
    embed.set_footer(text=f"İstenen: {ctx.author}")
    await ctx.send(embed=embed)


# ─── GENEL KOMUTLAR ────────────────────────────────────────────────────────────

@bot.command(name="ping")
async def ping(ctx):
    gecikme = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot gecikmesi: **{gecikme}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="avatar")
async def avatar(ctx, uye: discord.Member = None):
    uye = uye or ctx.author
    embed = discord.Embed(
        title=f"{uye.display_name} adlı kullanıcının avatarı",
        color=discord.Color.blue()
    )
    embed.set_image(url=uye.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="banner")
async def banner(ctx, uye: discord.Member = None):
    uye = uye or ctx.author
    
    # Banner bilgisini almak için fetch_user kullanıyoruz
    user = await bot.fetch_user(uye.id)
    
    if user.banner is None:
        embed = discord.Embed(
            description=f"❌ {uye.mention} kullanıcısının banneri yok!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    # Banner rengini al
    banner_rengi = user.accent_color
    
    embed = discord.Embed(
        title=f"{uye.display_name} adlı kullanıcının banneri",
        color=banner_rengi if banner_rengi else discord.Color.blue()
    )
    embed.set_image(url=user.banner.url)
    embed.set_footer(text=f"İstenen: {ctx.author.display_name}")
    await ctx.send(embed=embed)


afk_listesi = {}

@bot.command(name="afk")
async def afk(ctx, *, sebep: str = "Sebep belirtilmedi"):
    afk_listesi[ctx.author.id] = (sebep, datetime.now(timezone.utc))
    embed = discord.Embed(
        description=f"💤 {ctx.author.mention} AFK moduna geçti. Sebep: **{sebep}**",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)
    try:
        await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
    except:
        pass


@bot.command(name="ship")
async def ship(ctx, uye1: discord.Member, uye2: discord.Member = None):
    uye2 = uye2 or ctx.author
    import hashlib
    toplam = int(hashlib.md5(f"{uye1.id}{uye2.id}".encode()).hexdigest(), 16)
    yuzde = toplam % 101
    if yuzde < 30:
        yorum = "💔 Hiç uyumlu değiller..."
        renk = discord.Color.red()
    elif yuzde < 60:
        yorum = "💛 Orta düzey uyum."
        renk = discord.Color.yellow()
    elif yuzde < 85:
        yorum = "💙 İyi bir uyum var!"
        renk = discord.Color.blue()
    else:
        yorum = "❤️ Mükemmel bir çift!"
        renk = discord.Color.magenta()

    dolu = "❤️" * (yuzde // 10)
    bos = "🖤" * (10 - yuzde // 10)
    embed = discord.Embed(
        title="💘 Uyum Hesaplayıcı",
        description=(
            f"**{uye1.display_name}** ╳ **{uye2.display_name}**\n\n"
            f"{dolu}{bos}\n"
            f"**%{yuzde} uyum**\n\n"
            f"{yorum}"
        ),
        color=renk
    )
    await ctx.send(embed=embed)


@bot.command(name="m")
async def mesaj_sayisi(ctx, uye: discord.Member = None):
    uye = uye or ctx.author
    guild_id = ctx.guild.id
    veri = mesaj_sayaci[guild_id][uye.id]
    embed = discord.Embed(
        title=f"📊 {uye.display_name} — Mesaj İstatistikleri",
        color=discord.Color.blue()
    )
    embed.add_field(name="📅 Bugün", value=f"**{veri['gunluk']}** mesaj", inline=True)
    embed.add_field(name="📈 Tüm Zamanlar", value=f"**{veri['toplam']}** mesaj", inline=True)
    embed.set_thumbnail(url=uye.display_avatar.url)
    embed.set_footer(text="⚠️ Sayaç bot yeniden başlatılınca sıfırlanır.")
    await ctx.send(embed=embed)


# ─── MODERASYON KOMUTLARI ──────────────────────────────────────────────────────

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = discord.Embed(
        description=f"🔒 **{ctx.channel.name}** kanalı kilitlendi.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    embed = discord.Embed(
        description=f"🔓 **{ctx.channel.name}** kanalı açıldı.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, uye: discord.Member, *, sebep: str = "Sebep belirtilmedi"):
    if uye == ctx.author:
        return await ctx.send("❌ Kendini banlayamazsın!")
    if uye.top_role >= ctx.author.top_role:
        return await ctx.send("❌ Bu kişiyi banlayamazsın, rolü senden yüksek veya eşit!")
    await uye.ban(reason=sebep)
    embed = discord.Embed(
        title="🔨 Kullanıcı Banlandı",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Kullanıcı", value=f"{uye} (ID: {uye.id})", inline=False)
    embed.add_field(name="Yetkili", value=str(ctx.author), inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, kullanici_id: int):
    """Kullanıcı ID'si ile banı kaldırır. Örnek: .unban 123456789"""
    try:
        kullanici = await bot.fetch_user(kullanici_id)
    except discord.NotFound:
        return await ctx.send("❌ Bu ID'ye sahip bir kullanıcı bulunamadı.")

    try:
        await ctx.guild.unban(kullanici, reason=f"Banı kaldıran: {ctx.author}")
        embed = discord.Embed(
            title="✅ Ban Kaldırıldı",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Kullanıcı", value=f"{kullanici} (ID: {kullanici.id})", inline=False)
        embed.add_field(name="Yetkili", value=str(ctx.author), inline=True)
        embed.set_thumbnail(url=kullanici.display_avatar.url)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("❌ Bu kullanıcı zaten banlı değil.")
    except discord.Forbidden:
        await ctx.send("❌ Bu kullanıcının banını kaldırma yetkim yok.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, uye: discord.Member, *, sebep: str = "Sebep belirtilmedi"):
    if uye == ctx.author:
        return await ctx.send("❌ Kendini atamazsın!")
    await uye.kick(reason=sebep)
    embed = discord.Embed(
        title="👢 Kullanıcı Atıldı",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Kullanıcı", value=f"{uye} (ID: {uye.id})", inline=False)
    embed.add_field(name="Yetkili", value=str(ctx.author), inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, uye: discord.Member, sure: int = 10, *, sebep: str = "Sebep belirtilmedi"):
    from datetime import timedelta
    await uye.timeout(timedelta(minutes=sure), reason=sebep)
    embed = discord.Embed(
        title="🔇 Kullanıcı Susturuldu",
        color=discord.Color.dark_grey(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Kullanıcı", value=uye.mention, inline=True)
    embed.add_field(name="Süre", value=f"{sure} dakika", inline=True)
    embed.add_field(name="Yetkili", value=str(ctx.author), inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, uye: discord.Member):
    await uye.timeout(None)
    embed = discord.Embed(
        description=f"🔊 {uye.mention} adlı kullanıcının susturması kaldırıldı.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="nuke")
@commands.has_permissions(manage_channels=True)
async def nuke(ctx):
    kanal = ctx.channel
    embed = discord.Embed(
        description="⚠️ Bu kanalı nuke'lamak istediğinden emin misin? (evet/hayır)",
        color=discord.Color.red()
    )
    onay_msg = await ctx.send(embed=embed)

    def kontrol(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["evet", "hayır", "hayir"]

    try:
        cevap = await bot.wait_for("message", timeout=15.0, check=kontrol)
    except asyncio.TimeoutError:
        return await onay_msg.edit(content="❌ Süre doldu, işlem iptal edildi.", embed=None)

    if cevap.content.lower() != "evet":
        return await ctx.send("❌ Nuke işlemi iptal edildi.")

    yeni_kanal = await kanal.clone(reason=f"Nuke - {ctx.author}")
    await kanal.delete()
    embed2 = discord.Embed(
        title="💥 Kanal Nuke'landı!",
        description=f"Bu kanal {ctx.author.mention} tarafından sıfırlandı.",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    await yeni_kanal.send(embed=embed2)


uyari_listesi = defaultdict(list)

@bot.command(name="uyar")
@commands.has_permissions(manage_messages=True)
async def uyar(ctx, uye: discord.Member, *, sebep: str = "Sebep belirtilmedi"):
    uyari_listesi[uye.id].append({
        "sebep": sebep,
        "yetkili": str(ctx.author),
        "zaman": datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    })
    sayi = len(uyari_listesi[uye.id])
    embed = discord.Embed(
        title="⚠️ Kullanıcı Uyarıldı",
        color=discord.Color.yellow(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Kullanıcı", value=uye.mention, inline=True)
    embed.add_field(name="Toplam Uyarı", value=f"**{sayi}**", inline=True)
    embed.add_field(name="Yetkili", value=str(ctx.author), inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=False)
    await ctx.send(embed=embed)
    try:
        dm_embed = discord.Embed(
            title=f"⚠️ {ctx.guild.name} sunucusunda uyarıldın!",
            description=f"**Sebep:** {sebep}\n**Yetkili:** {ctx.author}\n**Toplam uyarın:** {sayi}",
            color=discord.Color.yellow()
        )
        await uye.send(embed=dm_embed)
    except:
        pass


@bot.command(name="sil")
@commands.has_permissions(manage_messages=True)
async def sil(ctx, miktar: int):
    if miktar < 1 or miktar > 100:
        return await ctx.send("❌ Lütfen 1 ile 100 arasında bir sayı gir.")
    await ctx.message.delete()
    silinen = await ctx.channel.purge(limit=miktar)
    mesaj = await ctx.send(
        embed=discord.Embed(
            description=f"🗑️ **{len(silinen)}** mesaj silindi.",
            color=discord.Color.red()
        )
    )
    await asyncio.sleep(3)
    await mesaj.delete()


# ─── HATA YÖNETİMİ ─────────────────────────────────────────────────────────────

@bot.event
async def on_command_error(ctx, hata):
    if isinstance(hata, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için yetkin yok!")
    elif isinstance(hata, commands.MemberNotFound):
        await ctx.send("❌ Kullanıcı bulunamadı!")
    elif isinstance(hata, commands.UserNotFound):
        await ctx.send("❌ Kullanıcı bulunamadı!")
    elif isinstance(hata, commands.BadArgument):
        await ctx.send("❌ Geçersiz argüman! Lütfen kullanımı kontrol et.")
    elif isinstance(hata, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Eksik argüman: `{hata.param.name}`. `.yardım` yazarak kullanımı öğrenebilirsin.")
    else:
        print(f"Hata: {hata}")


# ─── BOTU BAŞLAT ───────────────────────────────────────────────────────────────
bot.run(TOKEN)
