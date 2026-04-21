import streamlit as st
import yt_dlp
import os
import requests
from openai import OpenAI
from st_copy import copy_button

# Set up the Streamlit page
st.set_page_config(page_title="TikTok to Transcript", page_icon="🎵")

st.title("🎵 TikTok Audio Transcriber & Editor")
st.write("Paste a TikTok link to transcribe it, clean it up, and generate an ElevenLabs voiceover.")

# --- Secure API Key Handling ---
if "OPENAI_API_KEY" in st.secrets:
    openai_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ OpenAI API Key not found!")
    st.stop()

if "ELEVENLABS_API_KEY" in st.secrets:
    elevenlabs_key = st.secrets["ELEVENLABS_API_KEY"]
else:
    st.error("⚠️ ElevenLabs API Key not found! Please add `ELEVENLABS_API_KEY` to your Streamlit Secrets.")
    st.stop()

# --- Custom System Prompt ---
SYSTEM_PROMPT = """You are a precise script editor. Your job is to clean up raw video transcripts to make them highly readable while keeping changes minimal. 

STRICT RULES:
1. Fix minor mistakes and improve readability, but do not rewrite the whole script. Keep changes minimal.
2. You MUST completely remove the phrase "The last one will blow your mind." (and any close variations).
3. Convert spelled-out numbers used in lists to digits (e.g., change "Number one" to "Number 1"). Do not change "$4,000" to "4,000 dollars" unless improving readability. 
4. Add proper paragraph spacing. Create a new paragraph for the intro, and a new paragraph for each numbered item.

EXAMPLE INPUT:
Things you throw away that are worth stupid money. The last one will blow your mind. Number one, Lego pieces. Old Lego pieces can be surprisingly valuable. Rare minifigures and discontinued parts are highly collectible. One of the most famous examples is the Mr. Gold minifigure released in 2013.

EXAMPLE OUTPUT:
Things you throw away that could be worth serious money. 

Number 1, Lego pieces. Old Lego parts can be surprisingly valuable, especially rare minifigures and discontinued sets. One well known example is the Mister Gold minifigure released in 2013.
"""

# --- Session State Initialization ---
# This ensures your transcript isn't wiped out when you click the voiceover button
if "final_transcript" not in st.session_state:
    st.session_state.final_transcript = None

# --- Main UI ---
tiktok_url = st.text_input("Enter TikTok URL:", placeholder="https://www.tiktok.com/@username/video/123456789")

if st.button("Process Video"):
    if not tiktok_url:
        st.warning("Please enter a valid TikTok URL.")
    else:
        client = OpenAI(api_key=openai_key)
        audio_path = "temp_audio.mp3"
        
        # Step 1: Download the Audio
        with st.spinner("Downloading audio from TikTok..."):
            ydl_opts = {
                'format': 'best',
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
            except Exception as e:
                st.error(f"Error downloading from TikTok: {e}")
                st.stop()

        # Step 2: Transcribe with Whisper
        with st.spinner("Transcribing with OpenAI Whisper..."):
            try:
                with open(audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                
                raw_text = transcript.text
                
                # Step 3: Edit with GPT-5.4
                with st.spinner("Applying edits and formatting with GPT-5.4..."):
                    response = client.chat.completions.create(
                        model="gpt-5.4",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"Please edit this transcript according to the rules:\n\n{raw_text}"}
                        ]
                    )
                    # Save it to the app's short-term memory
                    st.session_state.final_transcript = response.choices[0].message.content

            except Exception as e:
                st.error(f"Error during processing: {e}")
                
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

# --- Display Results & Voiceover Generator ---
# We put this OUTSIDE the button logic above, so it stays visible!
if st.session_state.final_transcript:
    st.success("Script processed successfully!")
    
    st.markdown("### Final Script:")
    st.text_area(label="Output", value=st.session_state.final_transcript, height=400, label_visibility="collapsed")
    copy_button(st.session_state.final_transcript, tooltip="Copy to clipboard", copied_label="Copied!")
    
    st.markdown("---")
    st.markdown("### 🎙️ Generate Voiceover")
    
    if st.button("Generate Voiceover"):
        with st.spinner("Generating voiceover with ElevenLabs..."):
            voice_id = "IRHApOXLvnW57QJPQH2P"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_key
            }
            
            # Your exact custom settings
            data = {
                "text": st.session_state.final_transcript,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.58,
                    "similarity_boost": 0.68,
                    "style": 0.0,
                    "speed": 1.12,
                    "use_speaker_boost": True
                }
            }
            
            try:
                response = requests.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    # Show an audio player to listen immediately
                    st.audio(response.content, format="audio/mp3")
                    
                    # Provide a button to download the MP3
                    st.download_button(
                        label="Download Voiceover",
                        data=response.content,
                        file_name="adam_voiceover.mp3",
                        mime="audio/mpeg"
                    )
                    st.success("Voiceover ready!")
                else:
                    st.error(f"ElevenLabs Error: {response.text}")
            except Exception as e:
                st.error(f"Failed to generate voiceover: {e}")
