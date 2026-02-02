import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

st.set_page_config(
    page_title="Controle de Entregas - Obra",
    page_icon="🏗️",
    layout="wide"
)

DATA_FILE = "entregas_obra.json"
USERS_FILE = "usuarios.json"

# 🔥 PLANILHA FIXA (AUTOMÁTICO)
SHEET_URL = "https://docs.google.com/spreadsheets/d/17pK_8AgmQISuaLGdZD5FoiQzQBlPKOY6YV2Xh96RCqs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =====================================================
# MUNICÍPIOS
# =====================================================

MUNICIPIOS = [
    "São Vicente do Seridó",
    "Pedra Lavrada",
]

# =====================================================
# MATERIAIS
# =====================================================

MATERIAIS_PADRAO = [
    {"nome": "Tijolo", "quantidade_padrao": "1000 un"},
    {"nome": "Brita", "quantidade_padrao": "5 m³"},
    {"nome": "Areia", "quantidade_padrao": "5 m³"},
    {"nome": "Cimento", "quantidade_padrao": "50 sacos"},
]

# =====================================================
# USUÁRIOS
# =====================================================

USUARIOS_PADRAO = [
    {"username": "gutemberg", "nome": "Gutemberg Martins", "pin": "0000", "admin": True},
]

# =====================================================
# GOOGLE SHEETS
# =====================================================

def conectar_google_sheets():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def sincronizar_sheets(dados, client):
    sheet = client.open_by_url(SHEET_URL)

    rows = []
    rows.append(["Município", "Casa", "Material", "Quantidade", "Status", "Data Entrega", "Confirmado Por"])

    for municipio, casas in dados["municipios"].items():
        for casa, materiais in casas.items():
            for item in materiais:
                rows.append([
                    municipio,
                    casa,
                    item["material"],
                    item.get("quantidade", ""),
                    "Entregue" if item["entregue"] else "Pendente",
                    item.get("data_entrega", ""),
                    item.get("confirmado_por", "")
                ])

    try:
        ws = sheet.worksheet("Controle")
    except:
        ws = sheet.add_worksheet(title="Controle", rows=1000, cols=10)

    ws.clear()
    ws.update("A1", rows)


def carregar_sheets(client):
    sheet = client.open_by_url(SHEET_URL)

    try:
        ws = sheet.worksheet("Controle")
    except:
        return {"municipios": {}}

    data = ws.get_all_values()

    if len(data) <= 1:
        return {"municipios": {}}

    dados = {"municipios": {}}

    for row in data[1:]:
        municipio, casa, material, quantidade, status, data_entrega, confirmado = row

        dados["municipios"].setdefault(municipio, {})
        dados["municipios"][municipio].setdefault(casa, [])

        dados["municipios"][municipio][casa].append({
            "material": material,
            "quantidade": quantidade,
            "entregue": status == "Entregue",
            "data_entrega": data_entrega,
            "confirmado_por": confirmado
        })

    return dados


# =====================================================
# DADOS (SALVAMENTO AUTOMÁTICO)
# =====================================================

def carregar_dados():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"municipios": {}}


def salvar_dados(dados):
    # salva local
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    # 🔥 salva automático no Sheets
    client = st.session_state.get("gs_client")
    if client:
        sincronizar_sheets(dados, client)


def inicializar_materiais():
    return [
        {
            "material": m["nome"],
            "quantidade": m["quantidade_padrao"],
            "entregue": False,
            "data_entrega": None,
            "confirmado_por": None
        }
        for m in MATERIAIS_PADRAO
    ]


# =====================================================
# LOGIN
# =====================================================

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def tela_login():
    st.title("Login")

    usuarios = {
        u["username"]: {
            "nome": u["nome"],
            "pin": hash_pin(u["pin"]),
            "admin": u["admin"]
        }
        for u in USUARIOS_PADRAO
    }

    user = st.selectbox("Usuário", usuarios.keys())
    pin = st.text_input("PIN", type="password")

    if st.button("Entrar"):
        if hash_pin(pin) == usuarios[user]["pin"]:
            st.session_state.usuario = user
            st.rerun()
        else:
            st.error("PIN errado")


# =====================================================
# INICIALIZAÇÃO AUTOMÁTICA DO SHEETS
# =====================================================

if "gs_client" not in st.session_state:
    st.session_state.gs_client = conectar_google_sheets()

if "dados" not in st.session_state:
    st.session_state.dados = carregar_sheets(st.session_state.gs_client)

if "usuario" not in st.session_state:
    st.session_state.usuario = None


# =====================================================
# APP
# =====================================================

if not st.session_state.usuario:
    tela_login()
    st.stop()


st.title("🏗️ Controle de Entregas")

dados = st.session_state.dados

municipio = st.selectbox("Município", MUNICIPIOS)
casa = st.text_input("Casa")

if st.button("Adicionar Casa"):
    dados["municipios"].setdefault(municipio, {})
    dados["municipios"][municipio][casa] = inicializar_materiais()
    salvar_dados(dados)
    st.rerun()


for mun, casas in dados["municipios"].items():
    st.header(mun)

    for nome_casa, materiais in casas.items():
        st.subheader(nome_casa)

        for item in materiais:
            if not item["entregue"]:
                if st.button(f"Entregar {item['material']} ({nome_casa})"):
                    item["entregue"] = True
                    item["data_entrega"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    item["confirmado_por"] = st.session_state.usuario
                    salvar_dados(dados)
                    st.rerun()
