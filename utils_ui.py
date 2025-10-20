from pathlib import Path
import io
import base64
import streamlit as st
from typing import Optional
from PIL import Image, UnidentifiedImageError

def _open_raster_image(path: Path):
    try:
        with path.open('rb') as f:
            data = f.read()
        img = Image.open(io.BytesIO(data))
        img.load()
        return img
    except (FileNotFoundError, UnidentifiedImageError, OSError):
        return None

def _is_svg(path: Path) -> bool:
    return path.suffix.lower() == ".svg"

def _render_svg_from_path(path: Path, width: int):
    try:
        svg_text = path.read_text(encoding="utf-8")
        data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
        html = f"<img src='{data_uri}' style='width:{width}px;height:auto;'/>"
        st.markdown(html, unsafe_allow_html=True)
        return True
    except Exception:
        return False

def _render_svg_from_bytes(raw: bytes, width: int):
    try:
        data_uri = "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")
        html = f"<img src='{data_uri}' style='width:{width}px;height:auto;'/>"
        st.markdown(html, unsafe_allow_html=True)
        return True
    except Exception:
        return False

def _candidates(base: Path, src: Optional[str]):
    prefer = []
    if src:
        p = Path(src)
        prefer = [p, base / p.name, (base / "assets" / p.name), Path.cwd() / p.name]
    default = [
        base / "start.svg", base / "START.svg", base / "assets" / "start.svg", base / "assets" / "START.svg", Path.cwd() / "start.svg", Path.cwd() / "START.svg",
        base / "logo.svg", base / "assets" / "logo.svg", Path.cwd() / "logo.svg",
        base / "start.png", base / "START.png", base / "assets" / "start.png", base / "assets" / "START.png", Path.cwd() / "start.png", Path.cwd() / "START.png",
        base / "logo.png", base / "assets" / "logo.png", Path.cwd() / "logo.png",
        base / "start.jpg", base / "start.jpeg", Path.cwd() / "start.jpg", Path.cwd() / "start.jpeg",
    ]
    seen = set()
    out = []
    for x in prefer + default:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def show_logo(src: Optional[str] = None, width: int = 160):
    """Exibe um logo priorizando SVG; aceita também PNG/JPG.
    - src (opcional): nome/caminho sugerido (ex.: "start.png" ou "assets/logo.svg").
    - width: largura desejada em pixels.
    Compatível com chamadas antigas: show_logo(160) ou show_logo(width=160).
    """
    if isinstance(src, (int, float)) and width == 160:
        width = int(src)
        src = None

    base = Path(__file__).parent
    for p in _candidates(base, src):
        if p.exists():
            if _is_svg(p):
                if _render_svg_from_path(p, width):
                    return
            else:
                img = _open_raster_image(p)
                if img is not None:
                    st.image(img, width=width)
                    return

    st.info("Logo não encontrado ou inválido. Envie um SVG/PNG/JPG abaixo para usarmos nesta sessão.")
    uploaded = st.file_uploader("Enviar logo (SVG/PNG/JPG)", type=["svg", "png", "jpg", "jpeg"], key="logo_upload")
    if uploaded is not None:
        filename = uploaded.name.lower()
        data = uploaded.read()
        assets = base / "assets"
        assets.mkdir(exist_ok=True)
        if filename.endswith('.svg') or uploaded.type == 'image/svg+xml':
            out = assets / "logo.svg"
            out.write_bytes(data)
            if _render_svg_from_bytes(data, width):
                st.success(f"Logo SVG salvo em {out.name}.")
                return
            st.error("SVG inválido.")
        else:
            try:
                img = Image.open(io.BytesIO(data))
                img.load()
                out = assets / "logo.png"
                img.save(out, format="PNG")
                st.success(f"Logo salvo em {out.name}.")
                st.image(img, width=width)
                return
            except UnidentifiedImageError:
                st.error("Arquivo enviado não é uma imagem válida (PNG/JPG/SVG).")
