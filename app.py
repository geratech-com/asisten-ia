import streamlit as st
import os
import zipfile
import requests
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

# Fungsi tangguh untuk download file besar dari Google Drive tanpa gdown
def download_file_besar_drive(id_file, jalur_output):
    URL_BASE = "https://docs.google.com/uc?export=download"
    sesi = requests.Session()
    respon = sesi.get(URL_BASE, params={'id': id_file}, stream=True)
    
    # Periksa apakah Google memunculkan halaman konfirmasi virus scan
    token_konfirmasi = None
    for kunci, nilai in respon.cookies.items():
        if kunci.startswith('download_warning'):
            token_konfirmasi = nilai
            break
            
    if token_konfirmasi:
        params = {'id': id_file, 'confirm': token_konfirmasi}
        respon = sesi.get(URL_BASE, params=params, stream=True)
        
    with open(jalur_output, "wb") as f:
        for chunk in respon.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)

# 3. Fungsi Cerdas Memuat dan Mengunduh Database
@st.cache_resource
def muat_database():
    PATH_SIMPAN = './storage'
    
    if not os.path.exists(PATH_SIMPAN):
        os.makedirs(PATH_SIMPAN)

    FILE_UTAMA = f'{PATH_SIMPAN}/docstore.json'
    
    # Jika database belum ada di server Streamlit, lakukan download & extract
    if not os.path.exists(FILE_UTAMA):
        with st.spinner("Mengambil database 919 MB dari server pusat (Mohon tunggu 1-3 menit, jangan di-close)..."):
            
            # 🔍 LANGKAH WAJIB: Klik kanan 'database_ai.zip' di Drive, pilih Bagikan -> Ambil ID-nya dan tempel di bawah ini
            file_id = '1aLGhHcG9A2Nm4KAKQzUarIMBGk1St9lt'
            output_zip = 'database_ai.zip'
            
            try:
                # Unduh file raksasa bypass scan virus
                download_file_besar_drive(file_id, output_zip)
                
                # Ekstrak file zip ke folder './storage'
                with zipfile.ZipFile(output_zip, 'r') as zip_ref:
                    zip_ref.extractall('./storage')
                    
                # Hapus file zip mentah setelah diekstrak agar server hemat ruang
                if os.path.exists(output_zip):
                    os.remove(output_zip)
                    
            except Exception as e:
                st.error(f"❌ Gagal mengunduh atau mengekstrak database: {e}")
                return None

    # Antisipasi jika struktur zip membungkus folder di dalam folder (storage/storage/...)
    if not os.path.exists(FILE_UTAMA) and os.path.exists('./storage/storage/docstore.json'):
        PATH_SIMPAN = './storage/storage'

    # Proses membaca ingatan AI
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

# Menampilkan riwayat chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Kotak Tanya Jawab
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
