# Geoportal · Potencial de Restauração em Terras Indígenas de Rondônia
**Ecoporé · Projeto Tawi**

---

## Estrutura

```
geoportal_final/
├── app.py                        ← app Streamlit (entry point)
├── requirements.txt              ← dependências do Streamlit Cloud
├── .streamlit/config.toml        ← tema
├── .gitignore
├── scripts/
│   ├── config.py                 ← caminhos e constantes centralizados
│   ├── 00_preparar_dados.py      ← PASSO 1: processa vetores e rasters
│   └── 01_gerar_overlays.py      ← PASSO 2: gera PNGs para o mapa
└── data/
    ├── raw/                      ← coloque os 4 arquivos originais aqui
    ├── processado/               ← gerado pelos scripts
    └── estatisticas/             ← gerado pelos scripts
```

---

## Setup local (preparar dados)

### 1. Dependências locais
```bash
conda activate geo_stats_env
pip install rio-cogeo rasterstats matplotlib Pillow --break-system-packages
```

### 2. Copiar arquivos brutos para `data/raw/`
```
ESTADO_RO.gpkg
TERRAS_INDIGENAS_RO.gpkg
FLORESTA_SECUNDARIA_RO.tif
POTENCIAL_RN_RO.tif
```

### 3. Rodar os scripts de preparação
```bash
python scripts/00_preparar_dados.py
python scripts/01_gerar_overlays.py
```

### 4. Testar local
```bash
streamlit run app.py
```

---

## Deploy no Streamlit Community Cloud

```bash
git add .
git commit -m "dados processados e overlays"
git push
```

Acesse [share.streamlit.io](https://share.streamlit.io) → conecte o repositório → `app.py` → Deploy.

---

## Atualizar dados

Basta rodar os scripts novamente e fazer push. O Streamlit Cloud atualiza automaticamente.
