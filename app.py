import streamlit as st
import yt_dlp
import os
from openai import OpenAI
from st_copy import copy_button

# Set up the Streamlit page
st.set_page_config(page_title="TikTok to Transcript", page_icon="🎵")

st.title("🎵 TikTok Audio Transcriber & Editor")
st.write("Paste a TikTok link to transcribe it. The app will automatically clean up the text, fix numbers, and format spacing.")

# --- Secure API Key Handling ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ OpenAI API Key not found! Please add `OPENAI_API_KEY` to your Streamlit Secrets.")
    st.stop()

# --- Custom System Prompt ---
# This tells GPT exactly how to behave, using your rules and examples
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

# --- Main UI ---
tiktok_url = st.text_input("Enter TikTok URL:", placeholder="https://www.tiktok.com/@username/video/123456789")

if st.button("Process Video"):
    if not tiktok_url:
        st.warning("Please enter a valid TikTok URL.")
    else:
        client = OpenAI(api_key=api_key)
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
                    final_text = response.choices[0].message.content

                st.success("Done!")
                
                # Display the final text
                st.markdown("### Final Script:")
                st.text_area(label="Output", value=final_text, height=400, label_visibility="collapsed")
                
                # Copy button
                copy_button(final_text, tooltip="Copy to clipboard", copied_label="Copied!")
                
            except Exception as e:
                st.error(f"Error during processing: {e}")
                
            finally:
                # Step 4: Clean up
                if os.path.exists(audio_path):
                    os.remove(audio_path)
