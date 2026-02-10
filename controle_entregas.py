import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import time

# Timezone de Brasília (UTC-3)
TZ_BRASILIA = timezone(timedelta(hours=-3))

# =====================================================
# CONFIGURAÇÕES
# =====================================================

st.set_page_config(
    page_title="Controle de Entregas - Obra",
    page_icon="🏗️",
    layout="wide"
)

# URL da planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/17pK_8AgmQISuaLGdZD5FoiQzQBlPKOY6YV2Xh96RCqs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =====================================================
# MATERIAIS COM QUANTIDADE
# =====================================================

MATERIAIS_COM_QUANTIDADE = {
    "Cimento composto CP II": "sacos",
    "Pedra brita 19": "m³",
    "Areia média": "m³"
}

# =====================================================
# MUNICÍPIOS E MATERIAIS
# =====================================================

MUNICIPIOS = [
    "São Vicente do Seridó",
    "Pedra Lavrada",
]

MATERIAIS_PADRAO = [
    # 🧱 ALVENARIA
    "Pedra brita 19",
    "Pedra rocha fundação",
    "Areia média",
    "Cimento composto CP II",
    "Aço vergalhão 10mm",
    "Aço vergalhão 5,2mm",
    "Arame recozido",
    "Tijolo cerâmico",
    "Trilho para laje",
    "Tábuas 0,30 x 3m",
    "Tábuas 0,10 x 3m",
    "Lajotas",
    
    # 🏠 TELHADO
    "Telha cerâmica",
    "Linha 3/5 – 7,5m",
    "Linha 3/5 – 4m",
    "Linha 3/5 – 5m",
    "Linha 3/5 – 2m",
    "Barrote de 3m",
    "Barrote 4,5m",
    "Caibros 5,5m",
    "Ripas",
    "Canaletas grandes",
    "Canaletas pequenas",
    "Sapata",
    
    # 🪟 ESQUADRIAS / ACABAMENTO
    "Janela 1x1,20",
    "Janela 1,00x1",
    "Janela 50x50",
    "Porta semi-oca",
    "Porta almofadada",
    "Coluna 5/16 – 3m",
    "Cerâmica piso",
    "Cerâmica parede",
    "Argamassa 15kg",
    "Rejunte",
    "Forra de porta (pct)",
    "Dobradiças p/ janela",
    "Dobradiças p/ portas",
    "Ferrolho redondo",
    "Parafusos p/ janela, porta e ferragem",
    "Pivoltante",
    "Caixa d'água 500L",
    "Caixa d'água 1000L",
    
    # 🚿 BANHEIRO / PINTURA
    "Kit banheiro",
    "Fechadura externa",
    "Fechadura interna",
    "Fechadura banheiro",
    "Lixa 120",
    "Verniz 3L",
    "Tinta esmalte sintético 15L",
    "Selador 18L",
    "Cal para pintura",
    "Rolo para pintura 23cm",
    "Rolo para pintura 9cm",
    "Brocha para pintura",
    "Pincel 1 1/2 polegadas",
    
    # ⚡ ELÉTRICA
    "Quadro distribuição 6 disjuntores",
    "Quadro de luz completo",
    "Pontalete energia",
    "Eletroduto PVC corrugado",
    "Lâmpada",
    "Interruptor de 2 sessões",
    "Interruptor de 1 sessão",
    "Tomadas 10A",
    "Tomadas 20A",
    "Fita isolante",
    "Fio 4mm 750V",
    "Fio 2,5mm",
    "Fio 1,5mm",
    "Disjuntor 16 amperes",
    "Disjuntor 10 amperes",
    "Disjuntor 25 amperes",
    "Disjuntor 32 amperes",
    "Disjuntor 40 amperes DR",
    "Bocal de lâmpadas",
    "Plafon",
    "Cano eletroduto",
    "Capacete para eletrodutos",
    "Haste para aterramento",
    "Cone para aterramento",
    "Curva eletroduto 3/4",
    "Tomada da internet",
    "Tomada para TV",
    "Caixa PVC 4x2",
    "Fixa fio (pct)",
    "Conector para haste",
    
    # 🚰 HIDRÁULICA
    "Joelho PVC 25mm",
    "Joelho redução 25x1/2\"",
    "Tê 25mm",
    "Registro gaveta cromado",
    "Registro pressão",
    "Adaptador curto SR 25mm x 3/4\"",
    "Joelho 40mm 90°",
    "Joelho 45° 50mm esgoto série normal",
    "Joelho 90° 50mm esgoto série normal",
    "Luva PVC SR 25mm x 3/4\" rosca externa",
    "Tê 100x50mm",
    "Tubo PVC 25mm 6m",
    "Tubo PVC esgoto 100mm 6m",
    "Tubo PVC esgoto 75mm 6m",
    "Tubo PVC esgoto 50mm 6m",
    "Tubo PVC esgoto 40mm 6m",
    "Tubo PVC água 40mm 1,5m",
    "Ralo sifonado",
    "Tê 40mm",
    "Tê 50mm",
    "Y esgoto 100x50mm",
    "Joelho esgoto 50mm 45°",
    "Joelho esgoto 50mm",
    "Joelho esgoto 40mm",
    "Joelho esgoto 40mm 45°",
    "Joelho esgoto 100mm",
    "Cola de cano 175g",
    "Sifão sifonado",
    "Torneira p/ lavatório",
    "Torneira p/ lavanderia",
    "Torneira p/ pia de cozinha",
    "Calha de PVC",
    "Terminal PVC",
    "Tampa PVC",
    "Emenda PVC para bica",
    "Suporte para bica",
    "Parafusos para suporte da bica",
    "Vedanel",
    "Flange 40mm",
    "Flange 25mm",
    "Válvula para lavatório",
    "Válvula para pia inox",
    "Chicote flexível 40cm",
    "Tanque p/ lavar roupa",
    "Cantoneira 40cm",
    "Parafuso com bucha 10mm",
    "Parafuso para tanque",
    "Pia de banheiro",
    "Arame da cisterna",
    "Vaso acoplado",
    "Veda rosca",
    
    # 🚿 ACESSIBILIDADE
    "Parafuso p/ vaso sanitário",
    "Chuveiro com cano",
    "Barra de apoio 70cm",
    "Cadeira para banho",
]

# =====================================================
# USUÁRIOS
# =====================================================

USUARIOS = {
    "gutemberg": {
        "nome": "Gutemberg Martins",
        "pin": "0000",
        "admin": True
    },
    "severino": {
        "nome": "Severino Cordeiro",
        "pin": "0101",
        "admin": False
    },
    "virgilho": {
        "nome": "Virgilho Cordeiro",
        "pin": "0209",
        "admin": False
    },
    "gutemberg_filho": {
        "nome": "Gutemberg Filho",
        "pin": "2004",
        "admin": False
    },
}

# =====================================================
# FUNÇÕES OTIMIZADAS DO GOOGLE SHEETS
# =====================================================

@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets - CACHE PERMANENTE"""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None


def inicializar_planilha(client):
    """Cria as abas necessárias se não existirem - OTIMIZADO"""
    if not client:
        return None
    
    # Usa session_state para evitar verificações repetidas
    if "planilha_inicializada" in st.session_state:
        return st.session_state.planilha_inicializada
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        try:
            ws_casas = sheet.worksheet("Casas")
        except:
            ws_casas = sheet.add_worksheet(title="Casas", rows=1000, cols=10)
            ws_casas.update('A1', [["Município", "Casa", "Data Cadastro", "Cadastrado Por"]])
            time.sleep(1)
        
        try:
            ws_entregas = sheet.worksheet("Entregas")
            
            # Verifica se a coluna "Quantidade" existe
            header = ws_entregas.row_values(1)
            if len(header) < 6 or header[3] != "Quantidade":
                # Adiciona a coluna "Quantidade" na posição 4 (índice 3)
                ws_entregas.insert_cols([[]], col=4)
                time.sleep(1)
                ws_entregas.update('A1', [["Município", "Casa", "Material", "Quantidade", "Data Entrega", "Confirmado Por"]])
                time.sleep(1)
                st.info("✅ Coluna 'Quantidade' adicionada à planilha!")
        except:
            ws_entregas = sheet.add_worksheet(title="Entregas", rows=10000, cols=10)
            ws_entregas.update('A1', [["Município", "Casa", "Material", "Quantidade", "Data Entrega", "Confirmado Por"]])
            time.sleep(1)
        
        st.session_state.planilha_inicializada = sheet
        return sheet
    except Exception as e:
        st.error(f"Erro ao inicializar planilha: {e}")
        return None


@st.cache_data(ttl=180)  # ⚡ CACHE POR 3 MINUTOS
def carregar_todos_dados_cached(_client):
    """
    OTIMIZAÇÃO 1: Cache de 3 minutos
    OTIMIZAÇÃO 2: Batch request (carrega tudo de uma vez)
    """
    if not _client:
        return None, None
    
    try:
        sheet = _client.open_by_url(SHEET_URL)
        
        # 🚀 BATCH REQUEST - Uma chamada só!
        result = sheet.values_batch_get(['Casas!A:Z', 'Entregas!A:Z'])
        
        dados_casas = result['valueRanges'][0].get('values', [])
        dados_entregas = result['valueRanges'][1].get('values', [])
        
        # Padroniza para 6 colunas (compatibilidade com formato antigo de 5 colunas)
        dados_entregas_padronizados = []
        for linha in dados_entregas:
            if len(linha) == 5:
                # Formato antigo: adiciona coluna vazia para quantidade
                linha.insert(3, "")
            while len(linha) < 6:
                linha.append("")
            dados_entregas_padronizados.append(linha)
        
        return dados_casas, dados_entregas_padronizados
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None


@st.cache_data(ttl=180)  # ⚡ CACHE POR 3 MINUTOS
def processar_casas_cached(dados_casas):
    """OTIMIZADO: Cache no processamento de casas"""
    if not dados_casas or len(dados_casas) <= 1:
        return {}
    
    casas_por_municipio = {}
    for linha in dados_casas[1:]:
        if len(linha) >= 2:
            municipio = linha[0]
            casa = linha[1]
            
            if municipio not in casas_por_municipio:
                casas_por_municipio[municipio] = []
            
            if casa not in casas_por_municipio[municipio]:
                casas_por_municipio[municipio].append(casa)
    
    return casas_por_municipio


@st.cache_data(ttl=180)  # ⚡ CACHE POR 3 MINUTOS
def processar_entregas_cached(dados_entregas_tuple, municipio, casa):
    """
    OTIMIZAÇÃO 3: Lazy Loading - Processa apenas a casa selecionada
    OTIMIZAÇÃO 4: Cache por município/casa
    """
    # Converte tuple de volta para list (necessário para cache)
    dados_entregas = [list(linha) for linha in dados_entregas_tuple]
    
    # Carrega os materiais já entregues da planilha
    entregas_historico = {}
    
    if dados_entregas and len(dados_entregas) > 1:
        for linha in dados_entregas[1:]:
            while len(linha) < 6:
                linha.append("")
            
            # 🎯 LAZY LOADING: Filtra apenas esta casa
            if linha[0] == municipio and linha[1] == casa and linha[2] != "":
                material = linha[2]
                quantidade = linha[3]
                data_entrega = linha[4]
                confirmado_por = linha[5]
                
                if material not in entregas_historico:
                    entregas_historico[material] = []
                
                entregas_historico[material].append({
                    "quantidade": quantidade,
                    "data_entrega": data_entrega,
                    "confirmado_por": confirmado_por
                })
    
    # Cria lista completa combinando lista padrão com dados da planilha
    entregas = []
    for material in MATERIAIS_PADRAO:
        if material in entregas_historico:
            # Calcula quantidade total se for material quantitativo
            if material in MATERIAIS_COM_QUANTIDADE:
                total_qtd = 0
                for entrega in entregas_historico[material]:
                    try:
                        qtd = float(entrega["quantidade"]) if entrega["quantidade"] else 0
                        total_qtd += qtd
                    except:
                        pass
                
                entregas.append({
                    "material": material,
                    "entregue": True,
                    "historico": entregas_historico[material],
                    "quantidade_total": total_qtd
                })
            else:
                # Material normal (sem quantidade)
                entregas.append({
                    "material": material,
                    "entregue": True,
                    "historico": entregas_historico[material],
                    "quantidade_total": None
                })
        else:
            entregas.append({
                "material": material,
                "entregue": False,
                "historico": [],
                "quantidade_total": None
            })
    
    return entregas


def adicionar_casa(client, municipio, casa, usuario):
    """
    Só adiciona a casa, NÃO adiciona materiais
    OTIMIZADO: Limpa cache após modificação
    """
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_casas = sheet.worksheet("Casas")
        
        # Verifica duplicata
        todas_casas = ws_casas.get_all_values()
        if len(todas_casas) > 1:
            for linha in todas_casas[1:]:
                if len(linha) >= 2:
                    if linha[0].strip().lower() == municipio.strip().lower() and linha[1].strip().lower() == casa.strip().lower():
                        return False, "Casa já cadastrada neste município!"
        
        # Adiciona APENAS a casa
        data_cadastro = datetime.now(TZ_BRASILIA).strftime("%d/%m/%Y %H:%M:%S")
        ws_casas.append_row([municipio, casa, data_cadastro, usuario])
        
        # 🔄 LIMPA CACHE após modificação
        st.cache_data.clear()
        
        return True, f"✅ Casa '{casa}' cadastrada com sucesso!"
    except Exception as e:
        import traceback
        erro_completo = traceback.format_exc()
        st.error(f"❌ ERRO: {erro_completo}")
        return False, f"Erro: {str(e)}"


def marcar_entrega(client, municipio, casa, material, usuario, quantidade=None):
    """
    Adiciona uma nova linha na planilha quando marca como entregue
    OTIMIZADO: Limpa cache após modificação
    """
    if not client:
        return False, "Cliente do Google Sheets não inicializado"
        
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_entregas = sheet.worksheet("Entregas")
        
        data_entrega = datetime.now(TZ_BRASILIA).strftime("%d/%m/%Y %H:%M:%S")
        
        # Formata quantidade para string (vazio se None)
        qtd_str = str(quantidade) if quantidade is not None else ""
        
        # Adiciona nova linha na planilha
        ws_entregas.append_row([municipio, casa, material, qtd_str, data_entrega, usuario])
        
        # 🔄 LIMPA CACHE após modificação
        st.cache_data.clear()
        
        return True, "Entrega confirmada!"
    except Exception as e:
        return False, f"Erro ao marcar entrega: {e}"


# =====================================================
# FUNÇÕES DE AUTENTICAÇÃO
# =====================================================

def hash_pin(pin):
    """Hash simples do PIN"""
    return hashlib.sha256(pin.encode()).hexdigest()


def verificar_login(username, pin):
    """Verifica se o login é válido"""
    if username in USUARIOS:
        pin_hash_correto = hash_pin(USUARIOS[username]["pin"])
        pin_hash_digitado = hash_pin(pin)
        return pin_hash_correto == pin_hash_digitado
    return False


# =====================================================
# INTERFACE - LOGIN
# =====================================================

def tela_login():
    """Tela de login"""
    st.title("🔐 Login - Controle de Entregas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        usernames = list(USUARIOS.keys())
        nomes = [USUARIOS[u]["nome"] for u in usernames]
        
        opcao = st.selectbox("Selecione o usuário", nomes)
        username = usernames[nomes.index(opcao)]
        
        pin = st.text_input("Digite seu PIN", type="password", max_chars=4)
        
        if st.button("Entrar", use_container_width=True):
            if verificar_login(username, pin):
                st.session_state.usuario = username
                st.session_state.nome_usuario = USUARIOS[username]["nome"]
                st.session_state.is_admin = USUARIOS[username]["admin"]
                st.success(f"Bem-vindo, {USUARIOS[username]['nome']}!")
                st.rerun()
            else:
                st.error("❌ PIN incorreto!")
        
        st.markdown("---")


# =====================================================
# INTERFACE - PRINCIPAL (OTIMIZADA)
# =====================================================

def tela_principal():
    """Tela principal do sistema - VERSÃO OTIMIZADA"""
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏗️ Controle de Entregas de Material")
    with col2:
        st.write(f"**Usuário:** {st.session_state.nome_usuario}")
        if st.button("Sair"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown("---")
    
    client = st.session_state.get("gs_client")
    
    if not client:
        st.error("❌ Erro ao conectar com Google Sheets.")
        st.info("👉 Verifique as credenciais em Settings → Secrets")
        return
    
    sheet_result = inicializar_planilha(client)
    if not sheet_result:
        st.error("❌ Erro ao acessar a planilha.")
        return
    
    # 🚀 CARREGAMENTO OTIMIZADO COM CACHE
    with st.spinner("⚡ Carregando dados (cache: 3 min)..."):
        dados_casas, dados_entregas = carregar_todos_dados_cached(client)
    
    if dados_casas is None or dados_entregas is None:
        st.error("❌ Erro ao carregar dados da planilha.")
        return
    
    # 🧠 SESSION STATE: Armazena dados processados
    if 'casas_processadas' not in st.session_state or st.session_state.get('ultima_atualizacao', 0) < time.time() - 180:
        casas_por_municipio = processar_casas_cached(tuple(map(tuple, dados_casas)))
        st.session_state.casas_processadas = casas_por_municipio
        st.session_state.ultima_atualizacao = time.time()
    else:
        casas_por_municipio = st.session_state.casas_processadas
    
    # Botão para forçar recarga manual
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("🔄 Recarregar", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            if 'casas_processadas' in st.session_state:
                del st.session_state.casas_processadas
            st.rerun()
    
    with col_btn2:
        # Indicador de cache
        tempo_cache = int(time.time() - st.session_state.get('ultima_atualizacao', time.time()))
        st.caption(f"⏱️ Cache: {tempo_cache}s")
    
    tab1, tab2, tab3 = st.tabs(["📋 Controle de Entregas", "🏠 Adicionar Casa", "📊 Relatório"])
    
    # ===== TAB 1: CONTROLE DE ENTREGAS =====
    with tab1:
        st.subheader("Controle de Entregas")
        
        if not casas_por_municipio:
            st.info("Nenhuma casa cadastrada ainda. Adicione casas na aba 'Adicionar Casa'.")
        else:
            municipio_selecionado = st.selectbox("Selecione o Município", MUNICIPIOS)
            
            if municipio_selecionado in casas_por_municipio:
                casas = casas_por_municipio[municipio_selecionado]
                
                for casa in casas:
                    # 🎯 LAZY LOADING: Processa apenas quando necessário
                    dados_entregas_tuple = tuple(map(tuple, dados_entregas))
                    entregas = processar_entregas_cached(dados_entregas_tuple, municipio_selecionado, casa)
                    
                    total = len(entregas)
                    entregues = sum(1 for e in entregas if e["entregue"])
                    
                    chave_expander = f"expander_{municipio_selecionado}_{casa}"
                    expanded_default = st.session_state.get(chave_expander, False)
                    
                    titulo_expander = f"🏠 {casa}  |  ✅ {entregues}/{total} entregues"
                    
                    with st.expander(titulo_expander, expanded=expanded_default):
                        st.session_state[chave_expander] = True
                        
                        # Cabeçalho
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 2.5])
                        col1.write("**Material**")
                        col2.write("**Status**")
                        col3.write("**Quantidade**")
                        col4.write("**Última Entrega**")
                        st.markdown("---")
                        
                        for item in entregas:
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 2.5])
                            
                            material = item["material"]
                            tem_quantidade = material in MATERIAIS_COM_QUANTIDADE
                            
                            with col1:
                                st.write(material)
                            
                            with col2:
                                if item["entregue"]:
                                    # Material já entregue
                                    if tem_quantidade:
                                        # Permite adicionar mais quantidade
                                        btn_key = f"btn_add_{municipio_selecionado}_{casa}_{material}"
                                        if st.button("➕ Adicionar", key=btn_key, type="secondary", use_container_width=True):
                                            # Abre modal para adicionar quantidade
                                            st.session_state[f"modal_{municipio_selecionado}_{casa}_{material}"] = True
                                            st.session_state[chave_expander] = True
                                    else:
                                        # Material normal - não pode modificar
                                        st.button("✅ Entregue", key=f"btn_{municipio_selecionado}_{casa}_{material}", 
                                                type="primary", use_container_width=True, disabled=True)
                                else:
                                    # Material pendente
                                    if tem_quantidade:
                                        # Abre modal para primeira entrega
                                        btn_key = f"btn_{municipio_selecionado}_{casa}_{material}"
                                        if st.button("📦 Registrar", key=btn_key, type="secondary", use_container_width=True):
                                            st.session_state[f"modal_{municipio_selecionado}_{casa}_{material}"] = True
                                            st.session_state[chave_expander] = True
                                    else:
                                        # Material normal - marca como entregue
                                        btn_key = f"btn_{municipio_selecionado}_{casa}_{material}"
                                        clicked = st.button("❌ Pendente", key=btn_key, type="secondary", use_container_width=True)
                                        if clicked:
                                            st.session_state[chave_expander] = True
                                            sucesso, msg = marcar_entrega(client, municipio_selecionado, casa, material, 
                                                                         st.session_state.nome_usuario)
                                            if sucesso:
                                                st.success("✅ Entrega confirmada!")
                                                time.sleep(0.5)
                                                st.rerun()
                                            else:
                                                st.error(msg)
                            
                            with col3:
                                if tem_quantidade and item["entregue"]:
                                    unidade = MATERIAIS_COM_QUANTIDADE[material]
                                    qtd_total = item["quantidade_total"]
                                    st.write(f"**{qtd_total:.1f}** {unidade}")
                                else:
                                    st.write("—")
                            
                            with col4:
                                if item["entregue"] and item["historico"]:
                                    ultima = item["historico"][-1]
                                    if tem_quantidade:
                                        unidade = MATERIAIS_COM_QUANTIDADE[material]
                                        qtd = ultima["quantidade"]
                                        st.write(f"{qtd} {unidade} • {ultima['data_entrega'][:10]}")
                                    else:
                                        st.write(f"📅 {ultima['data_entrega'][:10]}")
                                else:
                                    st.write("—")
                            
                            # MODAL para registrar quantidade
                            modal_key = f"modal_{municipio_selecionado}_{casa}_{material}"
                            if st.session_state.get(modal_key, False):
                                with st.container():
                                    st.markdown("---")
                                    unidade = MATERIAIS_COM_QUANTIDADE[material]
                                    
                                    col_a, col_b, col_c = st.columns([1, 2, 1])
                                    with col_b:
                                        st.write(f"**{material}**")
                                        
                                        quantidade_input = st.number_input(
                                            f"Quantidade ({unidade})",
                                            min_value=0.0,
                                            step=0.5 if unidade == "m³" else 1.0,
                                            key=f"input_{municipio_selecionado}_{casa}_{material}"
                                        )
                                        
                                        col_x, col_y = st.columns(2)
                                        
                                        with col_x:
                                            if st.button("✅ Confirmar", key=f"confirmar_{municipio_selecionado}_{casa}_{material}", 
                                                       use_container_width=True, type="primary"):
                                                if quantidade_input > 0:
                                                    sucesso, msg = marcar_entrega(
                                                        client, municipio_selecionado, casa, material,
                                                        st.session_state.nome_usuario, quantidade_input
                                                    )
                                                    if sucesso:
                                                        del st.session_state[modal_key]
                                                        st.success("✅ Quantidade registrada!")
                                                        time.sleep(0.5)
                                                        st.rerun()
                                                    else:
                                                        st.error(msg)
                                                else:
                                                    st.warning("⚠️ Quantidade deve ser maior que zero!")
                                        
                                        with col_y:
                                            if st.button("❌ Cancelar", key=f"cancelar_{municipio_selecionado}_{casa}_{material}",
                                                       use_container_width=True):
                                                del st.session_state[modal_key]
                                                st.rerun()
                                    
                                    st.markdown("---")
                        
                        # Estatísticas
                        pendentes = total - entregues
                        st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total", total)
                        col2.metric("Entregues", entregues)
                        col3.metric("Pendentes", pendentes)
            else:
                st.info(f"Nenhuma casa cadastrada em {municipio_selecionado}")
    
    # ===== TAB 2: ADICIONAR CASA =====
    with tab2:
        st.subheader("➕ Adicionar Nova Casa")
        
        st.info(f"💡 Casa será criada instantaneamente! Os {len(MATERIAIS_PADRAO)} materiais aparecem automaticamente para controle.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            municipio_novo = st.selectbox("📍 Município", MUNICIPIOS, key="municipio_novo")
        
        with col2:
            casa_nova = st.text_input("🏠 Nome/Número da Casa", placeholder="Ex: Casa 01, Rua A nº 123")
        
        st.markdown("---")
        
        if st.button("➕ Adicionar Casa", use_container_width=True, type="primary"):
            if not casa_nova or not casa_nova.strip():
                st.error("❌ Por favor, informe o nome da casa!")
            else:
                with st.spinner("Adicionando casa..."):
                    sucesso, msg = adicionar_casa(
                        client, 
                        municipio_novo, 
                        casa_nova.strip(), 
                        st.session_state.nome_usuario
                    )
                    
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
        
        st.markdown("---")
        st.subheader("📋 Casas Cadastradas")
        
        if casas_por_municipio:
            for mun in MUNICIPIOS:
                if mun in casas_por_municipio and casas_por_municipio[mun]:
                    with st.expander(f"📍 {mun} ({len(casas_por_municipio[mun])} casas)"):
                        for idx, casa_nome in enumerate(casas_por_municipio[mun], 1):
                            st.write(f"{idx}. {casa_nome}")
        else:
            st.info("Nenhuma casa cadastrada ainda.")
    
    # ===== TAB 3: RELATÓRIO =====
    with tab3:
        st.subheader("📊 Relatório de Entregas")
        
        if not casas_por_municipio:
            st.info("Nenhum dado disponível.")
            return
        
        # 🚀 OTIMIZAÇÃO: Processa relatório com cache
        dados_relatorio = []
        dados_entregas_tuple = tuple(map(tuple, dados_entregas))
        
        for municipio in MUNICIPIOS:
            if municipio in casas_por_municipio:
                for casa in casas_por_municipio[municipio]:
                    entregas = processar_entregas_cached(dados_entregas_tuple, municipio, casa)
                    
                    total = len(entregas)
                    entregues = sum(1 for e in entregas if e["entregue"])
                    pendentes = total - entregues
                    percentual = (entregues / total * 100) if total > 0 else 0
                    
                    # Calcula totais de materiais quantitativos
                    cimento_total = 0
                    brita_total = 0
                    areia_total = 0
                    
                    for e in entregas:
                        if e["material"] == "Cimento composto CP II" and e["entregue"]:
                            cimento_total = e["quantidade_total"]
                        elif e["material"] == "Pedra brita 19" and e["entregue"]:
                            brita_total = e["quantidade_total"]
                        elif e["material"] == "Areia média" and e["entregue"]:
                            areia_total = e["quantidade_total"]
                    
                    dados_relatorio.append({
                        "Município": municipio,
                        "Casa": casa,
                        "Total": total,
                        "Entregues": entregues,
                        "Pendentes": pendentes,
                        "% Concluído": f"{percentual:.1f}%",
                        "Cimento (sacos)": f"{cimento_total:.0f}" if cimento_total > 0 else "—",
                        "Brita (m³)": f"{brita_total:.1f}" if brita_total > 0 else "—",
                        "Areia (m³)": f"{areia_total:.1f}" if areia_total > 0 else "—"
                    })
        
        if dados_relatorio:
            df = pd.DataFrame(dados_relatorio)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("📈 Resumo Geral")
            
            total_geral = sum(d["Total"] for d in dados_relatorio)
            entregues_geral = sum(d["Entregues"] for d in dados_relatorio)
            pendentes_geral = sum(d["Pendentes"] for d in dados_relatorio)
            perc_geral = (entregues_geral / total_geral * 100) if total_geral > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Materiais", total_geral)
            col2.metric("Entregues", entregues_geral)
            col3.metric("Pendentes", pendentes_geral)
            col4.metric("% Concluído", f"{perc_geral:.1f}%")
        else:
            st.info("Nenhum dado disponível.")


# =====================================================
# MAIN
# =====================================================

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