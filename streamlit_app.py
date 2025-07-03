import os
from dotenv import load_dotenv
import streamlit as st
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip
from tempfile import NamedTemporaryFile, mkdtemp

# Load environment variables from .env file
load_dotenv()

# Together API config
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-R1"

# Grab the Together API key
API_KEY = os.getenv("TOGETHER_API_KEY")
if not API_KEY:
    st.error("⚠️ Please set the TOGETHER_API_KEY environment variable in your .env file.")
    st.stop()

# Language display names
language_map = {
    "hi": "Hindi",
    "en": "English",
    "bn": "Bengali",
    "ta": "Tamil",
    "mr": "Marathi"
}

st.title("Scripted by Her: Vernacular Video Prototype")
st.write("Generate a short product video with localized script & voice using Together DeepSeek and gTTS.")

# --- INPUTS ---
uploaded_file = st.file_uploader("Upload product image", type=['jpg', 'jpeg', 'png'])
product_name = st.text_input("Product Name", "Handcrafted Brass Lamp")
features = st.text_area("Features (comma-separated)", "eco-friendly, long-lasting, intricate design")
context = st.text_input("Context (e.g. Diwali gifting)", "Diwali gifting")
language = st.selectbox("Language", list(language_map.keys()), format_func=lambda x: language_map[x])

if st.button("Generate Video"):
    if not uploaded_file:
        st.error("Please upload a product image.")
        st.stop()

    # 1) SCRIPT GENERATION via Together DeepSeek
    with st.spinner("Generating script..."):
        feature_list = [f.strip() for f in features.split(",") if f.strip()]
        prompt = (
            f"Write a 2-sentence sales pitch in {language_map[language]} for this product:\n"
            f"• Name: {product_name}\n"
            f"• Features: {', '.join(feature_list)}\n"
            f"Tone: friendly, festive. Context: {context}."
        )
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150
        }
        resp = requests.post(TOGETHER_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            st.error(f"DeepSeek API error: {resp.status_code} {resp.text}")
            st.stop()
        data = resp.json()
        script = data["choices"][0]["message"]["content"].strip()
    st.success("Script generated.")
    st.write(f"**Script:** {script}")

    # 2) TEXT-TO-SPEECH
    with st.spinner("Generating voice..."):
        tts = gTTS(text=script, lang=language)
        audio_tmp = NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(audio_tmp.name)
    st.success("Voice generated.")

    # 3) VIDEO ASSEMBLY
    with st.spinner("Assembling video..."):
        tmp_dir = mkdtemp()
        # save uploaded image
        img_path = os.path.join(tmp_dir, "product.png")
        with open(img_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # determine actual audio duration
        audio_clip = AudioFileClip(audio_tmp.name)
        duration = audio_clip.duration

        # build video clips
        img_clip = ImageClip(img_path).resize(width=1280).set_duration(duration)
        txt_clip = (
            TextClip(script, font="Amiri-Bold", fontsize=50, method="caption", align="South")
            .set_duration(duration)
            .set_position(("center", "bottom"))
        )
        video = CompositeVideoClip([img_clip, txt_clip]).set_audio(audio_clip)

        # write out
        video_path = os.path.join(tmp_dir, "product_video.mp4")
        video.write_videofile(
            video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            verbose=False,
            logger=None
        )
    st.success("Video generated!")

    # Display & download
    st.video(video_path)
    with open(video_path, "rb") as vf:
        st.download_button(
            label="Download Video",
            data=vf.read(),
            file_name=f"{product_name.replace(' ', '_')}.mp4",
            mime="video/mp4"
        )
