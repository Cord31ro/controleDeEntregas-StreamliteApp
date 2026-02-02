import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import time

# =====================================================
# CONFIGURAÇÕES
# =====================================================

st.set_page_config(
    page_title="Controle de Entregas - Obra",
    page_icon="🏗️",
    layout="wide"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/17pK_8AgmQISuaLGdZD5FoiQzQBlPKOY6YV2Xh96RCqs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MUNICIPIOS = ["São Vicente do Seridó", "Pedra Lavrada"]
MATERIAIS_PADRAO = ["Tijolo (1000 un)", "Brita (5 m³)", "Areia (5 m³)", "Cimento (50 sacos)", "Cal (20 sacos)", "Ferro 8mm (50 barras)", "Ferro 10mm (50 barras)"]

USUARIOS = {
    "gutemberg": {"nome": "Gutemberg Martins", "pin": "0000", "admin": True},
    "severino": {"nome": "Severino Cordeiro", "pin": "0101", "admin": False},
    "virgilho": {"nome": "Virgilho Cordeiro", "pin": "0209", "admin": False},
    "gutemberg_filho": {"nome": "Gutemberg Filho", "pin": "2004", "admin": False},
}

# =====================================================
# GOOGLE SHEETS
# =====================================================

@st.cache_resource
def conectar_google_sheets():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(credentials)
        st.success(f"✅ Conectado! Email: {creds_dict['client_email']}")
        return client
    except Exception as e:
        st.error(f"❌ Erro conexão: {e}")
        return None

def adicionar_casa(client, municipio, casa, usuario):
    try:
        st.info(f"🔄 Abrindo planilha...")
        sheet = client.open_by_url(SHEET_URL)
        
        st.info(f"🔄 Acessando aba Casas...")
        try:
            ws_casas = sheet.worksheet("Casas")
        except:
            st.warning("⚠️ Criando aba Casas...")
            ws_casas = sheet.add_worksheet(title="Casas", rows=1000, cols=10)
            ws_casas.update('A1', [["Município", "Casa", "Data Cadastro", "Cadastrado Por"]])
        
        st.info(f"🔄 Acessando aba Entregas...")
        try:
            ws_entregas = sheet.worksheet("Entregas")
        except:
            st.warning("⚠️ Criando aba Entregas...")
            ws_entregas = sheet.add_worksheet(title="Entregas", rows=5000, cols=10)
            ws_entregas.update('A1', [["Município", "Casa", "Material", "Entregue", "Data Entrega", "Confirmado Por"]])
        
        st.info(f"🔄 Verificando duplicatas...")
        todas_casas = ws_casas.get_all_values()
        for linha in todas_casas[1:]:
            if len(linha) >= 2:
                if linha[0].strip().lower() == municipio.strip().lower() and linha[1].strip().lower() == casa.strip().lower():
                    return False, "Casa já existe!"
        
        st.info(f"🔄 Adicionando casa na planilha...")
        data_cadastro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws_casas.append_row([municipio, casa, data_cadastro, usuario])
        st.success(f"✅ Casa adicionada na linha!")
        
        time.sleep(1)
        
        st.info(f"🔄 Adicionando {len(MATERIAIS_PADRAO)} materiais...")
        for i, material in enumerate(MATERIAIS_PADRAO, 1):
            ws_entregas.append_row([municipio, casa, material, "Não", "", ""])
            st.write(f"   ✓ {i}/{len(MATERIAIS_PADRAO)}: {material}")
        
        st.success(f"✅ TUDO SALVO NA PLANILHA!")
        return True, f"Casa '{casa}' cadastrada com sucesso!"
        
    except Exception as e:
        st.error(f"❌ ERRO: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False, str(e)

# =====================================================
# AUTH
# =====================================================

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def verificar_login(username, pin):
    if username in USUARIOS:
        return hash_pin(USUARIOS[username]["pin"]) == hash_pin(pin)
    return False

# =====================================================
# INTERFACE
# =====================================================

def tela_login():
    st.title("🔐 Login")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usernames = list(USUARIOS.keys())
        nomes = [USUARIOS[u]["nome"] for u in usernames]
        opcao = st.selectbox("Usuário", nomes)
        username = usernames[nomes.index(opcao)]
        pin = st.text_input("PIN", type="password", max_chars=4)
        
        if st.button("Entrar", use_container_width=True):
            if verificar_login(username, pin):
                st.session_state.usuario = username
                st.session_state.nome_usuario = USUARIOS[username]["nome"]
                st.rerun()
            else:
                st.error("❌ PIN incorreto!")

def tela_principal():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏗️ Controle de Entregas")
    with col2:
        st.write(f"**{st.session_state.nome_usuario}**")
        if st.button("Sair"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown("---")
    
    client = st.session_state.get("gs_client")
    if not client:
        st.error("❌ Cliente não conectado")
        return
    
    st.subheader("➕ Adicionar Casa (COM DEBUG)")
    
    col1, col2 = st.columns(2)
    with col1:
        municipio_novo = st.selectbox("Município", MUNICIPIOS)
    with col2:
        casa_nova = st.text_input("Nome da Casa", placeholder="Ex: Casa 01")
    
    if st.button("➕ ADICIONAR E VER LOGS", type="primary"):
        if not casa_nova or not casa_nova.strip():
            st.error("❌ Digite o nome da casa!")
        else:
            with st.spinner("Processando..."):
                sucesso, msg = adicionar_casa(client, municipio_novo, casa_nova.strip(), st.session_state.nome_usuario)
                
                if sucesso:
                    st.balloons()
                    st.info("Aguarde 3 segundos e verifique a planilha...")
                    time.sleep(3)
                    st.info("🔗 Abra: https://docs.google.com/spreadsheets/d/17pK_8AgmQISuaLGdZD5FoiQzQBlPKOY6YV2Xh96RCqs")

def main():
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "gs_client" not in st.session_state:
        st.session_state.gs_client = conectar_google_sheets()
    
    if st.session_state.usuario is None:
        tela_login()
    else:
        tela_principal()

if __name__ == "__main__":
    main()