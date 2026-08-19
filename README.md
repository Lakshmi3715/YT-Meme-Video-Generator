# YT Meme Video Generator

1. Create venv, activate:
   ```bash
   python -m venv venv 
   venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is installed and available in PATH:
   * Windows: Download from ffmpeg.org and add it to the PATH (or use Chocolatey: `choco install ffmpeg`).

4. **[OBSOLETE / NO LONGER REQUIRED]** Go to `/venv/Lib/site-packages/moviepy/video/fx/resize.py` and replace `'Image.ANTIALIAS'` with `'Image.Resampling.LANCZOS'`
   * *Justification:* This step was previously required because MoviePy used an outdated Pillow constant (`Image.ANTIALIAS`) which was deprecated and completely removed in modern Pillow versions (Pillow 10+), causing the app to crash. The project has now been fully migrated to run directly on native FFmpeg, removing the MoviePy dependency entirely. This manual step is no longer needed.

5. Run the web server:
   ```bash
   python app.py
   ```

6. Open http://127.0.0.1:5000 in your browser.