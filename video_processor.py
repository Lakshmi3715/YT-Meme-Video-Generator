# video_processor.py
import os
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip
import moviepy.video.fx.all as vfx
from moviepy.video.VideoClip import ColorClip


def create_full_video(images_folder, music_path, bg_video_path, output_path,
                      image_display_sec=7, fps=24, target_size=(1280,720)):
    """
    Full video: expects images_folder to have exactly 15 images.
    Each image displayed for image_display_sec seconds sequentially.
    target_size default is 1280x720 (16:9).
    """
    images = sorted([
        os.path.join(images_folder, f) for f in os.listdir(images_folder)
        if f.lower().endswith(('.png','.jpg','.jpeg'))
    ])
    if len(images) != 15:
        raise ValueError(f"Full video requires exactly 15 images; found {len(images)}")

    total_duration = 15 * image_display_sec

    # Prepare background: resize to target size, loop/trim
    bg = VideoFileClip(bg_video_path)
    bg = bg.resize(newsize=target_size)
    if bg.duration < total_duration:
        bg = vfx.loop(bg, duration=total_duration)
    else:
        bg = bg.subclip(0, total_duration)

    # Create image overlays sequentially (fit_inside logic, no cropping)
    image_clips = []
    target_ratio = target_size[0] / target_size[1]

    for i, img_path in enumerate(images):
        ic = ImageClip(img_path).set_duration(image_display_sec)

        # proportional resize to fit inside 16:9
        img_ratio = ic.w / ic.h
        if img_ratio > target_ratio:
            ic = ic.resize(width=target_size[0])
        else:
            ic = ic.resize(height=target_size[1])

        # center placement, no trimming
        ic = ic.set_position(("center", "center")).set_start(i * image_display_sec)
        image_clips.append(ic)

    composite = CompositeVideoClip([bg] + image_clips, size=target_size).set_duration(total_duration)

    # Audio: loop/trim
    audio = AudioFileClip(music_path)
    if audio.duration < total_duration:
        audio = vfx.loop(audio, duration=total_duration)
    else:
        audio = audio.subclip(0, total_duration)
    composite = composite.set_audio(audio)

    # Write out
    composite.write_videofile(output_path, fps=fps, codec='libx264', audio_codec='aac', threads=4)


def create_short_video(image_paths, music_path, bg_video_path, output_path,
                       duration=10, fps=30, target_size=(720,1280),
                       width_fraction=0.65, gap_px=40, margin_px=60):
    """
    Create a portrait short (default 720x1280, 9:16) showing two images stacked
    (top & bottom) with a gap so the background video remains visible.
    - image_paths: list of two image file paths
    - music_path, bg_video_path: files from assets
    """
    if len(image_paths) != 2:
        raise ValueError("Short video requires exactly 2 images")

    total_duration = duration
    target_w, target_h = target_size

    # --- Prepare background video: scale to portrait height, then crop or pad horizontally ---
    bg = VideoFileClip(bg_video_path)
    # Resize background to match target height first (preserve aspect)
    bg = bg.resize(height=target_h)

    if bg.w > target_w:
        # crop horizontally centered to target width
        bg = vfx.crop(bg, width=target_w, height=target_h, x_center=bg.w/2, y_center=bg.h/2)
    elif bg.w < target_w:
        # pad background onto a solid-color clip of target size
        background = ColorClip(size=(target_w, target_h), color=(0, 0, 0), duration=total_duration)
        bg = CompositeVideoClip([background, bg.set_position(("center", "center"))], size=(target_w, target_h))
    else:
        bg = bg.set_position(("center", "center"))

    # Ensure bg exact duration
    if bg.duration < total_duration:
        bg = vfx.loop(bg, duration=total_duration)
    else:
        bg = bg.subclip(0, total_duration)

    # --- Prepare image clips ---
    img_top = ImageClip(image_paths[0]).set_duration(total_duration)
    img_bottom = ImageClip(image_paths[1]).set_duration(total_duration)

    # Resize by width_fraction of target width to keep background visible.
    max_img_w = int(target_w * width_fraction)
    img_top = img_top.resize(width=max_img_w)
    img_bottom = img_bottom.resize(width=max_img_w)

    # If combined heights don't fit, scale down both proportionally
    combined_h = img_top.h + img_bottom.h + gap_px + 2 * margin_px
    if combined_h > target_h:
        scale = (target_h - gap_px - 2 * margin_px) / (img_top.h + img_bottom.h)
        img_top = img_top.resize(scale)
        img_bottom = img_bottom.resize(scale)

    # Compute vertical positions
    top_y = margin_px
    bottom_y = target_h - margin_px - img_bottom.h

    img_top = img_top.set_position(("center", top_y))
    img_bottom = img_bottom.set_position(("center", bottom_y))

    # Compose final clip
    composite = CompositeVideoClip([bg, img_top, img_bottom], size=(target_w, target_h)).set_duration(total_duration)

    # --- Audio: loop or trim music to duration ---
    audio = AudioFileClip(music_path)
    if audio.duration < total_duration:
        audio = vfx.loop(audio, duration=total_duration)
    else:
        audio = audio.subclip(0, total_duration)
    composite = composite.set_audio(audio)

    # write final file
    composite.write_videofile(output_path, fps=fps, codec='libx264', audio_codec='aac', threads=4)
