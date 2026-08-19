1\. Create venv, activate: (python -m venv venv 
                            venv\Scripts\activate)

2\. Install dependencies: pip install -r requirements.txt

3\. Ensure ffmpeg is installed and available in PATH:
    Windows: Download from ffmpeg.org and add it to the PATH (or use Chocolatey: choco install ffmpeg).

4\. Go to /venv/Lib/site-packages/moviepy/video/fx/resize.py and replace 'Image.ANTIALIAS' with 'Image.Resampling.LANCZOS'

5\. Run: python app.py

6\. Open http://127.0.0.1:5000 in your browser.