import streamlit as st
import os
import zipfile
import requests
import re
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. Tampilan Halaman Web
st.set_page_config(page_title="Asisten Audit Agrinas", page_icon="🔍", layout="centered")

st.title("🔍 Asisten Audit Internal")
st.markdown("**PT Agrinas Pangan Nusantara - Asisten IA**")
st.markdown("---")

# 2. Menu Samping untuk Kunci Keamanan
with st.sidebar:
    st.header("⚙️ Pengaturan Sistem")
    api_key = st.text_input("Masukkan Google Gemini API Key:", type="password")
    st.info("💡 Masukkan kunci API Anda di sini agar aplikasi bisa berjalan.")

# =====================================================================
# SENJATA FINAL: PENGUNDUH CERDAS ANTI-BLOKIR (V2)
# =====================================================================
def unduh_paksa_drive(id_file, output_path):
    URL = "https://drive.google.com/uc?export=download"
    session = requests.Session()
    
    # LANGKAH 1: Ketuk pintu tanpa streaming untuk membedah halaman peringatan
    res_awal = session.get(URL, params={'id': id_file})
    
    token = None
    # Cari token izin dari Cookie
    for key, value in res_awal.cookies.items():
        if key.startswith('download_warning'):
            token = value
            break
            
    # Jika tidak ada di Cookie, bedah langsung isi HTML-nya
    if not token:
        cocok = re.search(r'confirm=([a-zA-Z0-9_-]+)', res_awal.text)
        if cocok:
            token = cocok.group(1)
            
    # LANGKAH 2: Masuk ambil file asli membawa token, nyalakan STREAMING
    if token:
        res_final = session.get(URL, params={'id': id_file, 'confirm': token}, stream=True)
    else:
        # Fallback cadangan
        res_final = session.get(URL, params={'id': id_file}, stream=True)
        
    # LANGKAH 3: Pengecekan Keamanan (Pastikan yang diunduh benar-benar ZIP)
    tipe_konten = res_final.headers.get('Content-Type', '')
    if 'text/html' in tipe_konten:
        raise Exception("Google Drive masih memblokir. Yang terunduh adalah halaman web peringatan.")
        
    # LANGKAH 4: Sedot file secara bertahap (1 MB per sedotan) agar RAM aman
    with open(output_path, "wb") as f:
        for chunk in res_final.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)

# 3. Fungsi Memuat Database
@st.cache_resource
def muat_database():
    PATH_SIMPAN = './storage'
    
    if not os.path.exists(PATH_SIMPAN):
        os.makedirs(PATH_SIMPAN)

    FILE_UTAMA = f'{PATH_SIMPAN}/docstore.json'
    
    if not os.path.exists(FILE_UTAMA):
        with st.spinner("Mengambil pangkalan data 919 MB dari Drive. Mohon tunggu 2-5 menit..."):
            
            output_zip = 'database_ai.zip'
            file_id = '1aLGhHcG9A2Nm4KAKQzUarIMBGk1St9lt'
            
            try:
                # Memanggil alat pengunduh cerdas kita
                unduh_paksa_drive(file_id, output_zip)
                
                # Ekstrak file zip
                with zipfile.ZipFile(output_zip, 'r') as zip_ref:
                    zip_ref.extractall('./storage')
                    
                # Hapus file zip mentah
                if os.path.exists(output_zip):
                    os.remove(output_zip)
                    
            except Exception as e:
                st.error(f"❌ Gagal menyedot data dari Google Drive: {e}")
                return None

    if not os.path.exists(FILE_UTAMA) and os.path.exists('./storage/storage/docstore.json'):
        PATH_SIMPAN = './storage/storage'

    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=PATH_SIMPAN)
        index = load_index_from_storage(storage_context)
        return index
    except Exception as e:
        st.error(f"❌ Gagal memuat index/dokumen: {e}")
        return None

# 4. Validasi Kunci
if not api_key:
    st.warning("⚠️ Silakan masukkan API Key di menu sebelah kiri.")
    st.stop()

# 5. Hidupkan Mesin AI
Settings.llm = GoogleGenAI(model="models/gemini-2.5-flash", api_key=api_key)

with st.spinner("⏳ Membangunkan ingatan AI..."):
    index = muat_database()

if index is None:
    st.stop()

if "chat_engine" not in st.session_state:
    st.session_state.chat_engine = index.as_chat_engine(
        system_prompt="Anda adalah Asisten Internal Audit PT Agrinas Pangan Nusantara. Tugas Anda adalah menjelaskan secara komprehensif dan profesional.",
        similarity_top_k=15
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ketik topik audit di sini..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Menganalisis ratusan dokumen..."):
            pertanyaan_super = f"""
            Tolong berikan analisis yang SANGAT PANJANG, LUAS, MENDETAIL, dan KOMPREHENSIF mengenai topik ini: "{prompt}".

            Saat menjawab, Anda WAJIB mematuhi instruksi berikut:
            1. Cari SEMUA aturan, pasal, atau kebijakan di seluruh dokumen.
            2. Jabarkan setiap poin secara eksplisit, jangan ada yang dipotong.
            3. Sebutkan dengan jelas nama dokumen atau nomor SK sumber data tersebut.
            4. Jika ada sebutan angka, nominal, atau persentase, tuliskan selengkapnya.
            5. Susun jawaban dalam paragraf yang rapi dan menarik.
            """
            try:
                response = st.session_state.chat_engine.chat(pertanyaan_super)
                st.markdown(response.response)
                st.session_state.messages.append({"role": "assistant", "content": response.response})
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan teknis: {e}")
