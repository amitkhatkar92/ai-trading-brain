"""
oios/seeds/universe_230.py

Authoritative list of 230 NSE symbols constituting the OIOS trading universe.
Drawn from NIFTY 50, NIFTY Next 50, NIFTY Midcap 100, and select sector leaders.

Schema per entry: (symbol, company_name, sector, sector_purity_score)
  symbol              — Yahoo Finance ticker (with .NS suffix for NSE equities)
  company_name        — display name
  sector              — primary sector (used for Layer 1.5 participation buckets)
  sector_purity_score — 1.0 for pure-plays; lower for conglomerates

Sectors used (12 buckets for manageable participation statistics):
  BANKING_FINANCE, IT, PHARMA, AUTO, FMCG, DEFENCE, INFRA,
  METALS, ENERGY, TELECOM, CONSUMER_DURABLES, CHEMICALS
"""

# fmt: off
UNIVERSE_230: list[tuple[str, str, str, float]] = [
    # ------------------------------------------------------------------
    # BANKING & FINANCE (30)
    # ------------------------------------------------------------------
    ("HDFCBANK.NS",  "HDFC Bank",                     "BANKING_FINANCE", 1.00),
    ("ICICIBANK.NS", "ICICI Bank",                     "BANKING_FINANCE", 1.00),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank",             "BANKING_FINANCE", 0.90),
    ("AXISBANK.NS",  "Axis Bank",                      "BANKING_FINANCE", 1.00),
    ("SBIN.NS",      "State Bank of India",             "BANKING_FINANCE", 1.00),
    ("INDUSINDBK.NS","IndusInd Bank",                   "BANKING_FINANCE", 1.00),
    ("BANKBARODA.NS","Bank of Baroda",                  "BANKING_FINANCE", 1.00),
    ("PNB.NS",       "Punjab National Bank",            "BANKING_FINANCE", 1.00),
    ("CANBK.NS",     "Canara Bank",                     "BANKING_FINANCE", 1.00),
    ("UNIONBANK.NS", "Union Bank of India",             "BANKING_FINANCE", 1.00),
    ("IDFCFIRSTB.NS","IDFC First Bank",                 "BANKING_FINANCE", 1.00),
    ("FEDERALBNK.NS","Federal Bank",                    "BANKING_FINANCE", 1.00),
    ("RBLBANK.NS",   "RBL Bank",                        "BANKING_FINANCE", 1.00),
    ("YESBANK.NS",   "Yes Bank",                        "BANKING_FINANCE", 1.00),
    ("BAJFINANCE.NS","Bajaj Finance",                   "BANKING_FINANCE", 0.95),
    ("BAJAJFINSV.NS","Bajaj Finserv",                   "BANKING_FINANCE", 0.80),
    ("HDFCLIFE.NS",  "HDFC Life Insurance",             "BANKING_FINANCE", 1.00),
    ("SBILIFE.NS",   "SBI Life Insurance",              "BANKING_FINANCE", 1.00),
    ("ICICIGI.NS",   "ICICI Lombard General Insurance", "BANKING_FINANCE", 1.00),
    ("CHOLAFIN.NS",  "Cholamandalam Investment Finance","BANKING_FINANCE", 0.90),
    ("MUTHOOTFIN.NS","Muthoot Finance",                 "BANKING_FINANCE", 0.95),
    ("LICHSGFIN.NS", "LIC Housing Finance",             "BANKING_FINANCE", 1.00),
    ("M&MFIN.NS",    "Mahindra & Mahindra Financial",   "BANKING_FINANCE", 0.90),
    ("RECLTD.NS",    "REC Ltd",                         "BANKING_FINANCE", 0.85),
    ("PFC.NS",       "Power Finance Corp",              "BANKING_FINANCE", 0.85),
    ("SHRIRAMFIN.NS","Shriram Finance",                 "BANKING_FINANCE", 0.90),
    ("MANAPPURAM.NS","Manappuram Finance",              "BANKING_FINANCE", 0.95),
    ("IIFLFINANCE.NS","IIFL Finance",                   "BANKING_FINANCE", 0.90),
    ("IRFC.NS",      "Indian Railway Finance Corp",     "BANKING_FINANCE", 0.85),
    ("BSE.NS",       "BSE Ltd",                         "BANKING_FINANCE", 0.80),

    # ------------------------------------------------------------------
    # IT (20)
    # ------------------------------------------------------------------
    ("TCS.NS",       "Tata Consultancy Services",       "IT", 1.00),
    ("INFY.NS",      "Infosys",                         "IT", 1.00),
    ("WIPRO.NS",     "Wipro",                           "IT", 0.90),
    ("HCLTECH.NS",   "HCL Technologies",                "IT", 1.00),
    ("TECHM.NS",     "Tech Mahindra",                   "IT", 0.95),
    ("LTIM.NS",      "LTIMindtree",                     "IT", 1.00),
    ("MPHASIS.NS",   "Mphasis",                         "IT", 1.00),
    ("PERSISTENT.NS","Persistent Systems",              "IT", 1.00),
    ("COFORGE.NS",   "Coforge",                         "IT", 1.00),
    ("OFSS.NS",      "Oracle Financial Services",       "IT", 1.00),
    ("KPITTECH.NS",  "KPIT Technologies",               "IT", 1.00),
    ("ZENSARTECH.NS","Zensar Technologies",             "IT", 1.00),
    ("HEXAWARE.NS",  "Hexaware Technologies",           "IT", 1.00),
    ("MASTEK.NS",    "Mastek",                          "IT", 1.00),
    ("NIIT.NS",      "NIIT Ltd",                        "IT", 0.85),
    ("RATEGAIN.NS",  "RateGain Travel Technologies",   "IT", 1.00),
    ("NAUKRI.NS",    "Info Edge (India)",               "IT", 0.80),
    ("POLICYBZR.NS", "PB Fintech (PolicyBazaar)",       "IT", 0.85),
    ("MAPMYINDIA.NS","MapmyIndia (CE Info Systems)",    "IT", 1.00),
    ("INTELLECT.NS", "Intellect Design Arena",          "IT", 1.00),

    # ------------------------------------------------------------------
    # PHARMA (20)
    # ------------------------------------------------------------------
    ("SUNPHARMA.NS", "Sun Pharmaceutical",              "PHARMA", 1.00),
    ("DRREDDY.NS",   "Dr. Reddy's Laboratories",        "PHARMA", 1.00),
    ("CIPLA.NS",     "Cipla",                           "PHARMA", 1.00),
    ("DIVISLAB.NS",  "Divi's Laboratories",             "PHARMA", 1.00),
    ("AUROPHARMA.NS","Aurobindo Pharma",                "PHARMA", 1.00),
    ("LUPIN.NS",     "Lupin",                           "PHARMA", 1.00),
    ("BIOCON.NS",    "Biocon",                          "PHARMA", 0.90),
    ("TORNTPHARM.NS","Torrent Pharmaceuticals",         "PHARMA", 1.00),
    ("IPCA.NS",      "IPCA Laboratories",               "PHARMA", 1.00),
    ("ALKEM.NS",     "Alkem Laboratories",              "PHARMA", 1.00),
    ("ABBOTINDIA.NS","Abbott India",                    "PHARMA", 1.00),
    ("PFIZER.NS",    "Pfizer India",                    "PHARMA", 1.00),
    ("SANOFI.NS",    "Sanofi India",                    "PHARMA", 1.00),
    ("GLAXO.NS",     "GSK Pharmaceuticals",             "PHARMA", 1.00),
    ("GRANULES.NS",  "Granules India",                  "PHARMA", 1.00),
    ("AJANTPHARM.NS","Ajanta Pharma",                   "PHARMA", 1.00),
    ("ERIS.NS",      "Eris Lifesciences",               "PHARMA", 1.00),
    ("GLENMARK.NS",  "Glenmark Pharmaceuticals",        "PHARMA", 1.00),
    ("NATCOPHARM.NS","Natco Pharma",                    "PHARMA", 1.00),
    ("LAURUSLABS.NS","Laurus Labs",                     "PHARMA", 1.00),

    # ------------------------------------------------------------------
    # AUTO (20)  — TVSMOTORS.NS removed (invalid; TVSMOTOR.NS is correct)
    # ------------------------------------------------------------------
    ("MARUTI.NS",    "Maruti Suzuki",                   "AUTO", 1.00),
    ("M&M.NS",       "Mahindra & Mahindra",             "AUTO", 0.85),
    ("TATAMOTORS.NS","Tata Motors",                     "AUTO", 0.85),
    ("BAJAJ-AUTO.NS","Bajaj Auto",                      "AUTO", 1.00),
    ("EICHERMOT.NS", "Eicher Motors",                   "AUTO", 0.90),
    ("HEROMOTOCO.NS","Hero MotoCorp",                   "AUTO", 1.00),
    ("TVSMOTOR.NS",  "TVS Motor Company",               "AUTO", 0.90),
    ("ASHOKLEY.NS",  "Ashok Leyland",                   "AUTO", 1.00),
    ("BOSCHLTD.NS",  "Bosch India",                     "AUTO", 0.90),
    ("MOTHERSON.NS", "Samvardhana Motherson",           "AUTO", 0.85),
    ("BHARATFORG.NS","Bharat Forge",                    "AUTO", 0.90),
    ("EXIDEIND.NS",  "Exide Industries",                "AUTO", 0.90),
    ("AMARAJABAT.NS","Amara Raja Energy & Mobility",    "AUTO", 0.85),
    ("SUNDRMFAST.NS","Sundram Fasteners",               "AUTO", 0.90),
    ("ENDURANCE.NS", "Endurance Technologies",          "AUTO", 1.00),
    ("MINDAIND.NS",  "Spark Minda",                     "AUTO", 0.90),
    ("APOLLOTYRE.NS","Apollo Tyres",                    "AUTO", 1.00),
    ("TIINDIA.NS",   "Tube Investments of India",       "AUTO", 0.80),
    ("OLECTRA.NS",   "Olectra Greentech",               "AUTO", 0.90),
    ("CRAFTSMAN.NS", "Craftsman Automation",            "AUTO", 1.00),

    # ------------------------------------------------------------------
    # FMCG (20)
    # ------------------------------------------------------------------
    ("HINDUNILVR.NS","Hindustan Unilever",              "FMCG", 1.00),
    ("ITC.NS",       "ITC Ltd",                         "FMCG", 0.70),
    ("NESTLEIND.NS", "Nestle India",                    "FMCG", 1.00),
    ("BRITANNIA.NS", "Britannia Industries",            "FMCG", 1.00),
    ("DABUR.NS",     "Dabur India",                     "FMCG", 1.00),
    ("MARICO.NS",    "Marico",                          "FMCG", 1.00),
    ("GODREJCP.NS",  "Godrej Consumer Products",        "FMCG", 0.90),
    ("COLPAL.NS",    "Colgate-Palmolive India",         "FMCG", 1.00),
    ("EMAMILTD.NS",  "Emami",                           "FMCG", 0.85),
    ("TATACONSUM.NS","Tata Consumer Products",          "FMCG", 0.80),
    ("PGHH.NS",      "P&G Hygiene & Healthcare",        "FMCG", 1.00),
    ("VBL.NS",       "Varun Beverages",                 "FMCG", 0.90),
    ("RADICO.NS",    "Radico Khaitan",                  "FMCG", 0.85),
    ("ZYDUSWELL.NS", "Zydus Wellness",                  "FMCG", 0.90),
    ("JYOTHYLAB.NS", "Jyothy Labs",                     "FMCG", 1.00),
    ("BIKAJI.NS",    "Bikaji Foods International",      "FMCG", 1.00),
    ("DEVYANIINTL.NS","Devyani International",          "FMCG", 1.00),
    ("SAPPHIRE.NS",  "Sapphire Foods India",            "FMCG", 1.00),
    ("GODREJAGRO.NS","Godrej Agrovet",                  "FMCG", 0.80),
    ("GODFRYPHLPS.NS","Godfrey Phillips India",         "FMCG", 0.75),

    # ------------------------------------------------------------------
    # DEFENCE (15)
    # ------------------------------------------------------------------
    ("HAL.NS",       "Hindustan Aeronautics",           "DEFENCE", 1.00),
    ("BEL.NS",       "Bharat Electronics",              "DEFENCE", 0.95),
    ("BEML.NS",      "BEML Ltd",                        "DEFENCE", 0.80),
    ("BDL.NS",       "Bharat Dynamics",                 "DEFENCE", 1.00),
    ("COCHINSHIP.NS","Cochin Shipyard",                  "DEFENCE", 0.90),
    ("MIDHANI.NS",   "Mishra Dhatu Nigam (MIDHANI)",    "DEFENCE", 0.85),
    ("MAZDOCK.NS",   "Mazagon Dock Shipbuilders",       "DEFENCE", 1.00),
    ("GRSE.NS",      "Garden Reach Shipbuilders",       "DEFENCE", 1.00),
    ("PARAS.NS",     "Paras Defence & Space Technologies","DEFENCE",1.00),
    ("DATAPATTNS.NS","Data Patterns (India)",           "DEFENCE", 1.00),
    ("ASTRA.NS",     "Astra Microwave Products",        "DEFENCE", 1.00),
    ("IDEAFORGE.NS", "ideaForge Technology",            "DEFENCE", 1.00),
    ("SOLARINDS.NS", "Solar Industries India",          "DEFENCE", 0.85),
    ("MTAR.NS",      "MTAR Technologies",               "DEFENCE", 1.00),
    ("CENTUM.NS",    "Centum Electronics",              "DEFENCE", 0.90),

    # ------------------------------------------------------------------
    # INFRA & CONSTRUCTION (20)
    # ------------------------------------------------------------------
    ("LT.NS",        "Larsen & Toubro",                 "INFRA", 0.75),
    ("ADANIPORTS.NS","Adani Ports",                     "INFRA", 0.90),
    ("POWERGRID.NS", "Power Grid Corp",                 "INFRA", 1.00),
    ("NTPC.NS",      "NTPC",                            "INFRA", 0.90),
    ("ADANIGREEN.NS","Adani Green Energy",              "INFRA", 1.00),
    ("ADANIENSOL.NS","Adani Energy Solutions",          "INFRA", 0.90),
    ("TORNTPOWER.NS","Torrent Power",                   "INFRA", 0.90),
    ("CESC.NS",      "CESC Ltd",                        "INFRA", 0.85),
    ("JSWENERGY.NS", "JSW Energy",                      "INFRA", 0.90),
    ("IRCON.NS",     "IRCON International",             "INFRA", 0.90),
    ("RVNL.NS",      "Rail Vikas Nigam",                "INFRA", 0.95),
    ("IRCTC.NS",     "IRCTC",                           "INFRA", 0.85),
    ("LTTS.NS",      "L&T Technology Services",         "INFRA", 0.80),
    ("NCC.NS",       "NCC Ltd",                         "INFRA", 0.95),
    ("KNR.NS",       "KNR Constructions",               "INFRA", 1.00),
    ("PNBHOUSING.NS","PNB Housing Finance",             "INFRA", 0.90),
    ("DLF.NS",       "DLF Ltd",                         "INFRA", 1.00),
    ("GODREJPROP.NS","Godrej Properties",               "INFRA", 1.00),
    ("PRESTIGE.NS",  "Prestige Estates Projects",       "INFRA", 1.00),
    ("SOBHA.NS",     "Sobha Ltd",                       "INFRA", 1.00),

    # ------------------------------------------------------------------
    # METALS & MINING (17)
    # ------------------------------------------------------------------
    ("TATASTEEL.NS", "Tata Steel",                      "METALS", 1.00),
    ("JSWSTEEL.NS",  "JSW Steel",                       "METALS", 1.00),
    ("HINDALCO.NS",  "Hindalco Industries",             "METALS", 0.90),
    ("VEDL.NS",      "Vedanta Ltd",                     "METALS", 0.75),
    ("COALINDIA.NS", "Coal India",                      "METALS", 1.00),
    ("SAIL.NS",      "Steel Authority of India",        "METALS", 1.00),
    ("NMDC.NS",      "NMDC Ltd",                        "METALS", 1.00),
    ("NATIONALUM.NS","National Aluminium Company",      "METALS", 1.00),
    ("HINDZINC.NS",  "Hindustan Zinc",                  "METALS", 0.90),
    ("MOIL.NS",      "MOIL Ltd",                        "METALS", 1.00),
    ("WELCORP.NS",   "Welspun Corp",                    "METALS", 0.85),
    ("APL.NS",       "APL Apollo Tubes",                "METALS", 1.00),
    ("RATNAMANI.NS", "Ratnamani Metals & Tubes",        "METALS", 1.00),
    ("JINDALSTEL.NS","Jindal Steel & Power",            "METALS", 0.90),
    ("JINDALPOLY.NS","Jindal Poly Films",               "METALS", 0.80),
    ("SHYAMMETL.NS", "Shyam Metalics & Energy",         "METALS", 0.90),
    ("TINPLATE.NS",  "Tinplate Company of India",       "METALS", 1.00),

    # ------------------------------------------------------------------
    # ENERGY / OIL & GAS (18)
    # ------------------------------------------------------------------
    ("RELIANCE.NS",  "Reliance Industries",             "ENERGY", 0.70),
    ("ONGC.NS",      "Oil & Natural Gas Corp",          "ENERGY", 1.00),
    ("IOC.NS",       "Indian Oil Corp",                 "ENERGY", 1.00),
    ("BPCL.NS",      "Bharat Petroleum Corp",           "ENERGY", 1.00),
    ("HPCL.NS",      "Hindustan Petroleum Corp",        "ENERGY", 1.00),
    ("GAIL.NS",      "GAIL (India)",                    "ENERGY", 0.90),
    ("IGL.NS",       "Indraprastha Gas",                "ENERGY", 1.00),
    ("MGL.NS",       "Mahanagar Gas",                   "ENERGY", 1.00),
    ("PETRONET.NS",  "Petronet LNG",                    "ENERGY", 1.00),
    ("GUJARATGAS.NS","Gujarat Gas",                     "ENERGY", 1.00),
    ("OIL.NS",       "Oil India",                       "ENERGY", 1.00),
    ("MRPL.NS",      "MRPL Ltd",                        "ENERGY", 1.00),
    ("CASTROLIND.NS","Castrol India",                   "ENERGY", 1.00),
    ("TATAPOWER.NS", "Tata Power Company",              "ENERGY", 0.80),
    ("SUZLON.NS",    "Suzlon Energy",                   "ENERGY", 1.00),
    ("NHPC.NS",      "NHPC Ltd",                        "ENERGY", 1.00),
    ("SJVN.NS",      "SJVN Ltd",                        "ENERGY", 1.00),
    ("JPPOWER.NS",   "Jaiprakash Power Ventures",       "ENERGY", 0.85),

    # ------------------------------------------------------------------
    # TELECOM (10)
    # ------------------------------------------------------------------
    ("BHARTIARTL.NS","Bharti Airtel",                   "TELECOM", 0.90),
    ("IDEA.NS",      "Vodafone Idea",                   "TELECOM", 1.00),
    ("TATACOMM.NS",  "Tata Communications",             "TELECOM", 0.85),
    ("ROUTE.NS",     "Route Mobile",                    "TELECOM", 0.90),
    ("INDIAMART.NS", "IndiaMART InterMESH",             "TELECOM", 0.80),
    ("STLTECH.NS",   "Sterlite Technologies",           "TELECOM", 1.00),
    ("HFCL.NS",      "HFCL Ltd",                        "TELECOM", 1.00),
    ("TEJASNET.NS",  "Tejas Networks",                  "TELECOM", 1.00),
    ("RAILTEL.NS",   "RailTel Corporation",             "TELECOM", 0.90),
    ("ONMOBILE.NS",  "OnMobile Global",                 "TELECOM", 0.85),

    # ------------------------------------------------------------------
    # CONSUMER DURABLES (20)
    # ------------------------------------------------------------------
    ("TITAN.NS",     "Titan Company",                   "CONSUMER_DURABLES", 0.90),
    ("VOLTAS.NS",    "Voltas",                          "CONSUMER_DURABLES", 0.90),
    ("BLUESTARCO.NS","Blue Star",                       "CONSUMER_DURABLES", 1.00),
    ("HAVELLS.NS",   "Havells India",                   "CONSUMER_DURABLES", 0.90),
    ("POLYCAB.NS",   "Polycab India",                   "CONSUMER_DURABLES", 0.90),
    ("KEI.NS",       "KEI Industries",                  "CONSUMER_DURABLES", 0.90),
    ("WHIRLPOOL.NS", "Whirlpool of India",              "CONSUMER_DURABLES", 1.00),
    ("VGUARD.NS",    "V-Guard Industries",              "CONSUMER_DURABLES", 0.90),
    ("CROMPTON.NS",  "Crompton Greaves Consumer",       "CONSUMER_DURABLES", 1.00),
    ("KAJARIAL.NS",  "Kajaria Ceramics",                "CONSUMER_DURABLES", 1.00),
    ("CERA.NS",      "Cera Sanitaryware",               "CONSUMER_DURABLES", 1.00),
    ("SYMPHONY.NS",  "Symphony Ltd",                    "CONSUMER_DURABLES", 1.00),
    ("RAJESHEXPO.NS","Rajesh Exports",                  "CONSUMER_DURABLES", 0.80),
    ("ASIANPAINT.NS","Asian Paints",                    "CONSUMER_DURABLES", 1.00),
    ("BERGERPAINTS.NS","Berger Paints India",           "CONSUMER_DURABLES", 1.00),
    ("BATAINDIA.NS", "Bata India",                      "CONSUMER_DURABLES", 1.00),
    ("PAGEIND.NS",   "Page Industries",                 "CONSUMER_DURABLES", 1.00),
    ("METROBRAND.NS","Metro Brands",                    "CONSUMER_DURABLES", 1.00),
    ("KALYANKJIL.NS","Kalyan Jewellers India",           "CONSUMER_DURABLES", 0.90),
    ("AMBER.NS",     "Amber Enterprises India",         "CONSUMER_DURABLES", 1.00),

    # ------------------------------------------------------------------
    # CHEMICALS (20)  — AAVAS.NS (housing finance, wrong sector) replaced with
    #                   DEEPAKFERT.NS; TATACHEMICALS.NS removed (invalid, use TATACHEM.NS)
    # ------------------------------------------------------------------
    ("PIDILITIND.NS","Pidilite Industries",             "CHEMICALS", 1.00),
    ("SRF.NS",       "SRF Ltd",                         "CHEMICALS", 0.90),
    ("DEEPAKFERT.NS","Deepak Fertilisers",              "CHEMICALS", 0.90),
    ("ATUL.NS",      "Atul Ltd",                        "CHEMICALS", 0.90),
    ("DEEPAKNTR.NS", "Deepak Nitrite",                  "CHEMICALS", 1.00),
    ("CLEAN.NS",     "Clean Science & Technology",      "CHEMICALS", 1.00),
    ("FINPIPE.NS",   "Finolex Industries",              "CHEMICALS", 0.85),
    ("TATACHEM.NS",  "Tata Chemicals",                  "CHEMICALS", 0.80),
    ("COROMANDEL.NS","Coromandel International",        "CHEMICALS", 0.90),
    ("NAVINFLUOR.NS","Navin Fluorine International",    "CHEMICALS", 1.00),
    ("ALKYLAMINE.NS","Alkyl Amines Chemicals",          "CHEMICALS", 1.00),
    ("BALAKRISIND.NS","Balkrishna Industries",          "CHEMICALS", 0.90),
    ("GNFC.NS",      "GNFC Ltd",                        "CHEMICALS", 0.85),
    ("GALAXYSURF.NS","Galaxy Surfactants",              "CHEMICALS", 1.00),
    ("FINEORG.NS",   "Fine Organic Industries",         "CHEMICALS", 1.00),
    ("VINATIORGA.NS","Vinati Organics",                 "CHEMICALS", 1.00),
    ("AARTI.NS",     "Aarti Industries",                "CHEMICALS", 0.95),
    ("NOCIL.NS",     "NOCIL Ltd",                       "CHEMICALS", 1.00),
    ("SUDARSCHEM.NS","Sudarshan Chemical Industries",   "CHEMICALS", 1.00),
    ("BASF.NS",      "BASF India",                      "CHEMICALS", 0.85),
]
# fmt: on
