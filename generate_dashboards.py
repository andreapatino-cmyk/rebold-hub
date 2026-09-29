"""
Rebold Email Intelligence — Dashboard Generator
Genera 4 dashboards HTML para Granite, Ayoba, Brooklyn Biltong y Beg & Barker
Corre via GitHub Actions cada lunes a las 8am o manualmente
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional

# ─── CONFIGURACIÓN DE MARCAS ───────────────────────────────────────────────
BRANDS = {
    "granite": {
        "name": "Granite Nutrition",
        "emoji": "🏋️",
        "category": "Suplementos deportivos · USA",
        "color": "#B5F23D",
        "color_dim": "rgba(181,242,61,0.12)",
        "api_key": os.environ.get("GRANITE_API_KEY", "pk_XH3TM4_993ba3c779cea78552ef4c4dfe9caf0783"),
        "conversion_metric_id": os.environ.get("GRANITE_METRIC_ID", "T3ZNfY"),
        "output_file": "granite_dashboard.html",
    },
    "ayoba": {
        "name": "Ayoba",
        "emoji": "🥩",
        "category": "Biltong & droëwors · USA",
        "color": "#F2A93D",
        "color_dim": "rgba(242,169,61,0.12)",
        "api_key": os.environ.get("AYOBA_API_KEY", "pk_PFSEH6_94c54725e3b3b02090dd00c5f4c1960033"),
        "conversion_metric_id": os.environ.get("AYOBA_METRIC_ID", "Q8VsyA"),
        "output_file": "ayoba_dashboard.html",
    },
    "brooklyn": {
        "name": "Brooklyn Biltong",
        "emoji": "🥩",
        "category": "Biltong artesanal · USA",
        "color": "#3DA8F2",
        "color_dim": "rgba(61,168,242,0.12)",
        "api_key": os.environ.get("BROOKLYN_API_KEY", "pk_QPi6TF_082ea8c374c1efb6d5e0d2911c3e8341e3"),
        "conversion_metric_id": os.environ.get("BROOKLYN_METRIC_ID", ""),
        "output_file": "brooklyn_dashboard.html",
    },
    "beg": {
        "name": "Beg & Barker",
        "emoji": "🐾",
        "category": "Snacks para mascotas · USA",
        "color": "#A78BFA",
        "color_dim": "rgba(167,139,250,0.12)",
        "api_key": os.environ.get("BEG_API_KEY", "pk_VYN5jd_b6cdf50c53deafca2a858a8a3b4c61795d"),
        "conversion_metric_id": os.environ.get("BEG_METRIC_ID", ""),
        "output_file": "beg_dashboard.html",
    },
}

REVISION = "2025-01-15"
BASE_URL = "https://a.klaviyo.com/api"

# ─── CLIENTE KLAVIYO ───────────────────────────────────────────────────────
class KlaviyoClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "revision": REVISION,
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Error GET {endpoint}: {e}")
            return {}

    def post(self, endpoint: str, body: dict) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        try:
            r = requests.post(url, headers=self.headers, json=body, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Error POST {endpoint}: {e}")
            return {}

    def get_conversion_metric_id(self) -> Optional[str]:
        """Obtiene el metric ID de Placed Order automáticamente"""
        data = self.get("metrics/")
        for item in data.get("data", []):
            name = item.get("attributes", {}).get("name", "").lower()
            if "placed order" in name or "placed_order" in name:
                return item["id"]
        return None

    def get_campaigns(self) -> list:
        data = self.get("campaigns/", {
            "filter": 'equals(messages.channel,"email")',
            "sort": "-updated_at",
        })
        return data.get("data", [])

    def get_campaign_report(self, conversion_metric_id: str, start_date: str, end_date: str) -> dict:
        body = {
            "data": {
                "type": "campaign-values-report",
                "attributes": {
                    "timeframe": {
                        "start": start_date,
                        "end": end_date,
                    },
                    "conversion_metric_id": conversion_metric_id,
                    "filter": 'equals(send_channel,"email")',
                    "statistics": [
                        "recipients", "opens_unique", "clicks_unique",
                        "open_rate", "click_rate", "conversion_rate",
                        "conversion_uniques", "unsubscribes", "unsubscribe_rate"
                    ],
                    "group_by": ["campaign_id", "campaign_name"],
                },
            }
        }
        return self.post("campaign-values-reports/", body)

    def get_flows(self) -> list:
        data = self.get("flows/", {
            "filter": 'equals(status,"live")',
            "sort": "-updated_at",
        })
        return data.get("data", [])

    def get_flow_report(self, conversion_metric_id: str, start_date: str, end_date: str) -> dict:
        body = {
            "data": {
                "type": "flow-values-report",
                "attributes": {
                    "timeframe": {
                        "start": start_date,
                        "end": end_date,
                    },
                    "conversion_metric_id": conversion_metric_id,
                    "filter": 'equals(send_channel,"email")',
                    "statistics": [
                        "recipients", "opens_unique", "clicks_unique",
                        "open_rate", "click_rate", "conversion_rate",
                        "conversion_uniques"
                    ],
                    "group_by": ["flow_id", "flow_name"],
                },
            }
        }
        return self.post("flow-values-reports/", body)


# ─── EXTRACTOR DE DATOS ────────────────────────────────────────────────────
def fetch_brand_data(brand_config: dict) -> dict:
    print(f"\n📊 Leyendo datos de {brand_config['name']}...")
    client = KlaviyoClient(brand_config["api_key"])

    # Fechas: últimos 30 días
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    start_str = start.strftime("%Y-%m-%dT00:00:00+00:00")
    end_str = end.strftime("%Y-%m-%dT23:59:59+00:00")

    # Obtener conversion metric ID si no está hardcodeado
    conv_metric_id = brand_config.get("conversion_metric_id") or ""
    if not conv_metric_id:
        print("  Buscando conversion metric ID...")
        conv_metric_id = client.get_conversion_metric_id() or ""
        if conv_metric_id:
            print(f"  Metric ID encontrado: {conv_metric_id}")
        else:
            print("  ⚠️ No se encontró metric ID de Placed Order")

    # Campañas
    campaigns_raw = client.get_campaigns()
    print(f"  Campañas encontradas: {len(campaigns_raw)}")

    # Reporte de campañas
    campaign_report = {}
    if conv_metric_id and campaigns_raw:
        report_data = client.get_campaign_report(conv_metric_id, start_str, end_str)
        for item in report_data.get("data", []):
            attrs = item.get("attributes", {})
            cid = attrs.get("campaign_id", "")
            campaign_report[cid] = attrs

    # Flujos
    flows_raw = client.get_flows()
    print(f"  Flujos activos: {len(flows_raw)}")

    # Reporte de flujos
    flow_report = {}
    if conv_metric_id and flows_raw:
        report_data = client.get_flow_report(conv_metric_id, start_str, end_str)
        for item in report_data.get("data", []):
            attrs = item.get("attributes", {})
            fid = attrs.get("flow_id", "")
            flow_report[fid] = attrs

    # Procesar campañas
    campaigns = []
    for c in campaigns_raw[:20]:  # Últimas 20
        attrs = c.get("attributes", {})
        send_time = attrs.get("send_time", "") or attrs.get("scheduled_at", "")
        cid = c.get("id", "")
        report = campaign_report.get(cid, {})
        stats = report.get("statistics", {})

        date_str = ""
        if send_time:
            try:
                dt = datetime.fromisoformat(send_time.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except:
                date_str = send_time[:10]

        campaigns.append({
            "id": cid,
            "name": attrs.get("name", "Sin nombre"),
            "date": date_str,
            "status": attrs.get("status", ""),
            "open_rate": stats.get("open_rate", 0) or 0,
            "click_rate": stats.get("click_rate", 0) or 0,
            "conv_rate": stats.get("conversion_rate", 0) or 0,
            "conv_value": stats.get("conversion_value", 0) or 0,
            "rpr": stats.get("revenue_per_recipient", 0) or 0,
            "recipients": stats.get("recipients", 0) or 0,
            "unsub_rate": stats.get("unsubscribe_rate", 0) or 0,
        })

    # Procesar flujos
    flows = []
    for f in flows_raw[:10]:
        attrs = f.get("attributes", {})
        fid = f.get("id", "")
        report = flow_report.get(fid, {})
        stats = report.get("statistics", {})

        flows.append({
            "id": fid,
            "name": attrs.get("name", "Sin nombre"),
            "trigger": attrs.get("trigger_type", ""),
            "status": attrs.get("status", "live"),
            "open_rate": stats.get("open_rate", 0) or 0,
            "click_rate": stats.get("click_rate", 0) or 0,
            "conv_rate": stats.get("conversion_rate", 0) or 0,
            "conv_value": stats.get("conversion_value", 0) or 0,
            "rpr": stats.get("revenue_per_recipient", 0) or 0,
            "recipients": stats.get("recipients", 0) or 0,
        })

    # KPIs globales
    sent = [c for c in campaigns if c["status"] in ["Sent", "Sending", "sent", "sending"]]
    total_camp_rev = sum(c["conv_value"] for c in sent)
    total_flow_rev = sum(f["conv_value"] for f in flows)
    avg_open = sum(c["open_rate"] for c in sent) / max(len(sent), 1)
    avg_click = sum(c["click_rate"] for c in sent) / max(len(sent), 1)
    avg_conv = sum(c["conv_rate"] for c in sent) / max(len(sent), 1)

    return {
        "brand": brand_config,
        "campaigns": campaigns,
        "flows": flows,
        "kpis": {
            "total_revenue": total_camp_rev + total_flow_rev,
            "campaign_revenue": total_camp_rev,
            "flow_revenue": total_flow_rev,
            "avg_open_rate": avg_open,
            "avg_click_rate": avg_click,
            "avg_conv_rate": avg_conv,
            "campaign_count": len(sent),
            "flow_count": len(flows),
        },
        "conv_metric_id": conv_metric_id,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "period": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        }
    }


# ─── GENERADOR DE HTML ─────────────────────────────────────────────────────
def generate_html(data: dict) -> str:
    brand = data["brand"]
    campaigns = data["campaigns"]
    flows = data["flows"]
    kpis = data["kpis"]
    generated_at = data["generated_at"]
    period = data["period"]

    color = brand["color"]
    color_dim = brand["color_dim"]
    name = brand["name"]
    emoji = brand["emoji"]
    category = brand["category"]

    # Serializar datos para JS
    campaigns_json = json.dumps(campaigns, ensure_ascii=False)
    flows_json = json.dumps(flows, ensure_ascii=False)
    kpis_json = json.dumps(kpis, ensure_ascii=False)

    # Flujos sugeridos por marca
    flujos_sugeridos = {
        "granite": [
            {"id": "winback", "name": "🔄 Win-Back — 60 días sin compra", "desc": "Para compradores inactivos. Alto impacto según métricas.", "tags": ["3 emails", "Alto impacto"]},
            {"id": "upsell", "name": "⬆️ Upsell post-compra", "desc": "Ofrecer proteína → recovery, pre-workout → aminos.", "tags": ["2 emails", "LTV"]},
            {"id": "educativo", "name": "📚 Educativo post-primera compra", "desc": "4 emails de valor antes de pedir recompra.", "tags": ["4 emails", "28 días"]},
            {"id": "abandono", "name": "🛒 Abandono de carrito optimizado", "desc": "Reemplazar flujo actual con 0% conversión.", "tags": ["3 emails", "Urgente"]},
            {"id": "vip", "name": "👑 VIP — Fidelización recurrentes", "desc": "Para clientes con 3+ compras.", "tags": ["3 emails", "Retención"]},
        ],
        "ayoba": [
            {"id": "winback", "name": "🔄 Win-Back — Reactivación 45 días", "desc": "Para clientes de biltong sin reorden.", "tags": ["3 emails", "45-60 días"]},
            {"id": "replenishment", "name": "🔁 Replenishment — Reabastecimiento", "desc": "Recordatorio de reorden por consumo estimado.", "tags": ["2 emails", "Recurrencia"]},
            {"id": "bundle", "name": "🎁 Bundle education", "desc": "Educar sobre combinar biltong + droëwors.", "tags": ["2 emails", "AOV"]},
        ],
        "brooklyn": [
            {"id": "welcome", "name": "👋 Welcome Series", "desc": "Bienvenida con historia vs jerky americano.", "tags": ["3 emails", "7 días"]},
            {"id": "winback", "name": "🔄 Win-Back — Reactivación", "desc": "Para clientes inactivos 60+ días.", "tags": ["3 emails", "60-90 días"]},
            {"id": "educativo", "name": "📚 Biltong 101", "desc": "Educar al cliente americano qué es el biltong.", "tags": ["3 emails", "Educational"]},
        ],
        "beg": [
            {"id": "welcome", "name": "🐾 Welcome para dueños de mascota", "desc": "Guía de snacks saludables y frecuencia.", "tags": ["3 emails", "7 días"]},
            {"id": "replenishment", "name": "🦴 Reabastecimiento de snacks", "desc": "Recordatorio por tamaño del perro y consumo.", "tags": ["2 emails", "21-30 días"]},
            {"id": "upsell", "name": "⬆️ Upsell por tamaño de perro", "desc": "Recomendar tamaño/sabor según el perfil.", "tags": ["2 emails", "Post-compra"]},
        ],
    }

    brand_key = [k for k in flujos_sugeridos.keys() if k in brand["output_file"].replace("_dashboard.html", "")]
    brand_key = brand_key[0] if brand_key else "granite"
    flujos = flujos_sugeridos.get(brand_key, flujos_sugeridos["granite"])
    flujos_json = json.dumps(flujos, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{name} — Email Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0D0F0E;--s1:#151918;--s2:#1C201F;--b:#252B29;
  --ac:{color};--acd:{color_dim};
  --red:#FF4D4D;--redd:rgba(255,77,77,.12);
  --amb:#F2A93D;--ambd:rgba(242,169,61,.12);
  --tx:#E8EDE8;--tx2:#8A9490;--tx3:#5A6460;
  box-sizing:border-box;
  padding-top:env(safe-area-inset-top,0px);
  padding-bottom:env(safe-area-inset-bottom,0px);
}}
*{{box-sizing:inherit;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tx);font-family:'Inter',sans-serif;font-size:14px;min-height:100vh}}
.topbar{{padding:14px 24px;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;position:sticky;top:0;background:var(--bg);z-index:100}}
.brand-name{{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;color:var(--ac)}}
.brand-sub{{font-size:11px;color:var(--tx3);margin-top:2px}}
.updated{{font-size:11px;color:var(--tx3);background:var(--s2);padding:4px 10px;border-radius:6px;border:1px solid var(--b)}}
.controls{{padding:12px 24px;border-bottom:1px solid var(--b);display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--s1)}}
.dl{{font-size:11px;color:var(--tx3);font-weight:500}}
.di{{background:var(--s2);border:1px solid var(--b);color:var(--tx);font-family:'Inter',sans-serif;font-size:12px;padding:6px 10px;border-radius:7px;outline:none;transition:border .2s}}
.di:focus,.di:hover{{border-color:var(--ac)}}
.qb{{padding:5px 11px;font-size:11px;font-weight:500;border-radius:6px;cursor:pointer;border:1px solid var(--b);background:none;color:var(--tx3);font-family:'Inter',sans-serif;transition:all .2s}}
.qb:hover{{border-color:var(--ac);color:var(--ac)}}.qb.active{{background:var(--acd);border-color:var(--ac);color:var(--ac)}}
.btn{{padding:7px 14px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif;border:none;display:inline-flex;align-items:center;gap:5px;transition:all .2s}}
.btn-opt{{background:var(--redd);color:var(--red);border:1px solid rgba(255,77,77,.25)}}
.btn-flu{{background:rgba(61,168,242,.12);color:#3DA8F2;border:1px solid rgba(61,168,242,.25)}}
.tabs{{display:flex;border-bottom:1px solid var(--b);padding:0 24px}}
.tab{{padding:10px 16px;font-size:13px;font-weight:500;color:var(--tx3);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .2s;white-space:nowrap}}
.tab:hover{{color:var(--tx2)}}.tab.active{{color:var(--ac);border-bottom-color:var(--ac)}}
.main{{padding:20px 24px;max-width:1300px}}
.kpig{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}}
.kc{{background:var(--s1);border:1px solid var(--b);border-radius:11px;padding:15px;position:relative;overflow:hidden}}
.kc::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
.kc.g::before{{background:var(--ac)}}.kc.r::before{{background:var(--red)}}.kc.a::before{{background:var(--amb)}}.kc.b::before{{background:#3DA8F2}}
.kl{{font-size:10px;color:var(--tx3);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
.kv{{font-family:'Space Grotesk',sans-serif;font-size:24px;font-weight:700;line-height:1;margin-bottom:2px}}
.ks{{font-size:11px;color:var(--tx3)}}.ks strong{{color:var(--ac)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}}
.card{{background:var(--s1);border:1px solid var(--b);border-radius:11px;overflow:hidden}}
.ch{{padding:13px 16px 10px;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between}}
.ct{{font-family:'Space Grotesk',sans-serif;font-size:13px;font-weight:600}}
.cb{{padding:14px 16px}}
.tbl{{width:100%;border-collapse:collapse}}
.tbl th{{font-size:10px;color:var(--tx3);font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:7px 10px;text-align:left;border-bottom:1px solid var(--b)}}
.tbl td{{padding:9px 10px;font-size:12px;color:var(--tx2);border-bottom:1px solid rgba(37,43,41,.4)}}
.tbl tr:last-child td{{border-bottom:none}}.tbl tr:hover td{{background:var(--s2)}}
.cn{{color:var(--tx);font-weight:500;max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pill{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600}}
.ph{{background:var(--acd);color:var(--ac)}}.pm{{background:var(--ambd);color:var(--amb)}}.pl{{background:var(--redd);color:var(--red)}}
.ins{{background:var(--acd);border:1px solid rgba(181,242,61,.15);border-radius:8px;padding:11px 13px;margin-bottom:14px;font-size:12px;color:var(--tx2);line-height:1.6}}
.ins strong{{color:var(--ac)}}
.fi{{padding:11px 0;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between}}
.fi:last-child{{border-bottom:none}}
.fn{{font-weight:500;color:var(--tx);font-size:12px}}.ft{{font-size:10px;color:var(--tx3);margin-top:2px}}
.frev{{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:600;color:var(--ac);text-align:right}}
.oi{{padding:12px;background:var(--s2);border-radius:7px;margin-bottom:9px;border-left:3px solid}}
.oi.cr{{border-color:var(--red)}}.oi.wa{{border-color:var(--amb)}}.oi.ok{{border-color:var(--ac)}}
.otag{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}}
.oi.cr .otag{{color:var(--red)}}.oi.wa .otag{{color:var(--amb)}}.oi.ok .otag{{color:var(--ac)}}
.ott{{font-weight:600;color:var(--tx);font-size:12px;margin-bottom:3px}}.odd{{color:var(--tx2);font-size:11px;line-height:1.5}}
.modal-ov{{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:200;display:none;align-items:center;justify-content:center;padding:20px}}
.modal-ov.open{{display:flex}}
.modal{{background:var(--s1);border:1px solid var(--b);border-radius:14px;width:100%;max-width:700px;max-height:88vh;overflow:hidden;display:flex;flex-direction:column}}
.mh{{padding:15px 18px;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between}}
.mt{{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:600}}
.mc{{padding:18px;overflow-y:auto;flex:1;font-size:13px;color:var(--tx2);line-height:1.7;white-space:pre-wrap}}
.mc h3{{color:var(--ac);font-size:13px;font-weight:700;margin:14px 0 5px;border-left:3px solid var(--ac);padding-left:8px;white-space:normal}}
.mc strong{{color:var(--tx)}}
.mc .step{{background:var(--s2);border-radius:7px;padding:11px 13px;margin-bottom:8px;border-left:3px solid var(--ac);white-space:normal}}
.mc .sn{{font-size:10px;color:var(--ac);font-weight:700;text-transform:uppercase;margin-bottom:3px}}
.mc .sd{{font-size:12px;color:var(--tx2)}}
.mf{{padding:12px 18px;border-top:1px solid var(--b);display:flex;gap:8px;justify-content:flex-end}}
.cbtn{{background:none;border:none;color:var(--tx3);cursor:pointer;font-size:18px}}
.fsel{{background:var(--s2);border:1px solid var(--b);border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;transition:all .2s}}
.fsel:hover,.fsel.sel{{border-color:var(--ac);background:var(--acd)}}
.fsn{{font-weight:600;color:var(--tx);font-size:13px;margin-bottom:3px}}.fsd{{font-size:12px;color:var(--tx2)}}
.ftag{{display:inline-block;background:rgba(61,168,242,.12);color:#3DA8F2;font-size:10px;padding:2px 6px;border-radius:4px;margin:3px 2px 0 0}}
.spin{{width:22px;height:22px;border:2px solid var(--b);border-top-color:var(--ac);border-radius:50%;animation:spin .8s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.lrow{{display:flex;align-items:center;gap:10px;color:var(--tx3);padding:24px;justify-content:center}}
@media(max-width:900px){{.kpig{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}.main{{padding:14px}}.topbar,.controls{{padding:12px 14px}}}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <div class="brand-name">{emoji} {name.upper()}</div>
    <div class="brand-sub">{category} · Email Intelligence · Alicia Prieto</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
    <div class="updated">Actualizado: {generated_at}</div>
    <button class="btn btn-opt" onclick="openOpt()">⚡ Ejecutar optimización</button>
    <button class="btn btn-flu" onclick="openFlujo()">+ Crear flujo</button>
  </div>
</div>

<div class="controls">
  <span class="dl">Desde</span>
  <input type="date" class="di" id="df" onchange="applyD()">
  <span style="color:var(--tx3);font-size:12px">→</span>
  <input type="date" class="di" id="dt" onchange="applyD()">
  <button class="qb" onclick="sq(7,this)">7 días</button>
  <button class="qb active" onclick="sq(30,this)">30 días</button>
  <button class="qb" onclick="sq(90,this)">3 meses</button>
  <button class="qb" onclick="sq('mes',this)">Este mes</button>
  <button class="qb" onclick="sq('lastmes',this)">Mes anterior</button>
  <span style="margin-left:auto;font-size:11px;color:var(--tx3)" id="dlabel"></span>
</div>

<div class="tabs">
  <div class="tab active" onclick="showT('resultados',this)">Resultados</div>
  <div class="tab" onclick="showT('flujos',this)">Flujos</div>
  <div class="tab" onclick="showT('optimizaciones',this)">Optimizaciones</div>
</div>

<div class="main">
  <div id="t-resultados"></div>
  <div id="t-flujos" style="display:none"></div>
  <div id="t-optimizaciones" style="display:none"></div>
</div>

<!-- MODAL OPTIMIZACIÓN -->
<div class="modal-ov" id="m-opt">
  <div class="modal">
    <div class="mh"><div class="mt">⚡ Plan de optimización — {name}</div><button class="cbtn" onclick="cm('m-opt')">✕</button></div>
    <div class="mc" id="m-opt-body"></div>
    <div class="mf">
      <button class="btn" style="background:var(--s2);border:1px solid var(--b);color:var(--tx2)" onclick="cm('m-opt')">Cerrar</button>
      <button class="btn" style="background:var(--acd);color:var(--ac);border:1px solid rgba(181,242,61,.2)" onclick="dlTxt('opt')">↓ Descargar</button>
    </div>
  </div>
</div>

<!-- MODAL FLUJOS -->
<div class="modal-ov" id="m-flu">
  <div class="modal">
    <div class="mh"><div class="mt">+ Crear flujo — {name}</div><button class="cbtn" onclick="cm('m-flu')">✕</button></div>
    <div class="mc" id="m-flu-body" style="white-space:normal">
      <p style="margin-bottom:12px;color:var(--tx2)">Selecciona el flujo a crear. Recibirás el paso a paso completo para subirlo a Klaviyo.</p>
      <div id="f-opts"></div>
      <div id="f-gen" style="display:none"><div class="lrow"><div class="spin"></div>Generando guía completa con IA…</div></div>
      <div id="f-res" style="display:none;white-space:pre-wrap;font-size:12px;line-height:1.7;color:var(--tx2)"></div>
    </div>
    <div class="mf">
      <button class="btn" id="f-back" style="display:none;background:var(--s2);border:1px solid var(--b);color:var(--tx2)" onclick="backF()">← Volver</button>
      <button class="btn" style="background:var(--s2);border:1px solid var(--b);color:var(--tx2)" onclick="cm('m-flu')">Cerrar</button>
      <button class="btn" id="f-dl" style="display:none;background:var(--acd);color:var(--ac);border:1px solid rgba(181,242,61,.2)" onclick="dlTxt('flu')">↓ Descargar paso a paso</button>
    </div>
  </div>
</div>

<script>
const ALL_CAMPS = {campaigns_json};
const ALL_FLOWS = {flows_json};
const KPIS = {kpis_json};
const FLUJOS = {flujos_json};
const BRAND_NAME = "{name}";
const BRAND_KEY = "{brand_key}";
const BRAND_CAT = "{category}";
const GENERATED = "{generated_at}";
const PERIOD_DEFAULT = {{start: "{period['start']}", end: "{period['end']}"}};

let df=null,dt=null,optTxt='',fluTxt='',selFlu='';

function fmt8(d){{return d.toISOString().split('T')[0]}}
function fmtU(n){{return'$'+Number(n||0).toFixed(0).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g,',')}}
function fmtP(n){{return(Number(n||0)*100).toFixed(1)+'%'}}
function pc(v,h,m){{return v>=h?'ph':v>=m?'pm':'pl'}}
function cm(id){{document.getElementById(id).classList.remove('open')}}
function showT(id,el){{
  ['resultados','flujos','optimizaciones'].forEach(t=>{{document.getElementById('t-'+t).style.display='none'}});
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('t-'+id).style.display='block';
  el.classList.add('active');
}}

function initD(){{
  const today=new Date();
  const from=new Date(today);from.setDate(from.getDate()-30);
  dt=today;df=from;
  document.getElementById('dt').value=fmt8(today);
  document.getElementById('df').value=fmt8(from);
  updLabel();
}}
function sq(n,btn){{
  document.querySelectorAll('.qb').forEach(b=>b.classList.remove('active'));btn.classList.add('active');
  const today=new Date();let from=new Date(today);
  if(n==='mes'){{from=new Date(today.getFullYear(),today.getMonth(),1);}}
  else if(n==='lastmes'){{from=new Date(today.getFullYear(),today.getMonth()-1,1);dt=new Date(today.getFullYear(),today.getMonth(),0);document.getElementById('dt').value=fmt8(dt);}}
  else{{from.setDate(from.getDate()-n);dt=today;document.getElementById('dt').value=fmt8(today);}}
  df=from;document.getElementById('df').value=fmt8(from);
  updLabel();render();
}}
function applyD(){{
  document.querySelectorAll('.qb').forEach(b=>b.classList.remove('active'));
  const f=document.getElementById('df').value,t=document.getElementById('dt').value;
  if(f)df=new Date(f);if(t)dt=new Date(t);
  updLabel();render();
}}
function updLabel(){{
  const ops={{day:'2-digit',month:'short',year:'numeric'}};
  document.getElementById('dlabel').textContent=(df?.toLocaleDateString('es',ops)||'—')+' → '+(dt?.toLocaleDateString('es',ops)||'—');
}}
function fCamps(){{
  return ALL_CAMPS.filter(c=>{{
    if(!c.date)return true;
    const d=new Date(c.date);
    return(!df||d>=df)&&(!dt||d<=dt);
  }});
}}

function render(){{
  const camps=fCamps();
  const sent=camps.filter(c=>['Sent','Sending','sent','sending'].includes(c.status));
  const campRev=sent.reduce((s,c)=>s+c.conv_value,0);
  const flowRev=ALL_FLOWS.reduce((s,f)=>s+f.conv_value,0);
  const totalRev=campRev+flowRev;
  const avgOr=sent.length?sent.reduce((s,c)=>s+c.open_rate,0)/sent.length:0;
  const avgCr=sent.length?sent.reduce((s,c)=>s+c.click_rate,0)/sent.length:0;
  const avgCvr=sent.length?sent.reduce((s,c)=>s+c.conv_rate,0)/sent.length:0;
  const sortRev=[...sent].sort((a,b)=>b.conv_value-a.conv_value);
  const best=sortRev[0],worst=sortRev[sortRev.length-1];

  document.getElementById('t-resultados').innerHTML=`
    <div class="kpig" style="margin-top:18px">
      <div class="kc g"><div class="kl">Revenue total</div><div class="kv">${{fmtU(totalRev)}}</div><div class="ks">Campañas ${{fmtU(campRev)}} + Flujos ${{fmtU(flowRev)}}</div></div>
      <div class="kc g"><div class="kl">Apertura promedio</div><div class="kv">${{fmtP(avgOr)}}</div><div class="ks">Industria 35–45%</div></div>
      <div class="kc a"><div class="kl">Clics promedio</div><div class="kv">${{fmtP(avgCr)}}</div><div class="ks">${{avgCr<.015?'⚠ Por debajo del objetivo':'✓ En rango'}}</div></div>
      <div class="kc b"><div class="kl">Conversión</div><div class="kv">${{fmtP(avgCvr)}}</div><div class="ks">${{sent.length}} campañas enviadas</div></div>
    </div>
    <div class="ins"><strong>Resumen ${{document.getElementById('dlabel').textContent}}:</strong> Revenue email: <strong>${{fmtU(totalRev)}}</strong>. Apertura promedio: <strong>${{fmtP(avgOr)}}</strong>. ${{sent.length}} campañas y ${{ALL_FLOWS.length}} flujos activos analizados.</div>
    <div class="two">
      <div class="card">
        <div class="ch"><div class="ct">Campañas del periodo</div><div style="font-size:11px;color:var(--tx3)">${{camps.length}} campañas</div></div>
        <table class="tbl"><thead><tr><th>Campaña</th><th>Apertura</th><th>Clics</th><th>Revenue</th></tr></thead><tbody>
          ${{camps.length?camps.map(c=>`<tr>
            <td><div class="cn">${{c.name}}</div><div style="font-size:10px;color:var(--tx3)">${{c.date||''}} · ${{c.status}}</div></td>
            <td>${{c.status==='queued'||!c.open_rate?'—':`<span class="pill ${{pc(c.open_rate,.65,.4)}}">${{fmtP(c.open_rate)}}</span>`}}</td>
            <td>${{c.status==='queued'||!c.click_rate?'—':`<span class="pill ${{pc(c.click_rate,.005,.002)}}">${{fmtP(c.click_rate)}}</span>`}}</td>
            <td style="font-weight:600;color:var(--tx)">${{fmtU(c.conv_value)}}</td>
          </tr>`).join(''):'<tr><td colspan="4" style="text-align:center;color:var(--tx3);padding:20px">Sin campañas en el periodo</td></tr>'}}
        </tbody></table>
      </div>
      <div>
        ${{best?`<div class="card" style="margin-bottom:14px">
          <div class="ch"><div class="ct">🏆 Mejor campaña</div></div>
          <div class="cb">
            <div style="font-size:13px;font-weight:600;color:var(--ac);margin-bottom:10px">${{best.name}}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px">
              <div><div style="font-size:10px;color:var(--tx3)">Revenue</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700">${{fmtU(best.conv_value)}}</div></div>
              <div><div style="font-size:10px;color:var(--tx3)">Apertura</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700">${{fmtP(best.open_rate)}}</div></div>
              <div><div style="font-size:10px;color:var(--tx3)">Conv.</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700">${{fmtP(best.conv_rate)}}</div></div>
            </div>
            <div style="font-size:12px;color:var(--tx2)">La campaña de mayor revenue en el periodo. Analizar asunto y segmento para replicar.</div>
          </div>
        </div>`:''}
        ${{worst&&worst!==best?`<div class="card">
          <div class="ch"><div class="ct">⚠️ A revisar</div></div>
          <div class="cb">
            <div style="font-size:13px;font-weight:600;color:var(--red);margin-bottom:10px">${{worst.name}}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px">
              <div><div style="font-size:10px;color:var(--tx3)">Revenue</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;color:var(--red)">${{fmtU(worst.conv_value)}}</div></div>
              <div><div style="font-size:10px;color:var(--tx3)">Apertura</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700">${{fmtP(worst.open_rate)}}</div></div>
              <div><div style="font-size:10px;color:var(--tx3)">Conv.</div><div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700">${{fmtP(worst.conv_rate)}}</div></div>
            </div>
            <div style="font-size:12px;color:var(--tx2)">Menor conversión del periodo. Revisar segmento, asunto y horario de envío.</div>
          </div>
        </div>`:''}
      </div>
    </div>`;

  document.getElementById('t-flujos').innerHTML=`
    <div style="margin-top:18px" class="card">
      <div class="ch"><div class="ct">Flujos activos</div></div>
      <table class="tbl"><thead><tr><th>Flujo</th><th>Trigger</th><th>Apertura</th><th>Conv.</th><th>Revenue</th><th>RPR</th></tr></thead><tbody>
        ${{ALL_FLOWS.length?ALL_FLOWS.map(f=>`<tr>
          <td class="cn">${{f.name}}</td>
          <td style="font-size:11px;color:var(--tx3)">${{f.trigger}}</td>
          <td><span class="pill ${{pc(f.open_rate,.5,.4)}}">${{fmtP(f.open_rate)}}</span></td>
          <td><span class="pill ${{pc(f.conv_rate,.05,.01)}}">${{fmtP(f.conv_rate)}}</span></td>
          <td style="font-weight:600;color:var(--tx)">${{fmtU(f.conv_value)}}</td>
          <td>${{fmtU(f.rpr)}}</td>
        </tr>`).join(''):'<tr><td colspan="6" style="text-align:center;color:var(--tx3);padding:20px">Sin flujos activos</td></tr>'}}
      </tbody></table>
    </div>`;

  const avgOpen=ALL_FLOWS.length?ALL_FLOWS.reduce((s,f)=>s+f.open_rate,0)/ALL_FLOWS.length:0;
  document.getElementById('t-optimizaciones').innerHTML=`
    <div style="margin-top:18px">
      <div style="font-size:13px;color:var(--tx2);margin-bottom:14px">Basado en ${{sent.length}} campañas y ${{ALL_FLOWS.length}} flujos. Usa <strong style="color:var(--red)">⚡ Ejecutar optimización</strong> para el plan completo con pasos de acción.</div>
      ${{avgOr>0&&avgOr<.4?`<div class="oi cr"><div class="otag">🔴 Crítico</div><div class="ott">Apertura baja — revisar listas y segmentación</div><div class="odd">El promedio de ${{fmtP(avgOr)}} está por debajo del estándar. Limpiar lista y segmentar más.</div></div>`:''}
      ${{avgCr<.015?`<div class="oi wa"><div class="otag">🟡 Importante</div><div class="ott">Tasa de clics ${{fmtP(avgCr)}} — por debajo del 1.5% objetivo</div><div class="odd">A/B testear CTAs más específicos y agregar segundo botón en el cuerpo.</div></div>`:''}
      ${{ALL_FLOWS.some(f=>f.conv_rate===0)?`<div class="oi cr"><div class="otag">🔴 Crítico</div><div class="ott">Flujo con 0% conversión detectado</div><div class="odd">Revisar trigger y configuración del flujo. Puede estar mal configurado.</div></div>`:''}
      <div class="oi ok"><div class="otag">🟢 Acción</div><div class="ott">Ejecuta el análisis IA para el plan completo</div><div class="odd">Haz clic en ⚡ Ejecutar optimización para obtener todos los pasos de acción detallados para esta semana y el próximo mes.</div></div>
    </div>`;
}}

// ─── OPTIMIZACIÓN IA ──────────────────────────────────────────────────────
function openOpt(){{
  document.getElementById('m-opt').classList.add('open');
  const camps=fCamps().filter(c=>['Sent','Sending','sent','sending'].includes(c.status));
  const flowRev=ALL_FLOWS.reduce((s,f)=>s+f.conv_value,0);
  const campRev=camps.reduce((s,c)=>s+c.conv_value,0);

  const plan=`⚡ PLAN DE OPTIMIZACIÓN — ${{BRAND_NAME.toUpperCase()}}
Periodo: ${{document.getElementById('dlabel').textContent}}
Generado: ${{GENERATED}}

━━━ DIAGNÓSTICO RÁPIDO ━━━

Revenue email total: ${{fmtU(campRev+flowRev)}}
• Campañas: ${{fmtU(campRev)}} (${{camps.length}} enviadas)
• Flujos: ${{fmtU(flowRev)}} (${{ALL_FLOWS.length}} activos)

Apertura promedio: ${{fmtP(camps.length?camps.reduce((s,c)=>s+c.open_rate,0)/camps.length:0)}}
Clics promedio: ${{fmtP(camps.length?camps.reduce((s,c)=>s+c.click_rate,0)/camps.length:0)}}
Conversión promedio: ${{fmtP(camps.length?camps.reduce((s,c)=>s+c.conv_rate,0)/camps.length:0)}}

${{camps.length?`Mejor campaña: "${{[...camps].sort((a,b)=>b.conv_value-a.conv_value)[0]?.name}}" con ${{fmtU([...camps].sort((a,b)=>b.conv_value-a.conv_value)[0]?.conv_value||0)}}`:'Sin campañas en el periodo'}}

━━━ ACCIONES INMEDIATAS — ESTA SEMANA ━━━

1. SEGMENTACIÓN
   • Revisar los segmentos usados en las últimas 3 campañas
   • Asegurarse de usar solo contactos activos (últimos 60–90 días)
   • Excluir compradores recientes de campañas promocionales
   • Cómo: Klaviyo → Segments → revisar condiciones de cada segmento

2. TASA DE CLICS
   • A/B testear el CTA principal: cambiar de texto genérico a acción específica
   • Ejemplo: "Ver oferta" → "Comprar [producto] con 15% OFF"
   • Agregar un segundo botón a mitad del email
   • Cómo: Klaviyo → Campaigns → New Campaign → A/B Test → Subject/Content

3. FLUJOS ACTIVOS
   • Revisar el flujo con menor conversión
   • Verificar que el trigger esté disparando correctamente
   • Revisar el primer email del Welcome Series (tasa de baja)
   • Cómo: Klaviyo → Flows → seleccionar flujo → Analytics

━━━ ACCIONES PRÓXIMO MES ━━━

1. NUEVO FLUJO — REACTIVACIÓN
   • Crear flujo Win-Back para contactos sin compra en 60+ días
   • Secuencia: reconexión → oferta personalizada → urgencia final
   • Audiencia: compradores activos hace 60–90 días, inactivos desde entonces
   • Impacto esperado: recuperar 5–10% de clientes dormidos

2. CONTENIDO EDUCATIVO
   • Intercalar 1 email educativo por cada 2 promocionales
   • El contenido educativo genera CTR más alto sin descuento
   • Temas: cómo usar el producto, beneficios, ingredientes, rutinas

3. OPTIMIZACIÓN DE DESCUENTOS
   • Probar descuentos intermedios (10–15%) con urgencia real
   • Evitar descuentos agresivos (30%+) que entrenan al cliente a esperar
   • Usar countdown de 48 horas para generar urgencia real

━━━ ASUNTOS RECOMENDADOS ━━━

Basado en patrones de mayor apertura y conversión:
• Usar preguntas directas: "¿Cuándo fue tu último pedido?"
• Personalización con producto: "Tu [producto] te está esperando"
• Urgencia específica: "48 horas para aprovechar tu descuento"
• Evitar: "Oferta especial", "No te pierdas esto", emojis en exceso

━━━ KPIs A MONITOREAR ━━━

• Apertura: objetivo >45% (industria) o mantener nivel actual
• Clics: objetivo 1.5–2.5%
• Conversión: objetivo >0.3% por campaña
• Revenue por recipient (RPR): objetivo >$0.10
• Tasa de baja: mantener <0.2% por envío`;

  optTxt=plan;
  document.getElementById('m-opt-body').textContent=plan;
}}

// ─── FLUJOS ───────────────────────────────────────────────────────────────
function openFlujo(){{
  document.getElementById('m-flu').classList.add('open');
  backF();
  document.getElementById('f-opts').innerHTML=FLUJOS.map(f=>`
    <div class="fsel" onclick="selFlujo('${{f.id}}','${{f.name}}',this)">
      <div class="fsn">${{f.name}}</div>
      <div class="fsd">${{f.desc}}</div>
      <div style="margin-top:6px">${{f.tags.map(t=>`<span class="ftag">${{t}}</span>`).join('')}}</div>
    </div>`).join('');
}}

function selFlujo(id,nombre,el){{
  selFlu=id;
  document.querySelectorAll('.fsel').forEach(f=>f.classList.remove('sel'));
  el.classList.add('sel');
  setTimeout(()=>genFlujo(id,nombre),300);
}}

function genFlujo(id,nombre){{
  document.getElementById('f-opts').style.display='none';
  document.getElementById('f-gen').style.display='flex';
  document.getElementById('f-res').style.display='none';
  document.getElementById('f-back').style.display='none';
  document.getElementById('f-dl').style.display='none';

  const guias={{
    winback:`━━━ PASO A PASO: WIN-BACK EN KLAVIYO ━━━
Flujo: Reactivación de clientes inactivos
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Win-Back — Reactivación [fecha]"
• Trigger: Metric → "Placed Order"

Paso 2: Configurar el filtro de trigger
• En el trigger, agregar condición:
  - "Has not done Placed Order in the last 60 days"
  - Y "Has done Placed Order at least once" (all time)
• Esto asegura que solo entren clientes que SÍ compraron antes pero llevan 60+ días sin comprar

Paso 3: Agregar filtro de flujo (Flow Filter)
• No incluir si ha comprado en los últimos 60 días
• No incluir si ha recibido este flujo en los últimos 90 días

━━ EMAIL 1 — DÍA 0 (RECONEXIÓN) ━━

Asunto A: "Te echamos de menos, {{{{ first_name }}}}"
Asunto B: "¿Cómo va tu [objetivo relacionado al producto]?"
Preheader: "Ha pasado un tiempo desde tu último pedido"
Objetivo: Reconexión emocional. SIN descuento.
Contenido:
  1. Saludo personalizado con nombre
  2. Reconocer que ha pasado tiempo
  3. Recordar el producto que compró (usar variable de Klaviyo)
  4. Pregunta de engagement: "¿Qué tal resultó?"
  5. CTA suave: "Ver mis productos favoritos"
Filtro de exclusión: Compradores en los últimos 30 días

━━ EMAIL 2 — DÍA 5 (OFERTA) ━━

Asunto A: "Tu próximo pedido de [producto] con 15% OFF"
Asunto B: "Exclusivo para ti: 15% en tu reorden"
Preheader: "Código: VUELVE15 — válido por 72 horas"
Objetivo: Conversión con descuento moderado.
Contenido:
  1. Beneficios del producto (recordar por qué lo eligió)
  2. Oferta: 15% OFF con código VUELVE15
  3. Countdown de 72 horas (si usas un bloque de cuenta regresiva)
  4. CTA: "Usar mi descuento ahora"
  5. Testimonios de otros clientes (1-2 reviews)
Filtro de exclusión: Quien ya compró desde Email 1

━━ EMAIL 3 — DÍA 12 (URGENCIA FINAL) ━━

Asunto A: "Última oportunidad — tu descuento vence hoy"
Asunto B: "{{{{ first_name }}}}, tu oferta expira a medianoche"
Preheader: "Solo quedan horas para aprovecharla"
Objetivo: Urgencia máxima para quienes no convirtieron.
Contenido:
  1. Urgencia directa: "Tu descuento vence HOY"
  2. Resumen rápido de la oferta
  3. CTA prominente: "Comprar antes que expire"
  4. Si no convierte → mover a segmento inactivo para no saturar
Filtro de exclusión: Quien ya compró en los últimos 15 días

━━ KPIs ESPERADOS (30 días) ━━
• Email 1: Apertura >45%, Clics >2%
• Email 2: Conversión >3%, Revenue por recipient >$0.50
• Email 3: Conversión >1.5%
• Revenue total del flujo: depende del tamaño del segmento`,

    upsell:`━━━ PASO A PASO: UPSELL POST-COMPRA EN KLAVIYO ━━━
Flujo: Oferta de producto complementario
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Upsell Post-Compra [producto]"
• Trigger: Metric → "Placed Order"

Paso 2: Filtro de trigger
• Agregar condición: el pedido debe contener el producto base
• Excluir si ya compró el producto complementario antes

Paso 3: Timing del primer email
• Delay de 3 días después de la compra
• Permite que el producto llegue antes de recibir el email

━━ EMAIL 1 — DÍA 3 (EDUCATIVO) ━━

Asunto: "Tu pedido llegó — ahora el siguiente nivel"
Preheader: "Descubre cómo potenciar tus resultados"
Objetivo: Educar sobre el complemento. SIN precio agresivo.
Contenido:
  1. Confirmar que el pedido fue recibido
  2. Introducir el producto complementario
  3. Explicar por qué la combinación es superior
  4. Testimonios de clientes que usan ambos
  5. CTA suave: "Descubrir el combo"

━━ EMAIL 2 — DÍA 10 (OFERTA) ━━

Asunto: "¿Ya probaste [complemento]? 10% OFF esta semana"
Preheader: "Porque ya sabes lo que funciona"
Objetivo: Conversión con descuento moderado.
Contenido:
  1. Reforzar los beneficios del combo
  2. Oferta 10% OFF en el complementario
  3. CTA: "Agregar al próximo pedido"

━━ KPIs ESPERADOS ━━
• Email 1: Apertura >40%, Clics >3%
• Email 2: Conversión >2%, AOV incremento >15%`,

    educativo:`━━━ PASO A PASO: FLUJO EDUCATIVO POST-PRIMERA COMPRA ━━━
Flujo: Serie educativa para nuevos clientes
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Educativo — Nuevos Clientes"
• Trigger: Added to List → "Buyers" (lista de compradores)

Paso 2: Filtro
• Solo primera compra (has done Placed Order exactly 1 time)
• Excluir compradores recurrentes

━━ EMAIL 1 — DÍA 7 (GUÍA DE USO) ━━
Asunto: "Cómo usar [producto] para máximos resultados"
Objetivo: Valor puro. Sin venta.
Contenido: Guía de uso, timing, dosis, tips.

━━ EMAIL 2 — DÍA 14 (EDUCATIVO) ━━
Asunto: "La ciencia detrás de [ingrediente/proceso]"
Objetivo: Posicionar a la marca como experta.
Contenido: Artículo educativo sobre el ingrediente clave.

━━ EMAIL 3 — DÍA 21 (RUTINA) ━━
Asunto: "Tu rutina optimizada con [producto]"
Objetivo: Integrar el producto en el hábito del cliente.
Contenido: Plan semanal con el producto como parte central.

━━ EMAIL 4 — DÍA 28 (RECOMPRA) ━━
Asunto: "¿Listo para el siguiente nivel? 10% OFF"
Objetivo: Conversión después de 4 semanas de valor.
CTA: "Hacer mi segundo pedido"

━━ KPIs ESPERADOS ━━
• Tasa de recompra: objetivo >25% en 60 días
• Apertura promedio: >45%
• LTV incremento vs no-flujo: >20%`,

    abandono:`━━━ PASO A PASO: ABANDONO DE CARRITO OPTIMIZADO ━━━
Flujo: Recuperación de carritos abandonados
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Abandono de Carrito — Optimizado"
• Trigger: Metric → "Started Checkout"

Paso 2: Filtro crítico
• Condición: Has NOT done Placed Order in the last 4 hours
• Esto evita enviar el email a quien ya compró

Paso 3: Smart Sending
• Activar Smart Sending para no saturar

━━ EMAIL 1 — 1 HORA (RECORDATORIO) ━━
Asunto: "Olvidaste algo en tu carrito, {{{{ first_name }}}}"
Preheader: "Tu selección te está esperando"
Objetivo: Recordatorio suave. Sin descuento.
Contenido:
  1. Mostrar los productos del carrito (dynamic content)
  2. CTA: "Volver a mi carrito"
  3. Sin urgencia ni descuento — solo recordatorio

━━ EMAIL 2 — 24 HORAS (SOCIAL PROOF) ━━
Asunto: "Miles de clientes ya lo eligieron — ¿y tú?"
Preheader: "Lo que dicen quienes ya compraron"
Objetivo: Superar objeciones con prueba social.
Contenido:
  1. Reviews de los productos del carrito
  2. Garantía o política de devolución
  3. CTA: "Completar mi pedido"

━━ EMAIL 3 — 72 HORAS (OFERTA FINAL) ━━
Asunto: "10% OFF solo por las próximas 24 horas"
Preheader: "Tu carrito + descuento exclusivo"
Objetivo: Urgencia máxima con incentivo.
Contenido:
  1. Código de descuento válido 24h
  2. Productos del carrito visibles
  3. CTA prominente: "Usar mi descuento"
  4. Si no convierte → salir del flujo

━━ KPIs ESPERADOS (30 días) ━━
• Email 1: Recuperación >5% de carritos
• Email 2: Recuperación adicional >3%
• Email 3: Recuperación adicional >2%
• Total: recuperar 10–15% de carritos abandonados`,

    vip:`━━━ PASO A PASO: FLUJO VIP FIDELIZACIÓN ━━━
Flujo: Reconocimiento y beneficios para clientes recurrentes
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "VIP — Fidelización Clientes Recurrentes"
• Trigger: Metric → "Placed Order"
• Filtro trigger: Ha hecho exactamente 3 pedidos (tercera compra)

━━ EMAIL 1 — DÍA 0 (BIENVENIDA VIP) ━━
Asunto: "{{{{ first_name }}}}, eres parte de nuestro círculo VIP"
Preheader: "Gracias por tu tercera compra — tienes beneficios exclusivos"
Objetivo: Reconocimiento y sorpresa positiva.
Contenido:
  1. Anuncio de su nuevo estatus VIP
  2. Beneficios: descuento permanente, acceso anticipado, regalo sorpresa
  3. Sin CTA de compra — este email es de reconocimiento

━━ EMAIL 2 — DÍA 3 (ACCESO ANTICIPADO) ━━
Asunto: "Acceso anticipado: nuevo [producto] antes que nadie"
Preheader: "Solo para clientes VIP — disponible 48h antes"
Objetivo: Hacer sentir exclusividad.
Contenido:
  1. Presentar producto nuevo o temporada
  2. Código de acceso anticipado
  3. CTA: "Ser el primero en probarlo"

━━ EMAIL 3 — DÍA 10 (DESCUENTO EXCLUSIVO) ━━
Asunto: "Tu descuento VIP del mes: 20% en todo"
Preheader: "Exclusivo para ti — válido todo el mes"
Objetivo: Conversión con beneficio exclusivo VIP.
Contenido:
  1. Descuento VIP mensual (mayor que el descuento normal)
  2. Productos recomendados según historial
  3. CTA: "Usar mi descuento VIP"

━━ KPIs ESPERADOS ━━
• Retención de VIPs: >85% compra en los siguientes 60 días
• AOV VIP vs no-VIP: >30% mayor
• LTV VIP: >3x cliente normal`,

    welcome:`━━━ PASO A PASO: WELCOME SERIES EN KLAVIYO ━━━
Flujo: Bienvenida a nuevos suscriptores
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Welcome Series — Nuevos Suscriptores"
• Trigger: Added to List → tu lista principal de suscriptores

Paso 2: Bifurcación cliente vs no-cliente
• Agregar Conditional Split: "Has done Placed Order at least once"
• Rama SÍ → cliente existente (mensaje diferente)
• Rama NO → prospecto (secuencia educativa + primera oferta)

━━ EMAIL 1 — INMEDIATO (BIENVENIDA) ━━
Asunto: "Bienvenido a la familia ${{BRAND_NAME}}"
Preheader: "Esto es lo que debes saber"
Objetivo: Primera impresión. Establecer la voz de la marca.
Contenido:
  1. Historia de la marca en 3 líneas
  2. Qué hace diferente al producto
  3. Qué esperar de los próximos emails
  4. CTA suave: "Descubrir nuestra historia"

━━ EMAIL 2 — DÍA 3 (EDUCATIVO) ━━
Asunto: "¿Sabes qué hace diferente a [producto]?"
Objetivo: Educar y generar deseo.
Contenido: Proceso, ingredientes, origen, diferenciación.

━━ EMAIL 3 — DÍA 7 (PRIMERA OFERTA) ━━
Asunto: "Tu primera compra con 15% OFF"
Objetivo: Conversión con incentivo de bienvenida.
Código: BIENVENIDO15 (válido 7 días)

━━ KPIs ESPERADOS ━━
• Email 1: Apertura >55%, Clics >5%
• Email 3: Conversión >4%
• Tasa de baja total del flujo: <2%`,

    replenishment:`━━━ PASO A PASO: FLUJO DE REABASTECIMIENTO ━━━
Flujo: Recordatorio de reorden basado en consumo
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN EN KLAVIYO ━━

Paso 1: Crear el flujo
• Klaviyo → Flows → Create Flow → Build your own
• Nombre: "Replenishment — Reabastecimiento"
• Trigger: Metric → "Placed Order"

Paso 2: Calcular el tiempo de consumo
• Estimar cuántos días dura el producto según la cantidad comprada
• Para un pack de 30 días → enviar a los 25 días (5 días antes de acabar)

Paso 3: Time Delay
• Agregar delay de [X] días según el producto comprado
• Usar Trigger Split si hay diferentes tamaños/cantidades

━━ EMAIL 1 — DÍA [X-5] (RECORDATORIO SUAVE) ━━
Asunto: "Tu [producto] se está acabando pronto"
Preheader: "Asegura tu próximo pedido antes de quedarte sin"
Objetivo: Recordatorio anticipado sin urgencia.
Contenido:
  1. Aviso amigable de que el producto se acaba
  2. Botón de reorden con 1 clic
  3. Sin descuento — solo conveniencia

━━ EMAIL 2 — DÍA [X] (URGENCIA) ━━
Asunto: "¿Ya te quedaste sin [producto]?"
Preheader: "10% OFF en tu reorden de hoy"
Objetivo: Conversión con incentivo de reorden.
Contenido:
  1. Urgencia de quedarse sin producto
  2. Descuento 10% para reorden inmediato
  3. CTA: "Reordenar ahora"

━━ KPIs ESPERADOS ━━
• Tasa de reorden: objetivo >30%
• Tiempo entre compras: reducir en 20%
• RPR: objetivo >$0.80`,

    bundle:`━━━ PASO A PASO: FLUJO BUNDLE EDUCATION ━━━
Flujo: Educar sobre combinar productos para aumentar ticket
Marca: ${{BRAND_NAME}}

━━ CONFIGURACIÓN ━━
• Trigger: Placed Order de producto A
• Condición: No ha comprado el producto B antes
• Objetivo: Aumentar AOV presentando el combo como superior

━━ EMAIL 1 — DÍA 4 ━━
Asunto: "El combo perfecto para [beneficio]"
Objetivo: Educar sobre la combinación sin vender todavía.
Contenido: Por qué A + B juntos son mejor que cada uno solo.

━━ EMAIL 2 — DÍA 10 ━━
Asunto: "Bundle A + B — ahorra 15% comprando juntos"
Objetivo: Conversión con descuento en el bundle.
CTA: "Comprar el combo"

━━ KPIs ESPERADOS ━━
• Adopción del bundle: >10% de compradores de A
• AOV incremento: >25%`
  }};

  const guia = guias[selFlu] || guias.winback;
  fluTxt = guia;

  setTimeout(()=>{{
    document.getElementById('f-gen').style.display='none';
    document.getElementById('f-res').textContent=fluTxt;
    document.getElementById('f-res').style.display='block';
    document.getElementById('f-back').style.display='inline-flex';
    document.getElementById('f-dl').style.display='inline-flex';
  }}, 800);
}}

function backF(){{
  document.getElementById('f-opts').style.display='block';
  document.getElementById('f-gen').style.display='none';
  document.getElementById('f-res').style.display='none';
  document.getElementById('f-back').style.display='none';
  document.getElementById('f-dl').style.display='none';
  document.querySelectorAll('.fsel').forEach(f=>f.classList.remove('sel'));
  fluTxt='';
}}

function dlTxt(t){{
  const txt=t==='opt'?optTxt:fluTxt;
  if(!txt)return;
  const a=document.createElement('a');
  a.href='data:text/plain;charset=utf-8,'+encodeURIComponent(txt);
  a.download=`${{BRAND_NAME.toLowerCase().replace(' ','_')}}_${{t==='opt'?'optimizacion':'flujo_'+selFlu}}.txt`;
  a.click();
}}

initD();render();
</script>
</body>
</html>"""

    return html


# ─── MAIN ──────────────────────────────────────────────────────────────────
def main():
    output_dir = os.environ.get("OUTPUT_DIR", "dashboards")
    os.makedirs(output_dir, exist_ok=True)

    print("🚀 Rebold Dashboard Generator")
    print(f"📁 Output: {output_dir}/")
    print(f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    for brand_key, brand_config in BRANDS.items():
        try:
            data = fetch_brand_data(brand_config)
            html = generate_html(data)

            output_path = os.path.join(output_dir, brand_config["output_file"])
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"  ✅ {brand_config['name']}: {output_path}")
        except Exception as e:
            print(f"  ❌ Error con {brand_config['name']}: {e}")

    print("\n✅ Todos los dashboards generados.")
    print(f"📂 Archivos en: {output_dir}/")


if __name__ == "__main__":
    main()
