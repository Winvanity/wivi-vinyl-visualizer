import os
import math
import threading
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
from moviepy import AudioFileClip, VideoClip
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pygame

# ==============================================================================
# Wivi Vinyl Visualizer
# Created by: Winvanity // Damian Rzepczyński
# Year: 2026
# ==============================================================================

pygame.mixer.init()

def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def create_vinyl_disc(cover_img, diameter):
    vinyl = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vinyl)
    center = diameter // 2

    draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=(18, 18, 20, 255), outline=(45, 45, 50, 255), width=max(2, diameter // 230))

    for r in range(int(diameter * 0.22), int(diameter * 0.48), max(3, diameter // 100)):
        shade = 28 if (r % 10 == 0) else 22
        draw.ellipse(
            (center - r, center - r, center + r, center + r),
            outline=(shade, shade, shade + 2, 255),
            width=1
        )

    label_size = int(diameter * 0.36)
    label_img = cover_img.resize((label_size, label_size), Image.Resampling.LANCZOS).convert("RGBA")

    mask = Image.new("L", (label_size, label_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, label_size - 1, label_size - 1), fill=255)

    label_pos = (center - label_size // 2, center - label_size // 2)
    vinyl.paste(label_img, label_pos, mask)

    hole_r = int(diameter * 0.022)
    draw.ellipse(
        (center - hole_r, center - hole_r, center + hole_r, center + hole_r),
        fill=(15, 15, 15, 255),
        outline=(80, 80, 85, 255),
        width=max(2, diameter // 230)
    )
    return vinyl

def build_static_layers(cover_path, artist, title, width, height, custom_bg_path=None):
    raw_cover = Image.open(cover_path).convert("RGB")
    scale = height / 1080.0

    if custom_bg_path and os.path.exists(custom_bg_path):
        try:
            raw_bg = Image.open(custom_bg_path).convert("RGB")
            bg = raw_bg.resize((width, height), Image.Resampling.LANCZOS)
            dark_overlay = Image.new("RGB", (width, height), (10, 10, 14))
            bg = Image.blend(bg, dark_overlay, alpha=0.45).convert("RGBA")
        except Exception:
            bg = raw_cover.resize((width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=int(35 * scale)))
            dark_overlay = Image.new("RGB", (width, height), (10, 10, 14))
            bg = Image.blend(bg, dark_overlay, alpha=0.55).convert("RGBA")
    else:
        bg = raw_cover.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=int(35 * scale)))
        dark_overlay = Image.new("RGB", (width, height), (10, 10, 14))
        bg = Image.blend(bg, dark_overlay, alpha=0.55).convert("RGBA")

    sleeve_size = int(480 * scale)
    sleeve_x = int(460 * scale)
    sleeve_y = (height - sleeve_size) // 2 - int(40 * scale)

    shadow_size = sleeve_size + int(30 * scale)
    shadow = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    offset = int(15 * scale)
    shadow_draw.rectangle((offset, offset, sleeve_size + offset, sleeve_size + offset), fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(12 * scale)))
    bg.paste(shadow, (sleeve_x - offset, sleeve_y - int(10 * scale)), shadow)

    sleeve_img = raw_cover.resize((sleeve_size, sleeve_size), Image.Resampling.LANCZOS).convert("RGBA")
    bg.paste(sleeve_img, (sleeve_x, sleeve_y))

    draw = ImageDraw.Draw(bg)
    text_x = sleeve_x + sleeve_size + int(250 * scale)
    artist_font = get_font(int(34 * scale), bold=False)
    title_font = get_font(int(54 * scale), bold=True)

    draw.text((text_x, sleeve_y + int(150 * scale)), artist.upper(), font=artist_font, fill=(190, 190, 200, 255))
    draw.text((text_x, sleeve_y + int(205 * scale)), title, font=title_font, fill=(255, 255, 255, 255))

    vinyl_diameter = int(460 * scale)
    vinyl_disc = create_vinyl_disc(raw_cover, diameter=vinyl_diameter)
    
    vinyl_target_x = sleeve_x + sleeve_size - int(20 * scale)
    vinyl_target_y = sleeve_y + sleeve_size // 2
    vinyl_hidden_x = sleeve_x + sleeve_size // 2

    return bg, vinyl_disc, (vinyl_target_x, vinyl_target_y), vinyl_hidden_x, (sleeve_x, sleeve_y, sleeve_size)

def generate_video_process(audio_path, cover_path, output_path, artist, title, resolution_str, fps_val, vinyl_rpm, custom_bg_path, particles_enabled, p_count, p_speed_val, progress_callback):
    res_map = {
        "1280x720 (HD)": (1280, 720),
        "1920x1080 (Full HD)": (1920, 1080),
        "2560x1440 (2K)": (2560, 1440),
        "3840x2160 (4K UHD)": (3840, 2160)
    }
    width, height = res_map.get(resolution_str, (1920, 1080))
    fps = fps_val
    scale = height / 1080.0

    progress_callback("Loading and analyzing audio (FFT)...", 0)
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    total_time_str = format_time(duration)

    sample_rate = 22050
    audio_mono = audio.to_soundarray(fps=sample_rate)
    if len(audio_mono.shape) > 1:
        audio_mono = audio_mono.mean(axis=1)

    chunk_size = 2048
    
    def get_eq_bands(t, num_bars=32):
        idx = int(t * sample_rate)
        start = max(0, idx - chunk_size // 2)
        end = min(len(audio_mono), start + chunk_size)
        chunk = audio_mono[start:end]
        
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            
        windowed = chunk * np.hanning(len(chunk))
        fft_vals = np.abs(np.fft.rfft(windowed))
        
        bins_per_bar = len(fft_vals) // num_bars
        bars = []
        for i in range(num_bars):
            val = np.mean(fft_vals[i * bins_per_bar : (i + 1) * bins_per_bar])
            val_log = math.log1p(val * 50)
            bars.append(min(max(val_log / 5.0, 0.05), 1.0))
        return bars

    if particles_enabled and p_count > 0:
        np.random.seed(1337)
        p_x = np.random.uniform(0, width, p_count)
        p_y = np.random.uniform(0, height, p_count)
        p_speed = np.random.uniform(15 * scale * p_speed_val, 45 * scale * p_speed_val, p_count)
        p_size = np.random.randint(2, 6, p_count)
        p_alpha = np.random.randint(40, 120, p_count)
        p_drift_freq = np.random.uniform(0.5, 2.0, p_count)

    progress_callback(f"Generating graphic layers ({width}x{height}, {fps} FPS)...", 10)
    base_bg, vinyl_disc, vinyl_target_pos, vinyl_hidden_x, sleeve_rect = build_static_layers(
        cover_path, artist, title, width, height, custom_bg_path
    )
    sleeve_x, sleeve_y, sleeve_size = sleeve_rect
    sleeve_overlay = base_bg.crop((sleeve_x, sleeve_y, sleeve_x + sleeve_size, sleeve_y + sleeve_size))
    base_bg_rgb = np.array(base_bg.convert("RGB"), dtype=np.float32)
    time_font = get_font(int(24 * scale), bold=False)

    bar_x1 = int(460 * scale)
    bar_x2 = width - int(460 * scale)
    bar_y = sleeve_y + sleeve_size + int(80 * scale)
    bar_height = max(4, int(6 * scale))

    intro_outro_duration = 3.0
    total_frames = int(duration * fps)

    def make_frame(t):
        if total_frames > 0:
            current_frame = int(t * fps)
            pct = min(100.0, (current_frame / total_frames) * 100.0)
            ui_pct = 15 + int(pct * 0.82)
            progress_callback(f"Rendering: {format_time(t)} / {total_time_str} ({pct:.1f}%)", ui_pct)

        eq_bars = get_eq_bands(t, num_bars=32)
        bass_intensity = np.mean(eq_bars[:5])
        pulse_multiplier = 1.0 + (bass_intensity * 0.08)
        pulsed_bg_rgb = np.clip(base_bg_rgb * pulse_multiplier, 0, 255).astype(np.uint8)
        frame = Image.fromarray(pulsed_bg_rgb)

        if particles_enabled and p_count > 0:
            particles_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            p_draw = ImageDraw.Draw(particles_layer)
            for i in range(p_count):
                curr_y = (p_y[i] + p_speed[i] * t) % height
                curr_x = p_x[i] + math.sin(t * p_drift_freq[i] + i) * (15 * scale)
                sz = p_size[i] * scale
                p_draw.ellipse(
                    (curr_x, curr_y, curr_x + sz, curr_y + sz),
                    fill=(255, 255, 255, int(p_alpha[i]))
                )
            frame = Image.alpha_composite(frame.convert("RGBA"), particles_layer).convert("RGB")

        target_x, target_y = vinyl_target_pos
        
        if t < intro_outro_duration:
            progress = t / intro_outro_duration
            smooth_progress = 1.0 - math.pow(1.0 - progress, 3)
            current_vinyl_x = vinyl_hidden_x + (target_x - vinyl_hidden_x) * smooth_progress
        elif t > (duration - intro_outro_duration):
            time_left = duration - t
            progress = time_left / intro_outro_duration
            smooth_progress = 1.0 - math.pow(1.0 - progress, 3)
            current_vinyl_x = vinyl_hidden_x + (target_x - vinyl_hidden_x) * smooth_progress
        else:
            current_vinyl_x = target_x

        angle = -(t * (vinyl_rpm / 60.0) * 360.0) % 360
        rotated_vinyl = vinyl_disc.rotate(angle, resample=Image.Resampling.BICUBIC)
        vx = int(current_vinyl_x - rotated_vinyl.width // 2)
        vy = int(target_y - rotated_vinyl.height // 2)
        
        frame.paste(rotated_vinyl, (vx, vy), rotated_vinyl)
        frame.paste(sleeve_overlay, (sleeve_x, sleeve_y))

        draw = ImageDraw.Draw(frame)
        
        eq_width = bar_x2 - bar_x1
        total_bars = len(eq_bars)
        b_width = eq_width / total_bars
        max_eq_h = int(70 * scale)
        eq_y_base = bar_y - int(15 * scale)

        for i, val in enumerate(eq_bars):
            bx = bar_x1 + i * b_width
            bh = val * max_eq_h
            by = eq_y_base - bh
            draw.rounded_rectangle(
                (bx + 2, by, bx + b_width - 3, eq_y_base),
                radius=3,
                fill=(255, 255, 255, int(180 * val + 75))
            )

        progress = min(max(t / duration, 0.0), 1.0)
        current_x = int(bar_x1 + (bar_x2 - bar_x1) * progress)

        draw.rounded_rectangle((bar_x1, bar_y, bar_x2, bar_y + bar_height), radius=bar_height//2, fill=(255, 255, 255, 60))
        if current_x > bar_x1:
            draw.rounded_rectangle((bar_x1, bar_y, current_x, bar_y + bar_height), radius=bar_height//2, fill=(255, 255, 255, 240))
        
        dot_r = max(4, int(7 * scale))
        draw.ellipse((current_x - dot_r, bar_y + bar_height // 2 - dot_r, current_x + dot_r, bar_y + bar_height // 2 + dot_r), fill=(255, 255, 255, 255))

        curr_time_str = format_time(t)
        draw.text((bar_x1, bar_y + int(18 * scale)), curr_time_str, font=time_font, fill=(210, 210, 210))
        
        bbox = draw.textbbox((0, 0), total_time_str, font=time_font)
        tw = bbox[2] - bbox[0]
        draw.text((bar_x2 - tw, bar_y + int(18 * scale)), total_time_str, font=time_font, fill=(210, 210, 210))

        return np.array(frame)

    progress_callback("Rendering video...", 15)
    video = VideoClip(make_frame, duration=duration)
    video = video.with_audio(audio)

    video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="320k",
        preset="medium",
        threads=4,
        logger=None
    )
    progress_callback("Done! File saved successfully.", 100)

class VinylApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wivi Vinyl Visualizer")
        self.root.geometry("1140x780")
        self.root.minsize(1050, 720)

        self.audio_path = ""
        self.cover_path = ""
        self.bg_path = ""
        self.preview_photo = None
        self.is_playing = False

        BG_DARK = "#18181b"
        PANEL_BG = "#27272a"
        TEXT_COLOR = "#f4f4f5"
        ACCENT_COLOR = "#10b981"
        ACCENT_HOVER = "#059669"

        self.root.configure(bg=BG_DARK)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="#3f3f46", background="#3f3f46", foreground=TEXT_COLOR, selectbackground="#52525b", selectforeground=TEXT_COLOR)
        style.map("TCombobox", fieldbackground=[('readonly', '#3f3f46')], selectbackground=[('readonly', '#52525b')], selectforeground=[('readonly', '#f4f4f5')], background=[('readonly', '#3f3f46')])
        self.root.option_add('*TCombobox*Listbox.background', '#27272a')
        self.root.option_add('*TCombobox*Listbox.foreground', '#f4f4f5')
        self.root.option_add('*TCombobox*Listbox.selectBackground', '#3f3f46')
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#f4f4f5')

        main_layout = tk.Frame(root, bg=BG_DARK)
        main_layout.pack(fill="both", expand=True, padx=20, pady=20)

        left_outer_frame = tk.Frame(main_layout, bg=BG_DARK)
        left_outer_frame.pack(side="left", fill="y", padx=(0, 15))

        canvas = tk.Canvas(left_outer_frame, bg=PANEL_BG, highlightthickness=0, width=420)
        scrollbar = ttk.Scrollbar(left_outer_frame, orient="vertical", command=canvas.yview)
        
        left_panel = tk.Frame(canvas, bg=PANEL_BG, padx=16, pady=16)
        left_panel.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=left_panel, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="y", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(left_panel, text="Project Configuration", bg=PANEL_BG, fg=TEXT_COLOR, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 14))

        def add_file_row(parent, label_text, browse_command):
            tk.Label(parent, text=label_text, bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
            row_f = tk.Frame(parent, bg=PANEL_BG)
            row_f.pack(fill="x", pady=(0, 10))
            entry = tk.Entry(row_f, font=("Segoe UI", 9), bg="#3f3f46", fg=TEXT_COLOR, insertbackground="white", relief="flat")
            entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
            btn = tk.Button(row_f, text="Browse", command=browse_command, bg="#52525b", fg=TEXT_COLOR, activebackground="#71717a", activeforeground="white", relief="flat", font=("Segoe UI", 9), cursor="hand2")
            btn.pack(side="left", ipadx=10, ipady=2)
            return entry

        self.audio_entry = add_file_row(left_panel, "Audio File (MP3 / WAV):", self.select_audio)
        
        self.play_btn = tk.Button(left_panel, text="▶ Preview Audio", bg="#52525b", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", command=self.toggle_audio_preview, state="disabled", cursor="hand2")
        self.play_btn.pack(fill="x", pady=(0, 12), ipady=5)

        self.cover_entry = add_file_row(left_panel, "Cover Art (JPG / PNG):", self.select_cover)
        self.bg_entry = add_file_row(left_panel, "Custom Background (Optional):", self.select_bg)

        tk.Label(left_panel, text="Artist:", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.artist_entry = tk.Entry(left_panel, font=("Segoe UI", 10), bg="#3f3f46", fg=TEXT_COLOR, insertbackground="white", relief="flat")
        self.artist_entry.pack(fill="x", pady=(0, 10), ipady=3)
        self.artist_entry.insert(0, "Artist Name")
        self.artist_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        tk.Label(left_panel, text="Track Title:", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.title_entry = tk.Entry(left_panel, font=("Segoe UI", 10), bg="#3f3f46", fg=TEXT_COLOR, insertbackground="white", relief="flat")
        self.title_entry.pack(fill="x", pady=(0, 12), ipady=3)
        self.title_entry.insert(0, "New Track")
        self.title_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        res_fps_row = tk.Frame(left_panel, bg=PANEL_BG)
        res_fps_row.pack(fill="x", pady=(0, 12))

        res_col = tk.Frame(res_fps_row, bg=PANEL_BG)
        res_col.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(res_col, text="Resolution:", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.res_combobox = ttk.Combobox(res_col, state="readonly", font=("Segoe UI", 9))
        self.res_combobox['values'] = ["1920x1080 (Full HD)", "1280x720 (HD)", "2560x1440 (2K)", "3840x2160 (4K UHD)"]
        self.res_combobox.current(0)
        self.res_combobox.pack(fill="x", ipady=2)

        fps_col = tk.Frame(res_fps_row, bg=PANEL_BG)
        fps_col.pack(side="right", fill="x", expand=True, padx=(6, 0))
        tk.Label(fps_col, text="Framerate (FPS):", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.fps_combobox = ttk.Combobox(fps_col, state="readonly", font=("Segoe UI", 9))
        self.fps_combobox['values'] = ["30 FPS", "60 FPS"]
        self.fps_combobox.current(0)
        self.fps_combobox.pack(fill="x", ipady=2)

        tk.Label(left_panel, text="Vinyl Rotation Speed (RPM):", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.rpm_scale = tk.Scale(left_panel, from_=1, to=45, orient="horizontal", bg=PANEL_BG, fg=TEXT_COLOR, highlightthickness=0, troughcolor="#3f3f46", font=("Segoe UI", 8))
        self.rpm_scale.set(12)
        self.rpm_scale.pack(fill="x", pady=(0, 12))

        particle_frame = tk.LabelFrame(left_panel, text=" Dust Particles ", bg=PANEL_BG, fg="#a1a1aa", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        particle_frame.pack(fill="x", pady=(4, 0))

        self.particles_var = tk.BooleanVar(value=True)
        tk.Checkbutton(particle_frame, text="Enable falling dust", variable=self.particles_var, bg=PANEL_BG, fg=TEXT_COLOR, selectcolor="#3f3f46", activebackground=PANEL_BG, activeforeground=TEXT_COLOR, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))
        
        p_sliders_row = tk.Frame(particle_frame, bg=PANEL_BG)
        p_sliders_row.pack(fill="x")
        
        self.p_count_scale = tk.Scale(p_sliders_row, label="Count", from_=10, to=150, orient="horizontal", bg=PANEL_BG, fg=TEXT_COLOR, highlightthickness=0, troughcolor="#3f3f46", font=("Segoe UI", 8))
        self.p_count_scale.set(70)
        self.p_count_scale.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.p_speed_scale = tk.Scale(p_sliders_row, label="Speed", from_=0.2, to=3.0, resolution=0.1, orient="horizontal", bg=PANEL_BG, fg=TEXT_COLOR, highlightthickness=0, troughcolor="#3f3f46", font=("Segoe UI", 8))
        self.p_speed_scale.set(1.0)
        self.p_speed_scale.pack(side="right", fill="x", expand=True, padx=(6, 0))

        right_panel = tk.Frame(main_layout, bg=BG_DARK)
        right_panel.pack(side="right", fill="both", expand=True)

        tk.Label(right_panel, text="Final Video Frame Preview (16:9):", bg=BG_DARK, fg=TEXT_COLOR, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        
        preview_container = tk.Frame(right_panel, bg="#09090b", bd=1, relief="solid")
        preview_container.pack(fill="both", expand=True, pady=(0, 15))

        self.preview_canvas_label = tk.Label(preview_container, text="Select a cover image to see preview", bg="#09090b", fg="#71717a", font=("Segoe UI", 10))
        self.preview_canvas_label.pack(expand=True)

        action_frame = tk.Frame(right_panel, bg=BG_DARK)
        action_frame.pack(fill="x", pady=(0, 0))

        self.status_label = tk.Label(action_frame, text="Ready.", bg=BG_DARK, fg="#a1a1aa", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(anchor="w", pady=(0, 6))

        self.progress_bar = ttk.Progressbar(action_frame, orient="horizontal", mode="determinate", length=100)
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.generate_btn = tk.Button(action_frame, text="GENERATE MP4 VIDEO", bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 11, "bold"), relief="flat", activebackground=ACCENT_HOVER, activeforeground="white", command=self.start_generation, cursor="hand2")
        self.generate_btn.pack(fill="x", ipady=12)

    def select_audio(self):
        filename = filedialog.askopenfilename(title="Select Audio Track", filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if filename:
            self.audio_path = filename
            self.audio_entry.delete(0, tk.END)
            self.audio_entry.insert(0, filename)
            self.play_btn.config(state="normal")
            if self.is_playing:
                pygame.mixer.music.stop()
                self.is_playing = False
                self.play_btn.config(text="▶ Preview Audio", bg="#52525b")

    def select_cover(self):
        filename = filedialog.askopenfilename(title="Select Cover Art", filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if filename:
            self.cover_path = filename
            self.cover_entry.delete(0, tk.END)
            self.cover_entry.insert(0, filename)
            self.update_preview()

    def select_bg(self):
        filename = filedialog.askopenfilename(title="Select Background", filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if filename:
            self.bg_path = filename
            self.bg_entry.delete(0, tk.END)
            self.bg_entry.insert(0, filename)
            self.update_preview()

    def update_preview(self):
        if not self.cover_path or not os.path.exists(self.cover_path):
            return
        
        try:
            prev_w, prev_h = 560, 315
            artist = self.artist_entry.get().strip()
            title = self.title_entry.get().strip()

            render_w, render_h = 1920, 1080
            
            base_bg, vinyl_disc, vinyl_target_pos, _, sleeve_rect = build_static_layers(
                self.cover_path, artist, title, render_w, render_h, self.bg_path if self.bg_path else None
            )
            
            sleeve_x, sleeve_y, sleeve_size = sleeve_rect
            sleeve_overlay = base_bg.crop((sleeve_x, sleeve_y, sleeve_x + sleeve_size, sleeve_y + sleeve_size))

            v_cx, v_cy = vinyl_target_pos
            base_bg.paste(vinyl_disc, (v_cx - vinyl_disc.width // 2, v_cy - vinyl_disc.height // 2), vinyl_disc)
            base_bg.paste(sleeve_overlay, (sleeve_x, sleeve_y))

            bg_preview = base_bg.resize((prev_w, prev_h), Image.Resampling.LANCZOS)

            self.preview_photo = ImageTk.PhotoImage(bg_preview)
            self.preview_canvas_label.config(image=self.preview_photo, text="")
        except Exception as e:
            print("Preview error:", e)

    def toggle_audio_preview(self):
        if not self.audio_path:
            return
        
        if not self.is_playing:
            try:
                pygame.mixer.music.load(self.audio_path)
                pygame.mixer.music.play()
                self.is_playing = True
                self.play_btn.config(text="⏹ Stop Preview", bg="#dc2626")
            except Exception as e:
                messagebox.showerror("Audio Error", f"Cannot play file:\n{str(e)}")
        else:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.play_btn.config(text="▶ Preview Audio", bg="#52525b")

    def update_status(self, text, progress_val=None):
        self.status_label.config(text=text)
        if progress_val is not None:
            self.progress_bar["value"] = progress_val
        self.root.update_idletasks()

    def start_generation(self):
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.play_btn.config(text="▶ Preview Audio", bg="#52525b")

        audio = self.audio_entry.get().strip()
        cover = self.cover_entry.get().strip()
        custom_bg = self.bg_entry.get().strip()
        artist = self.artist_entry.get().strip()
        title = self.title_entry.get().strip()
        resolution = self.res_combobox.get()
        
        fps_str = self.fps_combobox.get()
        fps_val = 60 if "60" in fps_str else 30

        rpm = self.rpm_scale.get()
        particles_on = self.particles_var.get()
        p_count = int(self.p_count_scale.get())
        p_speed = float(self.p_speed_scale.get())

        if not audio or not os.path.exists(audio):
            messagebox.showerror("Error", "Please select a valid audio file!")
            return
        if not cover or not os.path.exists(cover):
            messagebox.showerror("Error", "Please select a valid cover image!")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video Files", "*.mp4")],
            title="Save rendered video as..."
        )
        if not output_path:
            return

        self.generate_btn.config(state="disabled", bg="#52525b")
        self.progress_bar["value"] = 0
        
        def run_thread():
            try:
                generate_video_process(
                    audio, cover, output_path, artist, title, resolution, fps_val, rpm, 
                    custom_bg, particles_on, p_count, p_speed, self.update_status
                )
                messagebox.showinfo("Success", f"Video has been rendered successfully!\nSaved to:\n{output_path}")
                self.update_status("Completed successfully!", 100)
            except Exception as e:
                messagebox.showerror("Rendering Error", f"An error occurred:\n{str(e)}")
                self.update_status("Error during rendering.", 0)
            finally:
                self.generate_btn.config(state="normal", bg="#10b981")

        threading.Thread(target=run_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VinylApp(root)
    root.mainloop()