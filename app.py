import streamlit as st
import os
import gdown
import zipfile
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. Tampilan Halaman Web
st.set_page_config(page_title="JDIH Audit Agrinas", page_icon="🔍", layout="centered")

st.title("🔍 Asisten Pintar JDIH Audit Internal")
st.markdown("**PT Agrinas Pangan Nusantara - Strategi Audit 2026**")
st.markdown("---")

# 2. Menu Samping untuk Kunci Keamanan
with st.sidebar:
    st.header("⚙️ Pengaturan Sistem")
    api_key = st.text_input("Masukkan Google Gemini API Key:", type="password")
    st.info("💡 Masukkan kunci API Anda di sini agar aplikasi bisa berjalan.")

# 3. Fungsi Cerdas Memuat dan Mengunduh Database
@st.cache_resource
def muat_database():
    PATH_SIMPAN = './storage'
    FILE_UTAMA = f'{PATH_SIMPAN}/docstore.json'
    
    # PERBAIKAN: Kita cek apakah "isinya" (docstore.json) benar-benar ada.
    # Jika tidak ada, paksa download dari Google Drive!
    if not os.path.exists(FILE_UTAMA):
        with st.spinner("Mengambil database terbaru dari server pusat (Mohon tunggu 1-2 menit)..."):
            file_id = '1PdwjktYw1DV3Y45hPlQ9d_WIoC-1Djye'
            output = 'storage.zip'
            
            try:
                # Mengunduh file
                gdown.download(id=file_id, output=output, quiet=False)
                
                # Ekstrak file Zip
                with zipfile.ZipFile(output, 'r') as zip_ref:
                    zip_ref.extractall('.')
                    
            except Exception as e:
                st.error(f"❌ Gagal mengunduh database dari Google Drive: {e}")
                return None

    # PERBAIKAN: Antisipasi jika terekstrak menjadi folder ganda (storage/storage/...)
    if not os.path.exists(FILE_UTAMA) and os.path.exists('./storage/storage/docstore.json'):
        PATH_SIMPAN = './storage/storage'

    # Proses membaca ingatan AI
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=PATH_SIMPAN)
        index = load_index_from_storage(storage_context)
        return index
    except Exception as e:
        st.error(f"❌ Gagal memuat dokumen: {e}")
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
