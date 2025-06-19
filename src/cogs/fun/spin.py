import discord
from discord.ext import commands
import random
import asyncio
import io
import os
import logging
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor, ImageOps, ImageChops, ImageEnhance
import math
import colorsys
import numpy as np

from src.utils.database import initialize_mongodb
from src.utils.community.turkoyto.xp_manager import XPManager

def add_glow(img, amount=3, color=(255, 0, 255)):
    """Add neon glow effect to an image"""
    alpha = img.getchannel('A')
    glow = Image.new('RGBA', img.size, color + (0,))
    glow.putalpha(alpha)
    for i in range(amount):
        glow = glow.filter(ImageFilter.GaussianBlur(5))
    enhancer = ImageEnhance.Brightness(glow)
    glow = enhancer.enhance(1.5)
    result = ImageChops.composite(img, glow, glow)
    return result

def create_gradient(width, height, color1, color2, horizontal=True):
    """Create a gradient image between two colors"""
    base = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    for i in range(width if horizontal else height):
        t = i / (width if horizontal else height)
        color = tuple(int(a + (b - a) * t) for a, b in zip(color1, color2))
        if horizontal:
            draw.line([(i, 0), (i, height)], fill=color)
        else:
            draw.line([(0, i), (width, i)], fill=color)
    return base

def draw_grid(img, spacing=20, color=(100, 0, 255, 50), line_width=1):
    """Draw a synthwave grid pattern"""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    vanishing_point_y = h * 2
    for y in range(0, h, spacing):
        y_perspective = h - ((h - y) ** 1.1)
        if y_perspective < h:
            draw.line([(0, y_perspective), (w, y_perspective)], fill=color, width=line_width)
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=color, width=line_width)
    return img

logger = logging.getLogger('spin_cog')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/spin.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class Spin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = initialize_mongodb()
        self.xp_manager = XPManager(self.mongodb)
        self.spin_button_custom_id = "turkoyto_synthwave_spinwheel"
        self.ADD_EXP_CHANNEL_ID = 1288154600226160680
        self.WINNERS_CHANNEL_ID = 1288155323583955057
        self.prizes = [
            {"value": 100, "color": "#FF5177", "probability": 60.0, "name": "Sıradan", "glow": (255, 81, 119)},
            {"value": 250, "color": "#36F9F6", "probability": 29.0, "name": "Sık", "glow": (54, 249, 246)},
            {"value": 500, "color": "#9D4EDD", "probability": 7.0, "name": "Nadir", "glow": (157, 78, 221)},
            {"value": 1000, "color": "#F0E14A", "probability": 3.0, "name": "Epik", "glow": (240, 225, 74)},
            {"value": 7000, "color": "#FE53BB", "probability": 1.0, "name": "Efsane", "glow": (254, 83, 187)},
        ]
        self.synthwave_bg = (5, 5, 20)
        self.synthwave_pink = (255, 81, 119, 255)
        self.synthwave_blue = (54, 249, 246, 255)
        self.synthwave_purple = (157, 78, 221, 255)
        self.synthwave_yellow = (240, 225, 74, 255)
        self.synthwave_grid = (100, 0, 255, 70)
        self._prepare_wheel_assets()
        logger.info("Synthwave Spin cog initialized")

    def _prepare_wheel_assets(self):
        size = 800
        radius = 280
        center = size // 2
        self.wheel_size = size
        self.wheel_radius = radius
        self.wheel_center = center
        self.base_wheel = Image.new("RGBA", (size, size), self.synthwave_bg + (255,))
        sun_grad = create_gradient(size, size//2, (80, 0, 80, 255), (200, 50, 100, 0), horizontal=False)
        self.base_wheel.paste(sun_grad, (0, size//2), sun_grad)
        draw_grid(self.base_wheel, spacing=30, color=self.synthwave_grid, line_width=1)
        wheel_bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(wheel_bg)
        draw.ellipse([center - radius - 10, center - radius - 10, center + radius + 10, center + radius + 10], fill=(15, 10, 30, 255), outline=None)
        wheel_bg_glow = add_glow(wheel_bg, amount=5, color=self.synthwave_purple[:3])
        self.base_wheel.paste(wheel_bg_glow, (0, 0), wheel_bg_glow)
        draw = ImageDraw.Draw(self.base_wheel)
        total_prob = sum(p["probability"] for p in self.prizes)
        angle = 90
        self.segment_meta = []
        segment_gap = 2.0
        for prize in self.prizes:
            seg_angle = 360 * (prize["probability"] / total_prob) - segment_gap
            end_angle = angle + seg_angle
            color = ImageColor.getrgb(prize["color"])
            draw.pieslice(
                [center - radius, center - radius, center + radius, center + radius],
                start=angle, end=end_angle, fill=color + (230,), outline=None
            )
            self.segment_meta.append({
                "name": prize["name"], 
                "value": prize["value"],
                "color": prize["color"], 
                "start": angle, 
                "end": end_angle,
                "glow": prize["glow"]
            })
            angle = end_angle + segment_gap
        segment_outline = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        outline_draw = ImageDraw.Draw(segment_outline)
        for seg in self.segment_meta:
            outline_draw.arc(
                [center - radius, center - radius, center + radius, center + radius],
                start=seg["start"], end=seg["end"], fill=(255, 255, 255, 230), width=3
            )
            start_rad = math.radians(seg["start"])
            end_rad = math.radians(seg["end"])
            start_x = center + radius * math.cos(start_rad)
            start_y = center - radius * math.sin(start_rad)
            end_x = center + radius * math.cos(end_rad)
            end_y = center - radius * math.sin(end_rad)
            outline_draw.line([(center, center), (start_x, start_y)], fill=(255, 255, 255, 230), width=2)
            outline_draw.line([(center, center), (end_x, end_y)], fill=(255, 255, 255, 230), width=2)
        segment_outline_glow = add_glow(segment_outline, amount=2, color=(255, 255, 255))
        self.base_wheel.paste(segment_outline_glow, (0, 0), segment_outline_glow)
        hub_size = 80
        hub = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        hub_draw = ImageDraw.Draw(hub)
        hub_draw.ellipse(
            [center - hub_size, center - hub_size, center + hub_size, center + hub_size], 
            fill=(20, 10, 40, 255), outline=self.synthwave_blue[:3], width=4
        )
        hub_draw.ellipse(
            [center - hub_size//2, center - hub_size//2, center + hub_size//2, center + hub_size//2], 
            fill=(40, 20, 60, 255), outline=self.synthwave_pink[:3], width=2
        )
        try:
            font_path = "resources/fonts/Gotham-Black.otf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 24)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        hub_draw.text((center - 40, center - 12), "SPIN", font=font, fill=self.synthwave_yellow)
        hub_glow = add_glow(hub, amount=4, color=self.synthwave_blue[:3])
        self.base_wheel.paste(hub_glow, (0, 0), hub_glow)
        self.wheel_stand = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        stand_draw = ImageDraw.Draw(self.wheel_stand)
        stand_width = 200
        stand_height = 140
        stand_left = center - stand_width // 2
        stand_top = size - stand_height
        stand_points = [
            (stand_left, stand_top),
            (stand_left + stand_width, stand_top),
            (stand_left + stand_width + 40, size),
            (stand_left - 40, size),
        ]
        stand_draw.polygon(stand_points, fill=(30, 10, 50, 255))
        for i in range(5):
            y_pos = stand_top + (stand_height * i // 4)
            offset = int(i * 10 * (stand_height - (y_pos - stand_top)) / stand_height)
            stand_draw.line(
                [(stand_left - offset, y_pos), (stand_left + stand_width + offset, y_pos)],
                fill=self.synthwave_grid, width=2
            )
        platform_outline = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        platform_draw = ImageDraw.Draw(platform_outline)
        platform_draw.line(stand_points + [stand_points[0]], fill=self.synthwave_pink, width=3)
        platform_glow = add_glow(platform_outline, amount=5, color=self.synthwave_pink[:3])
        self.wheel_stand.paste(platform_glow, (0, 0), platform_glow)
        self.pointer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        pointer_draw = ImageDraw.Draw(self.pointer)
        pointer_tip_y = center - radius - 15
        pointer_shape = [
            (center, pointer_tip_y),
            (center - 25, pointer_tip_y + 40),
            (center - 15, pointer_tip_y + 50),
            (center, pointer_tip_y + 35),
            (center + 15, pointer_tip_y + 50),
            (center + 25, pointer_tip_y + 40),
        ]
        pointer_draw.polygon(pointer_shape, fill=(255, 255, 255, 220))
        pointer_draw.rectangle(
            [center - 15, pointer_tip_y + 40, center + 15, pointer_tip_y + 60],
            fill=(40, 20, 60, 255), outline=self.synthwave_yellow[:3], width=2
        )
        pointer_glow = add_glow(self.pointer, amount=5, color=self.synthwave_yellow[:3])
        self.base_wheel_with_frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.base_wheel_with_frame.paste(self.wheel_stand, (0, 0), self.wheel_stand)
        self.base_wheel_with_frame.paste(self.base_wheel, (0, 0), self.base_wheel)
        self.base_wheel_with_frame.paste(pointer_glow, (0, 0), pointer_glow)
        scanlines = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        scanlines_draw = ImageDraw.Draw(scanlines)
        for y in range(0, size, 2):
            scanlines_draw.line([(0, y), (size, y)], fill=(0, 0, 0, 30), width=1)
        self.base_wheel_with_frame = ImageChops.multiply(self.base_wheel_with_frame, scanlines)

    def get_color_at_pointer_tip(self, wheel_image):
        center = self.wheel_center
        y = center - self.wheel_radius - 15
        try:
            colors = [
                wheel_image.getpixel((center, y))[:3],
                wheel_image.getpixel((center-1, y+1))[:3],
                wheel_image.getpixel((center+1, y+1))[:3]
            ]
            return tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
        except Exception:
            return (255, 255, 255)

    def get_prize_from_color(self, sampled_rgb):
        min_dist = float('inf')
        closest = self.prizes[0]
        for prize in self.prizes:
            prize_rgb = ImageColor.getrgb(prize["color"])
            dist = sum((a - b) ** 2 for a, b in zip(sampled_rgb, prize_rgb))
            if dist < min_dist:
                min_dist = dist
                closest = prize
        return closest

    def calculate_remaining_cooldown(self, last_spin_time):
        if not last_spin_time:
            return None, True
        now = datetime.now()
        cooldown_end = last_spin_time + timedelta(days=1)
        if now >= cooldown_end:
            return None, True
        time_left = cooldown_end - now
        h, rem = divmod(time_left.seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s", False

    @commands.hybrid_command(name="spin", description="Turk Oyuncu Topluluğu Synthwave Çarkıfelek! XP kazan.")
    async def spin_command(self, ctx: commands.Context):
        user = ctx.author
        is_interaction = ctx.interaction is not None
        view = SpinButton(self)
        user_data = self.mongodb["users"].find_one({"user_id": str(user.id)})
        last_spin_time = user_data.get("last_spin_time") if user_data else None
        remaining_time, can_spin = self.calculate_remaining_cooldown(last_spin_time)
        if can_spin:
            status_message = "⚡ H A Z I R ! ⚡"
        else:
            status_message = f"⏳ B E K L E M E: **{remaining_time}**"
        embed = discord.Embed(
            title="🌆 S Y N T H W A V E  Ç A R K I F E L E K 🌆",
            description=f"Her gün 1 kez çarkı çevir, XP kazan!\n\n**D U R U M:** {status_message}",
            color=discord.Color.from_rgb(157, 78, 221)
        )
        prize_info = "\n".join([
            f"{self.get_rarity_emoji(p['name'])} **{p['name']}**: {p['value']} XP ({p['probability']}%)"
            for p in self.prizes
        ])
        embed.add_field(name="Ö D Ü L L E R", value=prize_info, inline=False)
        
        # Create a more visible wheel image
        wheel_img = self.base_wheel_with_frame.copy()
        
        # Enhance the brightness, contrast and saturation
        enhancer = ImageEnhance.Brightness(wheel_img)
        wheel_img = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Contrast(wheel_img)
        wheel_img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Color(wheel_img)
        wheel_img = enhancer.enhance(1.4)
        
        # Add a shimmer effect
        shimmer = Image.new("RGBA", (self.wheel_size, self.wheel_size), (0, 0, 0, 0))
        shimmer_draw = ImageDraw.Draw(shimmer)
        for i in range(20):
            angle = random.uniform(0, 360)
            length = random.randint(50, 200)
            center_x, center_y = self.wheel_center, self.wheel_center
            end_x = center_x + length * math.cos(math.radians(angle))
            end_y = center_y + length * math.sin(math.radians(angle))
            shimmer_draw.line(
                [(center_x, center_y), (end_x, end_y)],
                fill=(255, 255, 255, 25),
                width=2
            )
        wheel_img = Image.alpha_composite(wheel_img, shimmer)
        
        # Add a border to make it stand out with double glow
        border_img = Image.new("RGBA", (self.wheel_size + 20, self.wheel_size + 20), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.rectangle(
            [0, 0, self.wheel_size + 19, self.wheel_size + 19],
            outline=self.synthwave_pink, width=5
        )
        
        # Double glow effect
        pink_glow = add_glow(border_img, amount=5, color=self.synthwave_pink[:3])
        blue_border = Image.new("RGBA", (self.wheel_size + 20, self.wheel_size + 20), (0, 0, 0, 0))
        blue_draw = ImageDraw.Draw(blue_border)
        blue_draw.rectangle(
            [10, 10, self.wheel_size + 9, self.wheel_size + 9],
            outline=self.synthwave_blue, width=3
        )
        blue_glow = add_glow(blue_border, amount=3, color=self.synthwave_blue[:3])
        
        # Create a final composite image with synthwave background
        final_img = Image.new("RGBA", (self.wheel_size + 20, self.wheel_size + 20), (10, 5, 30, 255))
        
        # Add synthwave grid to background
        grid_bg = Image.new("RGBA", (self.wheel_size + 20, self.wheel_size + 20), (10, 5, 30, 255))
        draw_grid(grid_bg, spacing=20, color=(100, 0, 255, 40), line_width=1)
        final_img = Image.alpha_composite(final_img, grid_bg)
        
        # Add sun gradient
        sun_grad = create_gradient(self.wheel_size + 20, (self.wheel_size + 20)//2, 
                                  (80, 0, 80, 255), (200, 50, 100, 0), horizontal=False)
        final_img.paste(sun_grad, (0, (self.wheel_size + 20)//2), sun_grad)
        
        final_img.paste(pink_glow, (0, 0), pink_glow)
        final_img.paste(blue_glow, (0, 0), blue_glow)
        final_img.paste(wheel_img, (10, 10), wheel_img)
        
        # Add extra text
        try:
            font_path = "resources/fonts/Gotham-Black.otf"
            if os.path.exists(font_path):
                big_font = ImageFont.truetype(font_path, 36)
                small_font = ImageFont.truetype(font_path, 20)
            else:
                big_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
        except Exception:
            big_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            
        text_overlay = Image.new("RGBA", (self.wheel_size + 20, self.wheel_size + 20), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_overlay)
        
        text_draw.text(
            (self.wheel_size//2 - 150, 15), 
            "SYNTHWAVE ÇARKIFELEĞİ", 
            font=big_font, 
            fill=self.synthwave_yellow
        )
        
        text_draw.text(
            (self.wheel_size//2 - 100, self.wheel_size - 30), 
            "Her gün çevir, XP kazan!", 
            font=small_font, 
            fill=self.synthwave_blue[:3]
        )
        
        text_glow = add_glow(text_overlay, amount=3, color=self.synthwave_blue[:3])
        final_img.paste(text_glow, (0, 0), text_glow)
        
        # Save to BytesIO
        wheel_bytes = io.BytesIO()
        final_img.save(wheel_bytes, format='PNG')
        wheel_bytes.seek(0)
        
        file = discord.File(wheel_bytes, filename="synthwave_wheel.png")
        embed.set_image(url="attachment://synthwave_wheel.png")
        
        if not can_spin:
            for item in view.children:
                item.disabled = True
                item.label = f"COOLDOWN: {remaining_time}"
        send_kwargs = {"embed": embed, "view": view, "file": file}
        if is_interaction:
            send_kwargs["ephemeral"] = True
            await ctx.interaction.response.send_message(**send_kwargs)
        else:
            await ctx.send(**send_kwargs)

    def get_rarity_emoji(self, rarity):
        if rarity == "Efsane":
            return "🔮"
        elif rarity == "Epik":
            return "💫"
        elif rarity == "Nadir":
            return "✨"
        elif rarity == "Sık":
            return "🌟"
        else:
            return "⭐"

class SpinButton(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=None)
        self.parent = parent
        button = discord.ui.Button(
            label="S P I N !",
            style=discord.ButtonStyle.primary,
            custom_id=parent.spin_button_custom_id,
            emoji="🌌"
        )
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction):
        user_id = interaction.user.id
        now = datetime.now()
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        user_data = self.parent.mongodb["users"].find_one({"user_id": str(user_id)})
        last_spin_time = user_data.get("last_spin_time") if user_data else None
        if not is_admin and last_spin_time:
            remaining_time, can_spin = self.parent.calculate_remaining_cooldown(last_spin_time)
            if not can_spin:
                embed = discord.Embed(
                    title="⏰ C O O L D O W N",
                    description=f"Tekrar çevirmek için **{remaining_time}** beklemelisin.",
                    color=discord.Color.from_rgb(255, 81, 119)
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)
        except Exception:
            pass
        if not is_admin:
            self.parent.mongodb["users"].update_one(
                {"user_id": str(user_id)},
                {"$set": {"last_spin_time": now}},
                upsert=True
            )
        num_frames = 24
        wheel_size = self.parent.wheel_size
        center = self.parent.wheel_center
        full_rot = 2 + random.random() * 3
        final_angle = random.uniform(0, 360)
        total_rotation = full_rot * 360 + final_angle
        frames = []
        for i in range(num_frames):
            prog = i / (num_frames - 1)
            if prog < 0.7:
                eased = prog * 1.2
            else:
                eased = 0.84 + (prog - 0.7) * 0.16 / 0.3
            angle = (total_rotation * eased) % 360
            frame = self.parent.base_wheel_with_frame.copy()
            rotated = frame.rotate(-angle, center=(center, center), resample=Image.BICUBIC)
            if prog < 0.5:
                blur_amount = int(5 * (1 - prog * 2))
                if blur_amount > 0:
                    rotated = rotated.filter(ImageFilter.GaussianBlur(blur_amount * 0.3))
            if prog < 0.6:
                speed_draw = ImageDraw.Draw(rotated)
                lines = 12
                for j in range(lines):
                    line_angle = (360 / lines * j + angle * 0.5) % 360
                    line_rad = math.radians(line_angle)
                    x = center + (wheel_size // 2) * math.cos(line_rad)
                    y = center + (wheel_size // 2) * math.sin(line_rad)
                    opacity = int(200 * (1 - prog))
                    speed_draw.line(
                        [(center, center), (x, y)], 
                        fill=(255, 255, 255, opacity), 
                        width=1
                    )
            frame_bytes = io.BytesIO()
            rotated.save(frame_bytes, format='PNG')
            frame_bytes.seek(0)
            frames.append(frame_bytes)
            if i % 4 == 0:
                await asyncio.sleep(0.01)
        spin_msg = await interaction.followup.send(
            embed=discord.Embed(
                title="🌈 S P I N  W A V E  A C T I V A T E D",
                color=discord.Color.from_rgb(157, 78, 221)
            ).set_image(url="attachment://spin0.png"),
            file=discord.File(frames[0], filename="spin0.png"),
            ephemeral=True, wait=True
        )
        for i in range(1, num_frames):
            embed = spin_msg.embeds[0]
            if i < num_frames * 0.3:
                embed.title = "🌈 S P I N  W A V E  A C T I V A T E D"
            elif i < num_frames * 0.7:
                embed.title = "⚡ M A X I M U M  O V E R D R I V E ⚡"
            else:
                embed.title = "💫 S T A B I L I Z I N G..."
            embed.set_image(url=f"attachment://spin{i}.png")
            await spin_msg.edit(embed=embed, attachments=[discord.File(frames[i], filename=f"spin{i}.png")])
            if i < num_frames * 0.7:
                await asyncio.sleep(0.08 + (i / num_frames) * 0.12)
            else:
                await asyncio.sleep(0.2 + ((i - num_frames * 0.7) / (num_frames * 0.3)) * 0.3)
        final_img = Image.open(frames[-1])
        sampled_color = self.parent.get_color_at_pointer_tip(final_img)
        prize = self.parent.get_prize_from_color(sampled_color)
        member = interaction.user
        guild_id = interaction.guild.id if interaction.guild else None
        await self.parent.xp_manager.add_exp_from_command(
            interaction, member, guild_id, prize["value"], "spin"
        )
        
        # Create an enhanced final result image
        final_bytes = io.BytesIO()
        final_highlight = final_img.copy()
        
        # Add dramatic lighting
        lighting = Image.new("RGBA", final_highlight.size, (0, 0, 0, 0))
        lighting_draw = ImageDraw.Draw(lighting)
        
        # Create a radial gradient for dramatic lighting
        center_x, center_y = self.parent.wheel_center, self.parent.wheel_center
        max_radius = self.parent.wheel_size // 2
        
        for r in range(max_radius, 0, -1):
            opacity = int(100 * (1 - r/max_radius))
            lighting_draw.ellipse(
                [center_x - r, center_y - r, center_x + r, center_y + r],
                outline=prize["glow"] + (opacity,),
                width=2
            )
        
        final_highlight = Image.alpha_composite(final_highlight, lighting)
        
        # Highlight the winning segment with intense glow
        draw = ImageDraw.Draw(final_highlight)
        for seg in self.parent.segment_meta:
            if seg["name"] == prize["name"]:
                segment_outline = Image.new("RGBA", (self.parent.wheel_size, self.parent.wheel_size), (0, 0, 0, 0))
                outline_draw = ImageDraw.Draw(segment_outline)
                outline_draw.arc(
                    [
                        self.parent.wheel_center - self.parent.wheel_radius, 
                        self.parent.wheel_center - self.parent.wheel_radius,
                        self.parent.wheel_center + self.parent.wheel_radius,
                        self.parent.wheel_center + self.parent.wheel_radius
                    ],
                    start=seg["start"], end=seg["end"], 
                    fill=(255, 255, 255, 220), width=15
                )
                
                # Add sparkles around the winning segment
                mid_angle = (seg["start"] + seg["end"]) / 2
                for i in range(10):
                    spark_angle = mid_angle + random.uniform(-20, 20)
                    spark_rad = math.radians(spark_angle)
                    distance = self.parent.wheel_radius * 0.8
                    spark_x = self.parent.wheel_center + distance * math.cos(spark_rad)
                    spark_y = self.parent.wheel_center - distance * math.sin(spark_rad)
                    
                    spark_size = random.randint(5, 15)
                    outline_draw.ellipse(
                        [spark_x-spark_size, spark_y-spark_size, 
                         spark_x+spark_size, spark_y+spark_size],
                        fill=prize["glow"] + (200,)
                    )
                
                segment_glow = add_glow(segment_outline, amount=10, color=prize["glow"])
                final_highlight.paste(segment_glow, (0, 0), segment_glow)
                break
        
        # Add a banner showing what was won
        banner = Image.new("RGBA", (self.parent.wheel_size, 100), (20, 10, 40, 200))
        banner_draw = ImageDraw.Draw(banner)
        
        try:
            font_path = "resources/fonts/Gotham-Black.otf"
            if os.path.exists(font_path):
                prize_font = ImageFont.truetype(font_path, 36)
                info_font = ImageFont.truetype(font_path, 24)
            else:
                prize_font = ImageFont.load_default()
                info_font = ImageFont.load_default()
        except Exception:
            prize_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        banner_draw.text(
            (self.parent.wheel_size//2 - 150, 15),
            f"{self.parent.get_rarity_emoji(prize['name'])} {prize['name'].upper()} KAZANDIN!",
            font=prize_font,
            fill=ImageColor.getrgb(prize["color"])
        )
        
        banner_draw.text(
            (self.parent.wheel_size//2 - 100, 60),
            f"⚡ {prize['value']} XP ÖDÜLÜ ⚡",
            font=info_font,
            fill=(255, 255, 255)
        )
        
        banner_glow = add_glow(banner, amount=5, color=prize["glow"])
        final_highlight.paste(banner_glow, (0, self.parent.wheel_size - 100), banner_glow)
        
        final_highlight.save(final_bytes, format='PNG')
        final_bytes.seek(0)
        final_file = discord.File(final_bytes, filename="spin_final.png")
        
        result_embed = discord.Embed(
            title=f"{self.parent.get_rarity_emoji(prize['name'])} {prize['name'].upper()} KAZANDIN! {self.parent.get_rarity_emoji(prize['name'])}",
            description=f"⚡ **{prize['value']} XP** ⚡\n\n*Retro-Future Güçleri Aktive Edildi!*",
            color=discord.Color.from_str(prize["color"])
        )
        result_embed.set_image(url="attachment://spin_final.png")
        next_spin_time = now + timedelta(days=1)
        formatted_time = next_spin_time.strftime('%Y-%m-%d %H:%M')
        result_embed.set_footer(text=f"NEXT SPIN: {formatted_time}")
        await spin_msg.edit(
            content="🌌 **S Y N T H W A V E  P R I Z E  D E T E C T E D** 🌌",
            embed=result_embed,
            attachments=[final_file]
        )
        try:
            winners_channel = self.parent.bot.get_channel(self.parent.WINNERS_CHANNEL_ID)
            if winners_channel and prize["name"] in ["Nadir", "Epik", "Efsane"]:
                win_embed = discord.Embed(
                    title=f"🏆 {prize['name'].upper()} ÖDÜL KAZANILDI! 🏆",
                    description=f"{member.mention} çarktan **{prize['value']} XP** kazandı!",
                    color=discord.Color.from_str(prize["color"])
                )
                win_embed.set_image(url="attachment://spin_final.png")
                win_embed.set_footer(text=f"SYNTHWAVE SPIN • {now.strftime('%Y-%m-%d %H:%M')}")
                await winners_channel.send(
                    content=f"⚡ **SYNTHWAVE ALERT** ⚡",
                    embed=win_embed,
                    file=final_file
                )
            logs_channel = self.parent.bot.get_channel(self.parent.ADD_EXP_CHANNEL_ID)
            if logs_channel:
                log_embed = discord.Embed(
                    title="🌌 Synthwave Spin Log",
                    description=f"{member} ({member.id}) {prize['name']} kazandı: {prize['value']} XP",
                    color=discord.Color.from_str(prize["color"])
                )
                await logs_channel.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Spin log/winner send error: {e}")
        self.parent.mongodb["spins"].insert_one({
            "user_id": str(member.id),
            "guild_id": str(guild_id) if guild_id else "dm",
            "prize_name": prize["name"],
            "prize_value": prize["value"],
            "spin_time": now,
            "theme": "synthwave"
        })

async def setup(bot):
    cog = Spin(bot)
    await bot.add_cog(cog)
    bot.add_view(SpinButton(cog))
    logger.info("Synthwave Spin cog loaded successfully")
