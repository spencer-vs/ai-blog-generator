from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from groq import Groq
from .models import BlogPost
import re
import requests




# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
load_dotenv(env_path)
# ---------------- HOME ---------------- #
@login_required
def index(request):
    return render(request, 'index.html')
# ---------------- BLOG GENERATOR ---------------- #
@csrf_exempt
@login_required
def generate_blog(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    try:
        data = json.loads(request.body)
        yt_link = data.get('link')
        if not yt_link:
            return JsonResponse({'error': 'No YouTube link provided'}, status=400)
        print(f"Generating blog for: {yt_link}")
        # Extract video ID
        video_id = get_video_id(yt_link)
        title = get_youtube_title(video_id)
        print("Extracted video ID:", video_id)
        if not video_id:
            return JsonResponse({'error': 'Invalid YouTube URL'}, status=400)
        # Get transcript
        transcription = get_transcription(video_id)
        if not transcription:
            return JsonResponse({'error': 'Transcript not available for this video'}, status=500)
        # Generate blog
        blog_content = generate_blog_from_transcript(transcription)
        if not blog_content:
            return JsonResponse({'error': 'Failed to generate blog'}, status=500)
        # Save blog to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()
        
        
        
        return JsonResponse({'content': blog_content})
    except Exception as e:
        print("SERVER ERROR:", e)
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
# ---------------- TRANSCRIPT FUNCTIONS ---------------- #
def get_video_id(url):
    try:
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print("Video ID extraction error:", e)
        return None
    
    
def get_youtube_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data["title"]
        return f"YouTube Video {video_id}"
    except Exception as e:
        print("Title fetch error:", e)
        return f"YouTube Video {video_id}"
    
    
    
def get_transcription(video_id):
    try:
        # First, check if transcripts are available
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        if not transcript_list:
            print("No transcripts available for video:", video_id)
            return None
        # Try to get the transcript (default to English)
        transcript = transcript_list.find_transcript(['en'])
        transcript_text = " ".join([t.text for t in transcript.fetch()])
        return transcript_text
    except Exception as e:
        print(f"Transcript error for video {video_id}: {type(e).__name__}: {e}")
        return None
# ---------------- AI BLOG GENERATION ---------------- #
def generate_blog_from_transcript(transcription):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Groq API key not found")
            return None
        client = Groq(api_key=api_key)
        prompt = f"""
        Based on the generated transcript, create a blog post based on the YouTube video, covering all aspects of the video.
        Transcript:
        {transcription}
        Article:
        """
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Groq error:", e)
        return None
# ---------------- BLOG LIST ---------------- #
@login_required
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})
@login_required
def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')
# ---------------- AUTH ---------------- #
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {
                'error_message': 'Invalid username or password'
            })
    return render(request, 'login.html')
def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        repeatPassword = request.POST.get('repeatPassword')
        if password != repeatPassword:
            return render(request, 'signup.html', {
                'error_message': 'Passwords do not match'
            })
        try:
            user = User.objects.create_user(username, email, password)
            login(request, user)
            return redirect('/')
        except Exception as e:
            print("Signup error:", e)
            return render(request, 'signup.html', {
                'error_message': 'Error creating account'
            })
    return render(request, 'signup.html')
def user_logout(request):
    logout(request)
    return redirect('/')






















# from django.shortcuts import render, redirect
# from django.contrib.auth.models import User
# from django.contrib.auth import authenticate, login, logout
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.csrf import csrf_exempt
# from django.http import JsonResponse
# from django.conf import settings
# import json
# import os
# from dotenv import load_dotenv
# import yt_dlp
# import assemblyai as aai
# from groq import Groq
# from .models import BlogPost

# # ✅ LOAD ENV VARIABLES - Specify the exact path
# env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
# load_dotenv(env_path)
# print(f"Loading .env from: {env_path}")


# @login_required
# def index(request):
#     return render(request, 'index.html')
# @csrf_exempt
# @login_required
# def generate_blog(request):
#     if request.method != "POST":
#         return JsonResponse({'error': 'Invalid request method'}, status=405)
#     try:
#         data = json.loads(request.body)
#         yt_link = data.get('link')
#         if not yt_link:
#             return JsonResponse({'error': 'No link provided'}, status=400)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)
#     try:
#         print(f"Generating blog for: {yt_link}")

#         # Get video title first
#         ydl_opts = {'nocheckcertificate': True}
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(yt_link, download=False)
#             title = info.get('title', 'Unknown Title')

#         transcription = get_transcription(yt_link)
#         if not transcription:
#             return JsonResponse({'error': 'Failed to get transcript. Check server logs for details.'}, status=500)
#         blog_content = generate_blog_from_transcript(transcription)
#         if not blog_content:
#             return JsonResponse({'error': 'Failed to generate blog. Check server logs for details.'}, status=500)

#         # Save the blog post to database
#         new_blog_article = BlogPost.objects.create(
#             user=request.user,
#             youtube_title=title,
#             youtube_link=yt_link,
#             generated_content=blog_content,
#         )
#         new_blog_article.save()

#         return JsonResponse({'content': blog_content})

#     except Exception as e:
#         print("SERVER ERROR:", e)
#         import traceback
#         traceback.print_exc()
#         return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

# def download_audio(link):
#     try:
#         output_template = os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s')
        
#         ydl_opts = {
#             'format': 'bestaudio/best',
#             'outtmpl': output_template,
#             'quiet': True,
#             'no_warnings': False,
#             'noplaylist': True,
#             'nocheckcertificate': True,
#             "http_headers": {
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
#             },
#             'sleep_interval': 3,
#             'max_sleep_interval': 5,
#             'extractor_args': {
#                 'youtube': {
#                     'player_client': ['android']
#                 }
#             },
#             'postprocessors': [{
#                 'key': 'FFmpegExtractAudio',
#                 'preferredcodec': 'mp3',
#                 'preferredquality': '192',
#             }],
            
#         }
        
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             print(f"Downloading audio from: {link}")
#             info = ydl.extract_info(link, download=True)
#             audio_file = ydl.prepare_filename(info)
#             # Change extension to .mp3
#             base, ext = os.path.splitext(audio_file)
#             mp3_file = base + '.mp3'
            
#             # If the file was converted, it might already be .mp3
#             if os.path.exists(mp3_file):
#                 print(f"Audio file ready: {mp3_file}")
#                 return mp3_file
#             elif os.path.exists(audio_file):
#                 print(f"Audio file ready: {audio_file}")
#                 return audio_file
#             else:
#                 print(f"Audio file not found at expected locations")
#                 return None
                
#     except Exception as e:
#         print(f"Download error: {e}")
#         import traceback
#         traceback.print_exc()
#         return None


# def get_transcription(link):
#     try:
#         print("Starting download...")
#         audio_file = download_audio(link)
#         if not audio_file:
#             print("Audio download failed.")
#             return None
        
#         # Check if file actually exists
#         if not os.path.exists(audio_file):
#             print(f"Audio file does not exist at path: {audio_file}")
#             return None
            
#         print("Audio downloaded:", audio_file)
#         api_key = os.getenv("ASSEMBLYAI_API_KEY")
#         print("AssemblyAI Key:", api_key if api_key else "NOT SET")
#         if not api_key:
#             print("AssemblyAI API key missing!")
#             return None
        
#         aai.settings.api_key = api_key
        
#         # Create transcription config with proper speech model
#         config = aai.TranscriptionConfig(
#             speech_models=["universal-2"]
#         )
        
#         transcriber = aai.Transcriber()
#         print("Sending file to AssemblyAI...")
#         transcript = transcriber.transcribe(audio_file, config=config)
#         print("Transcript status:", transcript.status)
        
#         if transcript.status == "error":
#             print("AssemblyAI error:", transcript.error)
#             return None
            
#         print("Transcript received successfully.")
#         return transcript.text
#     except Exception as e:
#         print("TRANSCRIPTION CRASH:", str(e))
#         import traceback
#         traceback.print_exc()
#         return None


# def generate_blog_from_transcript(transcription):
#     try:
#         api_key = os.getenv("GROQ_API_KEY")
#         print(f"GROQ_API_KEY found: {bool(api_key)}")
#         if not api_key:
#             print("Groq API key not found")
#             return None
        
#         print(f"Initializing Groq client...")
#         client = Groq(api_key=api_key)
        
#         prompt = f"""Based on the following transcript, write a professional blog article.
# Do not mention YouTube.
# Transcript:
# {transcription}
# Article:"""
        
#         print(f"Sending request to Groq API...")
#         completion = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0.7,
#             max_tokens=1000,
#         )
        
#         print(f"Response received from Groq")
#         return completion.choices[0].message.content.strip()
    
#     except Exception as e:
#         print("Groq error:", e)
#         import traceback
#         traceback.print_exc()
#         return None
# # ---------------- AUTH ---------------- #

# @login_required
# def blog_list(request):
#     blog_articles = BlogPost.objects.filter(user=request.user)
#     return render(request, "all-blogs.html", {'blog_articles': blog_articles})

# @login_required
# def blog_details(request, pk):
#     blog_article_detail = BlogPost.objects.get(id=pk)
#     if request.user == blog_article_detail.user:
#         return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
#     else:
#         return redirect('/')


# def user_login(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
#         if user:
#             login(request, user)
#             return redirect('/')
#         else:
#             return render(request, 'login.html', {
#                 'error_message': 'Invalid username or password'
#             })
#     return render(request, 'login.html')
# def user_signup(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         repeatPassword = request.POST.get('repeatPassword')
#         if password != repeatPassword:
#             return render(request, 'signup.html', {
#                 'error_message': 'Passwords do not match'
#             })
#         try:
#             user = User.objects.create_user(username, email, password)
#             login(request, user)
#             return redirect('/')
#         except Exception as e:
#             print("Signup error:", e)
#             return render(request, 'signup.html', {
#                 'error_message': 'Error creating account'
#             })
#     return render(request, 'signup.html')
# def user_logout(request):
#     logout(request)
#     return redirect('/')













