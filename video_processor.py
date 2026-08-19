# video_processor.py
import os
import sys
import subprocess
from PIL import Image

def detect_qsv_support():
    """
    Run a runtime probe to verify if Intel Quick Sync Video (h264_qsv)
    is compiled and functional on the current hardware/drivers.
    """
    try:
        # Check if h264_qsv is in encoders list
        res = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if "h264_qsv" in res.stdout:
            # Probe encode functionality using a dummy frame
            test_cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=100x100:d=0.1",
                "-c:v", "h264_qsv", "-f", "null", "-"
            ]
            test_run = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if test_run.returncode == 0:
                print("Intel QSV hardware acceleration (h264_qsv) is supported and functional.")
                return True
            else:
                print("Intel QSV encoder detected but not functional. Falling back to software encoding.")
        else:
            print("Intel QSV encoder (h264_qsv) not found in FFmpeg configuration.")
    except Exception as e:
        print(f"Error checking QSV support: {e}. Falling back to software encoding.")
    return False


def run_ffmpeg_command(cmd, total_duration, fallback_cmd=None):
    """
    Run FFmpeg command in a subprocess, parsing the stdout for progress reports
    and drawing a clean, custom progress bar in the terminal.
    """
    # Insert progress flag right after ffmpeg executable name
    progress_cmd = [cmd[0]] + ["-progress", "-"] + cmd[1:]
    
    print(f"Starting video generation (Duration: {total_duration}s)...")
    
    # Run the process
    process = subprocess.Popen(
        progress_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    current_time = 0.0
    speed = "N/A"
    bar_len = 30
    
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("out_time_us="):
                try:
                    us = int(line.split("=")[1])
                    current_time = us / 1000000.0
                except ValueError:
                    pass
            elif line.startswith("speed="):
                speed = line.split("=")[1]
            elif line.startswith("progress=end"):
                current_time = total_duration
            
            # Render custom progress bar
            percent = min(100.0, (current_time / total_duration) * 100.0)
            filled_len = int(round(bar_len * percent / 100))
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            sys.stdout.write(f"\rProgress: |{bar}| {percent:.1f}% ({current_time:.1f}s/{total_duration:.1f}s) Speed: {speed}")
            sys.stdout.flush()
            
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        process.kill()
        raise e
        
    process.wait()
    
    if process.returncode != 0:
        stderr_output = process.stderr.read()
        print(f"\nFFmpeg command failed with return code {process.returncode}")
        print(f"FFmpeg Error Output:\n{stderr_output}")
        if fallback_cmd:
            print("Attempting fallback command...")
            fallback_progress_cmd = [fallback_cmd[0]] + ["-progress", "-"] + fallback_cmd[1:]
            
            fallback_process = subprocess.Popen(
                fallback_progress_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            current_time = 0.0
            speed = "N/A"
            try:
                while True:
                    line = fallback_process.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line.startswith("out_time_us="):
                        try:
                            us = int(line.split("=")[1])
                            current_time = us / 1000000.0
                        except ValueError:
                            pass
                    elif line.startswith("speed="):
                        speed = line.split("=")[1]
                    elif line.startswith("progress=end"):
                        current_time = total_duration
                        
                    percent = min(100.0, (current_time / total_duration) * 100.0)
                    filled_len = int(round(bar_len * percent / 100))
                    bar = '█' * filled_len + '-' * (bar_len - filled_len)
                    sys.stdout.write(f"\rFallback Progress: |{bar}| {percent:.1f}% ({current_time:.1f}s/{total_duration:.1f}s) Speed: {speed}")
                    sys.stdout.flush()
                    
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception as e:
                fallback_process.kill()
                raise e
                
            fallback_process.wait()
            if fallback_process.returncode != 0:
                fallback_stderr = fallback_process.stderr.read()
                raise RuntimeError(f"FFmpeg fallback failed: {fallback_stderr}")
            return fallback_process
        else:
            raise RuntimeError(f"FFmpeg generation failed: {stderr_output}")
    return process


def create_full_video(images_folder, music_path, bg_video_path, output_path,
                      image_display_sec=7, fps=24, target_size=(1280, 720)):
    """
    Full video: expects images_folder to have exactly 15 images.
    Each image displayed for image_display_sec seconds sequentially.
    """
    images = sorted([
        os.path.join(images_folder, f) for f in os.listdir(images_folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    if len(images) != 15:
        raise ValueError(f"Full video requires exactly 15 images; found {len(images)}")

    total_duration = 15 * image_display_sec
    target_w, target_h = target_size
    use_qsv = detect_qsv_support()

    # Dynamically build FFmpeg filter graph
    # Inputs:
    # 0: bg_video
    # 1..15: images (15 inputs)
    # 16: music
    filters = []
    
    # Scale background video to match target dimensions
    filters.append(f"[0:v]scale={target_w}:{target_h}[bg]")
    
    last_label = "[bg]"
    for i in range(15):
        img_input = f"[{i+1}:v]"
        start_t = i * image_display_sec
        end_t = (i + 1) * image_display_sec
        
        # Proportional resize image to fit inside target box
        scale_filt = (
            f"scale=w='if(gt(iw/ih,{target_w}/{target_h}),{target_w},-1)':"
            f"h='if(gt(iw/ih,{target_w}/{target_h}),-1,{target_h})'"
        )
        scaled_label = f"[img{i}]"
        filters.append(f"{img_input}{scale_filt}{scaled_label}")
        
        # Overlay current image centered, active during its display window
        out_label = f"[v{i}]" if i < 14 else "[outv]"
        overlay_filt = (
            f"{last_label}{scaled_label}overlay="
            f"x='({target_w}-w)/2':y='({target_h}-h)/2':"
            f"enable='between(t,{start_t},{end_t})'"
        )
        filters.append(f"{overlay_filt}{out_label}")
        last_label = f"[v{i}]" if i < 14 else "[outv]"
        
    filter_complex = ";".join(filters)

    # Base commands
    base_cmd_inputs = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_video_path
    ]
    for img in images:
        base_cmd_inputs += ["-loop", "1", "-i", img]
    base_cmd_inputs += ["-stream_loop", "-1", "-i", music_path]

    # Shared parameters
    shared_params = [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "16:a",
        "-t", str(total_duration),
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "128k"
    ]

    # Main Command (QSV if supported)
    if use_qsv:
        cmd = base_cmd_inputs + shared_params + [
            "-c:v", "h264_qsv",
            "-global_quality", "25",
            "-preset", "faster",
            output_path
        ]
        # Fallback to software encoding if QSV command fails
        fallback_cmd = base_cmd_inputs + shared_params + [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    else:
        cmd = base_cmd_inputs + shared_params + [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        fallback_cmd = None

    run_ffmpeg_command(cmd, total_duration, fallback_cmd)


def create_short_video(image_paths, music_path, bg_video_path, output_path,
                       duration=10, fps=30, target_size=(720, 1280),
                       width_fraction=0.65, gap_px=40, margin_px=60):
    """
    Create a portrait short (default 720x1280, 9:16) showing two images stacked
    (top & bottom) with a gap so the background video remains visible.
    """
    if len(image_paths) != 2:
        raise ValueError("Short video requires exactly 2 images")

    total_duration = duration
    target_w, target_h = target_size
    use_qsv = detect_qsv_support()

    # Pre-calculate sizes using Pillow to build simple FFmpeg filters
    with Image.open(image_paths[0]) as im1:
        w1, h1 = im1.size
    with Image.open(image_paths[1]) as im2:
        w2, h2 = im2.size

    max_img_w = int(target_w * width_fraction)
    
    # Scale aspect ratio calculations
    s1 = max_img_w / w1
    s2 = max_img_w / w2
    
    h1_scaled = int(h1 * s1)
    h2_scaled = int(h2 * s2)
    
    # Downscale if combined height exceeds boundaries
    combined_h = h1_scaled + h2_scaled + gap_px + 2 * margin_px
    if combined_h > target_h:
        scale = (target_h - gap_px - 2 * margin_px) / (h1_scaled + h2_scaled)
        h1_scaled = int(h1_scaled * scale)
        h2_scaled = int(h2_scaled * scale)
        w1_final = int(max_img_w * scale)
        w2_final = int(max_img_w * scale)
    else:
        w1_final = max_img_w
        w2_final = max_img_w
        
    top_y = margin_px
    bottom_y = target_h - margin_px - h2_scaled

    # Filter Complex:
    # 0: bg_video
    # 1: top image
    # 2: bottom image
    # 3: music
    filters = []
    
    # Resize background video to match target height, crop horizontally centered
    filters.append(f"[0:v]scale=-1:{target_h},crop={target_w}:{target_h}[bg]")
    
    # Scale images
    filters.append(f"[1:v]scale={w1_final}:{h1_scaled}[img1]")
    filters.append(f"[2:v]scale={w2_final}:{h2_scaled}[img2]")
    
    # Overlays
    filters.append(f"[bg][img1]overlay=x=({target_w}-w)/2:y={top_y}[tmp1]")
    filters.append(f"[tmp1][img2]overlay=x=({target_w}-w)/2:y={bottom_y}[outv]")
    
    filter_complex = ";".join(filters)

    # Base commands
    base_cmd_inputs = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_video_path,
        "-loop", "1", "-i", image_paths[0],
        "-loop", "1", "-i", image_paths[1],
        "-stream_loop", "-1", "-i", music_path
    ]

    # Shared parameters
    shared_params = [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "3:a",
        "-t", str(total_duration),
        "-r", str(fps),
        "-c:a", "aac",
        "-b:a", "128k"
    ]

    # Main Command (QSV if supported)
    if use_qsv:
        cmd = base_cmd_inputs + shared_params + [
            "-c:v", "h264_qsv",
            "-global_quality", "25",
            "-preset", "faster",
            output_path
        ]
        # Fallback to software encoding
        fallback_cmd = base_cmd_inputs + shared_params + [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    else:
        cmd = base_cmd_inputs + shared_params + [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        fallback_cmd = None

    run_ffmpeg_command(cmd, total_duration, fallback_cmd)
