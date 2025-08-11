# ImoYield · Mapa de Rentabilidade (v0.2)
**ImoYield** é um mapa web que mostra a rentabilidade (yield, cap rate e yield líquida) por **freguesia** e **tipologia** (garagens, arrecadações, apartamentos, moradias), com módulos **EPBD** (custo de upgrade energético) e **GEE** (emissões operacionais).

## Como correr localmente
```bash
pip install -r requirements.txt
streamlit run imoyield_app.py
```

## Deploy (Streamlit Cloud)
1. Crie um repositório GitHub chamado `imoyield` e suba estes ficheiros.
2. Em streamlit.io → *Deploy an app* → selecione `imoyield_app.py`.
3. Python 3.10+ e `requirements.txt` como dependências.
4. Defina o *secrets* se/ quando precisar de chaves (não necessárias nesta v0.2).

## Dados
- `data/sample_listings.csv`: exemplos; substitua por CSV/Sheets com os seus imóveis.
- `data/freguesias_sample.geojson`: **DEMO**. Troque pelo **CAOP (DGT)** com códigos INE para *joins* robustos.
- `data/epbd_upgrade_costs.csv`: custos €/m² por tipologia e classe alvo.
- `data/emission_factors.csv`: fatores de emissão (kgCO₂e/kWh).

## Branding
- **Nome:** ImoYield
- **Cores:** teal `#14B8A6`, azul‑escuro `#0F172A`, laranja `#F97316`
- **Assets:** `assets/logo.png`, `assets/logo_wordmark.svg`, `assets/favicon.png`
- Tema dark ativado em `.streamlit/config.toml`.

## Roadmap curto
- [ ] Substituir polígonos de demo por **CAOP oficial (DGT)** + códigos INE
- [ ] Importar anúncios via CSV/Google Sheets e normalizar campos
- [ ] Estimar CE/consumos por zona climática (quando em falta) e marcar como *estimado*
- [ ] Exportar ficha de investimento em PDF
- [ ] Guardar histórico para *trends* por freguesia/tipologia
