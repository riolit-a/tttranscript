import streamlit as st
import yt_dlp
import os
from openai import OpenAI

# Set up the Streamlit page
st.set_page_config(page_title="TikTok to Transcript", page_icon="🎵")

st.title("🎵 TikTok Audio Transcriber")
st.write("Paste a TikTok link to download the audio and transcribe it using OpenAI's Whisper model.")

# --- Sidebar ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Get this from platform.openai.com")

# --- Main UI ---
tiktok_url = st.text_input("Enter TikTok URL:", placeholder="https://www.tiktok.com/@username/video/123456789")

if st.button("Transcribe Audio"):
    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")
    elif not tiktok_url:
        st.warning("Please enter a valid TikTok URL.")
    else:
        client = OpenAI(api_key=api_key)
        audio_path = "temp_audio.mp3"
        
        # Step 1: Download the Audio
        with st.spinner("Downloading audio from TikTok..."):
            ydl_opts = {
                'format': 'best', # Grabs the best video/audio combo
                'outtmpl': 'temp_audio.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'nocheckcertificate': True
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([tiktok_url])
                st.success("Audio extracted successfully!")
            except Exception as e:
                st.error(f"Error downloading from TikTok: {e}")
                st.stop()

        # Step 2: Transcribe with Whisper
        with st.spinner("Transcribing with OpenAI Whisper..."):
            try:
                with open(audio_path, "rb") as audio_file:
                    # whisper-1 is the API endpoint for OpenAI's v2 large model
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                
                st.success("Transcription complete!")
                
                st.markdown("### Full Transcript:")
                # Use a text area so the user can easily copy the result
                st.text_area(label="", value=transcript.text, height=300)
                
            except Exception as e:
                st.error(f"Error during transcription: {e}")
                
            finally:
                # Step 3: Clean up the temporary audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)