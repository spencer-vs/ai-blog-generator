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
import assemblyai
from groq import Groq
from .models import BlogPost
import re
import requests
import time




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
        # transcription = transcription[:1200]
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
    
    
    
# ---------------- TRANSCRIPT FUNCTIONS ---------------- #
def get_transcription(video_id):
    # """Try YouTube transcript first. If unavailable, fallback to AssemblyAI."""
   
    # try:
    #     transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    #     transcript_text = " ".join([entry['text'] for entry in transcript])
    #     return transcript_text
    # except Exception as e:
    #     print(f"YouTube transcript error: {e}")
    # # fallback to AssemblyAI
    # return get_transcription_assemblyai(video_id)
    
    
    """Attempt to retrieve a transcript using YouTubeTranscriptApi.

    If the YouTube API call fails (missing method, no transcript, etc.), we
    fall back to AssemblyAI. This version avoids using
    ``list_transcripts`` which may not exist in older installations.
    """

    try:
        # instantiate client (allows better compatibility across versions)
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id, languages=["en"])
        # the returned object is iterable of FetchedTranscriptSnippet
        transcript_text = " ".join([snippet.text for snippet in transcript_data])
        return transcript_text
    except Exception as e:
        # log and continue to fallback
        print(f"YouTube transcript error for video {video_id}: {type(e).__name__}: {e}")

    return get_transcription_assemblyai(video_id)
# ---------------- TRANSCRIPTION HELPERS ---------------- #
def get_transcription_assemblyai(video_id):
    """Use AssemblyAI to transcribe the YouTube video when transcript is unavailable."""
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("AssemblyAI API key missing")
        return None
    try:
        assemblyai.settings.api_key = api_key
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        transcriber = assemblyai.Transcriber()
        config = assemblyai.TranscriptionConfig(speech_model="universal-2")
        transcript = transcriber.transcribe(youtube_url, config=config)
        if transcript.status == "error":
            print("AssemblyAI transcription error:", transcript.error)
            return None
        return transcript.text
    except Exception as e:
        print("AssemblyAI service error:", e)
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






















