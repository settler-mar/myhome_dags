import os
import json
import subprocess
from datetime import datetime
from shutil import copyfile
from xml.etree import ElementTree as ET

from fastapi import (
  APIRouter, FastAPI, Depends, UploadFile, File, HTTPException, Body
)
from fastapi.responses import JSONResponse, FileResponse, Response
from utils.auth import RoleChecker
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import re

FONT_NAME = "icons"
CODEPOINT_START = 0xE001

GET_router = APIRouter(prefix="/api/fonts", tags=["fonts"])
POST_router = APIRouter(prefix="/api/fonts", tags=["fonts"], dependencies=[Depends(RoleChecker("admin"))])


class IconConfigManager:
  def __init__(self):
    self.folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../store"))
    self.fonts_folder = os.path.join(self.folder, "fonts")
    self.config_path = os.path.join(self.fonts_folder, "config.json")
    self.log_path = os.path.join(self.fonts_folder, "actions.log")
    self.icons_path = os.path.join(self.fonts_folder, "icons")
    self.output_path = os.path.join(self.fonts_folder, "output")
    self.csv_path = os.path.join(self.output_path, "font.csv")
    self.uploaded_font = os.path.join(self.fonts_folder, "uploaded_font.svg")

    os.makedirs(self.icons_path, exist_ok=True)
    os.makedirs(self.output_path, exist_ok=True)

    if not os.path.exists(self.config_path):
      self.generate_default_config()

    if not self.is_font_built():
      self.generate_fonts()

  def generate_default_config(self):
    icons = []
    for f in os.listdir(self.icons_path):
      if f.endswith(".svg"):
        name = os.path.splitext(f)[0]
        icons.append(name)
    with open(self.config_path, "w", encoding="utf-8") as f:
      json.dump({"icons": sorted(icons)}, f, indent=2, ensure_ascii=False)
    self.log("generated default config", {"icons": len(icons)})

  def log(self, action: str, payload: dict = None):
    with open(self.log_path, "a", encoding="utf-8") as f:
      line = f"{datetime.now().isoformat()} - {action}"
      if payload:
        line += f" - {json.dumps(payload, ensure_ascii=False)}"
      f.write(line + "\n")

  def copy_start_config(self):
    copyfile(self.start_path, self.config_path)
    self.log("reset to start")

  def read_config(self):
    with open(self.config_path, encoding="utf-8") as f:
      return json.load(f)

  def update_config(self, data: dict):
    with open(self.config_path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
    self.log("update", data)

  # Извлечение глифов из font_start.svg (если icons папка пуста)
  def extract_glyphs_from_font_start(self):
    tree = ET.parse(self.start_font)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    glyphs = root.findall(".//svg:glyph", ns)
    count = 0
    for glyph in glyphs:
      name = glyph.attrib.get("glyph-name")
      path_data = glyph.attrib.get("d")
      if not name or not path_data:
        continue
      content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 0 0">
  <g transform="scale(1 -1) translate(0 -1000)">
    <path d="{path_data}"/>
  </g>
</svg>'''
      with open(os.path.join(self.icons_path, f"{name}.svg"), "w", encoding="utf-8") as f:
        f.write(content)
      count += 1
    self.log("extract glyphs from font_start.svg", {"count": count})

  # Извлечение глифов из загруженного SVG-шрифта; target_folder — папка, куда сохранять
  def extract_glyphs_from_uploaded_font(self, font_file_path: str, target_folder: str):
    os.makedirs(target_folder, exist_ok=True)
    tree = ET.parse(font_file_path)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    glyphs = root.findall(".//svg:glyph", ns)
    count = 0
    for glyph in glyphs:
      name = glyph.attrib.get("glyph-name")
      path_data = glyph.attrib.get("d")
      if not name or not path_data:
        continue
      content = self._clean_svg_for_font(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
  <g transform="scale(1 -1) translate(0 -1000)">
    <path d="{path_data}"/>
  </g>
</svg>''', calc_viewBox=True, calc_transform=True)

      with open(os.path.join(target_folder, f"{name}.svg"), "w", encoding="utf-8") as f:
        f.write(content.decode("utf-8"))
      count += 1
    self.log("extract glyphs from uploaded font", {"count": count, "target": os.path.basename(target_folder)})

  def _clean_svg_for_font(self, file_stream_or_text, dest_path=None, calc_viewBox=False, calc_transform=False):
    """
    Версия, принимающая файл (file-like) или str (текст SVG).
    При calc_viewBox=True — автоматически рассчитывает viewBox по path-данным с помощью svgpathtools.
    """
    try:
      from io import StringIO
      from svgpathtools import parse_path

      if isinstance(file_stream_or_text, str):
        file_stream = StringIO(file_stream_or_text)
      else:
        file_stream = file_stream_or_text

      ET.register_namespace('', "http://www.w3.org/2000/svg")
      parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
      tree = ET.parse(file_stream, parser=parser)
      root = tree.getroot()

      NS = {'svg': 'http://www.w3.org/2000/svg'}

      # Удаляем мусорные теги
      for tag in ["metadata", "style", "desc", "title"]:
        for el in root.findall(f".//svg:{tag}", NS):
          parent = el.getparent() or root
          parent.remove(el)

      # Очистка атрибутов
      def recursive_clean(elem):
        for attr in list(elem.attrib):
          if attr.startswith("id") or attr.startswith("class") or attr.startswith("data-") or \
              attr in {"style", "font-family", "font-weight", "font-style", "opacity"}:
            del elem.attrib[attr]
        for child in elem:
          recursive_clean(child)

      recursive_clean(root)

      # ===== Коррекция viewBox по содержимому path =====
      if calc_viewBox:
        xmin, ymin, xmax, ymax = None, None, None, None
        for path in root.findall(".//svg:path", NS):
          d = path.attrib.get("d")
          if not d:
            continue
          try:
            p = parse_path(d)
            pxmin, pxmax, pymin, pymax = p.bbox()
            if xmin is None:
              xmin, xmax, ymin, ymax = pxmin, pxmax, pymin, pymax
            else:
              xmin = min(xmin, pxmin)
              xmax = max(xmax, pxmax)
              ymin = min(ymin, pymin)
              ymax = max(ymax, pymax)
          except Exception:
            continue

        if None not in (xmin, xmax, ymin, ymax):
          width = xmax - xmin
          height = ymax - ymin
          xmin, ymin, xmax, ymax = int(xmin), int(ymin), int(width), int(height)
        else:
          xmin, ymin, xmax, ymax = 0, 0, 1000, 1000

        viewBox = root.attrib.get("viewBox")
        if not viewBox or viewBox.strip() == "0 0 0 0":
          root.attrib["viewBox"] = f"{xmin} {ymin} {xmax} {ymax}"
        else:
          # Если viewBox уже задан, то не перезаписываем его то считаем какое отклонение от полученных значений
          vb_xmin, vb_ymin, vb_width, vb_height = map(int, viewBox.split())
          k_height = vb_height / ymax
          k_width = vb_width / xmax
          if abs(1 - k_height) > 0.15 or abs(1 - k_width) > 0.15:
            root.attrib["viewBox"] = f"{xmin} {ymin} {xmax} {ymax}"

      # ===== Коррекция transform =====
      if calc_transform:
        viewBox = root.attrib.get("viewBox", "0 0 1000 1000")
        try:
          _, pos_x_val, _, height_val = map(int, viewBox.split())
        except:
          height_val = 1000
          pos_x_val = 0
        for g in root.findall(".//svg:g", NS):
          t = g.attrib.get("transform")
          if t:
            g.attrib["transform"] = f"scale(1 -1) translate(0 -{height_val + pos_x_val * 2})"

      if dest_path:
        ET.ElementTree(root).write(dest_path, encoding="utf-8", xml_declaration=True, default_namespace=None)
      else:
        output = ET.tostring(root, encoding="utf-8", method="xml")
        return output

    except Exception as e:
      raise HTTPException(status_code=400, detail=f"Invalid SVG: {e}")

  def _human_size(self, size_bytes):
    if size_bytes < 1024:
      return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
      return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
      return f"{size_bytes / (1024 ** 2):.1f} MB"
    return f"{size_bytes / (1024 ** 3):.1f} GB"

  def save_uploaded_svg(self, file: UploadFile):

    original_name = file.filename
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in [".svg", '.woff', '.woff2']:
      raise HTTPException(status_code=400, detail="Invalid file type. Only SVG, WOFF, WOFF2 are allowed.")
    base_name = os.path.splitext(original_name)[0]

    if ext in {".woff", ".woff2"}:
      target_folder = os.path.join(self.icons_path, base_name)
      os.makedirs(target_folder, exist_ok=True)

      tmp_path = os.path.join(self.fonts_folder, f"uploaded_font{ext}")
      with open(tmp_path, "wb") as f:
        f.write(file.file.read())

      try:
        font = TTFont(tmp_path)
        glyph_set = font.getGlyphSet()
        cmap = font.getBestCmap()
        written = 0

        for codepoint, glyph_name in cmap.items():
          if glyph_name not in glyph_set:
            continue

          pen = SVGPathPen(glyph_set)
          glyph_set[glyph_name].draw(pen)
          svg_path = pen.getCommands()
          if not svg_path.strip():
            continue

          # Очистка имени
          safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', glyph_name.lower())
          if not safe_name:
            safe_name = f"glyph_{codepoint:04x}"

          svg_content = self._clean_svg_for_font(f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 0 0">
      <g transform="scale(1 -1) translate(0 -1000)">
        <path d="{svg_path}"/>
      </g>
    </svg>""", calc_viewBox=True, calc_transform=True)

          out_path = os.path.join(target_folder, f"{safe_name}.svg")
          with open(out_path, "w", encoding="utf-8") as out:
            out.write(svg_content.decode("utf-8"))

          written += 1

      except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse font: {e}")

      self.log("upload woff", {"filename": original_name, "folder": base_name})
      return {
        "uploaded": original_name,
        "folder": base_name,
        "mode": "woff",
        "count": written,
        "size": self._human_size(os.path.getsize(tmp_path))
      }

    first_bytes = file.file.read(1024).decode(errors="ignore")
    file.file.seek(0)

    # SVG-шрифт — содержит <font> или <glyph>
    if "<font" in first_bytes or "<glyph" in first_bytes:
      target_folder = os.path.join(self.icons_path, base_name)
      os.makedirs(target_folder, exist_ok=True)
      dest_path = os.path.join(self.fonts_folder, "uploaded_font.svg")
      with open(dest_path, "wb") as f:
        f.write(file.file.read())

      self.extract_glyphs_from_uploaded_font(dest_path, target_folder)
      file_count = len([f for f in os.listdir(target_folder) if f.endswith(".svg")])
      size = os.path.getsize(dest_path)

      self.log("upload font", {"filename": original_name, "folder": base_name})

      return {
        "uploaded": original_name,
        "folder": base_name,
        "mode": "font",
        "count": file_count,
        "size": self._human_size(size)
      }

    # Одиночная иконка → custom
    custom_path = os.path.join(self.icons_path, "custom")
    os.makedirs(custom_path, exist_ok=True)

    dest_path = os.path.join(custom_path, original_name)
    if os.path.exists(dest_path):
      base, ext = os.path.splitext(original_name)
      i = 1
      while True:
        new_name = f"{base}_{i}{ext}"
        dest_path = os.path.join(custom_path, new_name)
        if not os.path.exists(dest_path):
          break
        i += 1
      final_name = new_name
    else:
      final_name = original_name

    file.file.seek(0)
    self._clean_svg_for_font(file.file, dest_path)

    size = os.path.getsize(dest_path)
    self.log("upload svg", {"original": original_name, "saved_as": final_name})

    return {
      "uploaded": original_name,
      "saved_as": final_name,
      "folder": "custom",
      "mode": "single",
      "size": self._human_size(size)
    }

  def rename_icon(self, old_name: str, new_name: str):
    old_path = os.path.join(self.icons_path, old_name)
    new_path = os.path.join(self.icons_path, new_name)

    if not os.path.exists(old_path):
      raise HTTPException(status_code=404, detail="Original icon not found")
    if os.path.exists(new_path):
      raise HTTPException(status_code=400, detail="Target name already exists")

    os.rename(old_path, new_path)
    self.log("rename svg", {"from": old_name, "to": new_name})
    return {"from": old_name, "to": new_name}

  def generate_fonts(self):
    script = f'''
import fontforge
import os
icons_path = r"{self.icons_path}"
output_path = r"{self.output_path}"
csv_path = r"{self.csv_path}"

font = fontforge.font()
font.encoding = "UnicodeFull"
font.fontname = "{FONT_NAME}"
font.fullname = "{FONT_NAME}"
font.familyname = "{FONT_NAME}"

codepoint = {CODEPOINT_START}
mappings = []

# Итерируем по всем одиночным иконкам в папке icons (не рекурсивно)
for filename in sorted(os.listdir(icons_path)):
    if not filename.lower().endswith(".svg"):
        continue
    name = os.path.splitext(filename)[0]
    path = os.path.join(icons_path, filename)
    glyph = font.createChar(codepoint, name)
    glyph.importOutlines(path)
    glyph.width = 1000
    mappings.append((codepoint, name))
    codepoint += 1

font.generate(os.path.join(output_path, "{FONT_NAME}.ttf"))
font.generate(os.path.join(output_path, "{FONT_NAME}.woff"))
font.generate(os.path.join(output_path, "{FONT_NAME}.woff2"))
font.generate(os.path.join(output_path, "{FONT_NAME}.eot"))
font.generate(os.path.join(output_path, "{FONT_NAME}.svg"))

with open(csv_path, "w", encoding="utf-8") as f:
    f.write("codepoint,name,unicode\\n")
    for code, name in mappings:
        f.write(f"{{code}},{{name}},\\\\u{{code:04x}}\\n")
'''
    process = subprocess.Popen(
      ["fontforge", "-script", "/dev/stdin"],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True
    )
    stdout, stderr = process.communicate(script)
    if process.returncode != 0:
      raise HTTPException(status_code=500, detail=stderr)
    self.log("generate fonts")

  def is_font_built(self):
    required = ["icons.ttf", "icons.woff", "icons.woff2"]
    return all(os.path.exists(os.path.join(self.output_path, f)) for f in required)

  def get_icon_list(self, filepath: str):
    # Получаем список файлов иконок в папке icons + вложенные папки
    files = []
    for root, _, filenames in os.walk(filepath):
      for filename in filenames:
        if filename.lower().endswith(".svg"):
          files.append(os.path.relpath(os.path.join(root, filename), filepath))
    return sorted(files)

  # Работа с файлами иконок (одиночные)
  def list_icons(self):
    # Получаем список файлов иконок в папке icons + вложенные папки
    return self.get_icon_list(self.icons_path)

  def delete_icon(self, filepath: str):
    # filepath может содержать подпапку, например "example/alarm.svg"
    full_path = os.path.join(self.icons_path, filepath)
    if not os.path.exists(full_path):
      raise HTTPException(status_code=404, detail="File not found")
    os.remove(full_path)
    self.log("delete svg", {"filepath": filepath})
    return filepath

  def get_icon_path(self, filepath: str):
    full_path = os.path.join(self.icons_path, filepath)
    if not os.path.exists(full_path):
      raise HTTPException(status_code=404, detail="File not found")
    return full_path

  # Работа с шрифтом (сгенерированными файлами)
  def get_font_path(self, ext: str):
    path = os.path.join(self.output_path, f"icons.{ext}")
    if not os.path.exists(path):
      print(f"Font file not found: {path}")
      raise HTTPException(status_code=404, detail="Font not generated")
    return path

  def get_csv_path(self):
    if not os.path.exists(self.csv_path):
      raise HTTPException(status_code=404, detail="CSV not found")
    return self.csv_path


manager = IconConfigManager()


# ---------------------- ROUTES ----------------------


# Получение списка иконок (одиночные файлы) – можно расширить для рекурсии
@GET_router.get("/icons")
def list_icons():
  return manager.list_icons()


# Получение объединённого списка иконок с метаданными из config
@GET_router.get("/icons/with-meta")
def icons_with_meta():
  # Предполагаем, что config.json содержит ключ "icons" со списком имен
  config_data = manager.read_config()
  defined = set(config_data.get("icons", [])) if isinstance(config_data, dict) else set()
  folder_icons = set(manager.list_icons())
  # Если в папке есть подпапки — можно добавить их файлы (в виде "subdir/filename.svg")
  for entry in os.listdir(manager.icons_path):
    full = os.path.join(manager.icons_path, entry)
    if os.path.isdir(full):
      files = [f"{entry}/{f}" for f in os.listdir(full) if f.lower().endswith(".svg")]
      folder_icons.update(files)
  merged = []
  all_names = defined.union({os.path.splitext(name)[0] for name in folder_icons})
  for name in sorted(all_names):
    merged.append({
      "name": name.split('/')[-1],
      'folder': name.split('/')[0] if '/' in name else None,
      "defined": name in defined,
      "exists": any(name == os.path.splitext(f)[0] for f in folder_icons),
    })
  return merged


@GET_router.get("/icons/{filename:path}")
def get_icon(filename: str):
  path = os.path.join(manager.icons_path, filename)
  if not os.path.exists(path):
    raise HTTPException(status_code=404, detail="Icon not found")
  return FileResponse(path, media_type="image/svg+xml")


@GET_router.get("/font.csv")
def get_csv():
  return FileResponse(manager.get_csv_path(), media_type="text/csv")


@GET_router.get("/font.{ext}")
def get_font(ext: str):
  return FileResponse(manager.get_font_path(ext), media_type="application/octet-stream")


@GET_router.get("/style.css")
def get_font_css():
  css = f"""
@font-face {{
  font-family: '{FONT_NAME}';
  src: url('/api/fonts/font.woff2') format('woff2'),
       url('/api/fonts/font.woff') format('woff');
  font-weight: normal;
  font-style: normal;
}}
[class^='icon-'], [class*=' icon-'] {{
  font-family: '{FONT_NAME}' !important;
  speak: none;
  font-style: normal;
  font-weight: normal;
  font-variant: normal;
  text-transform: none;
  line-height: 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}
"""

  csv_path = manager.get_csv_path()
  if os.path.exists(csv_path):
    with open(csv_path, encoding="utf-8") as f:
      for line in f:
        if line.startswith("codepoint"):
          continue
        parts = line.strip().split(',')
        if len(parts) >= 3:
          _, name, unicode_val = parts
          # преобразуем '\\uXXXX' → '\\eXXX' без двойного экранирования
          unicode_hex = unicode_val.replace("\\ue", "\\e")
          css += f".icon-{name}::before {{ content: '{unicode_hex}'; }}\n"

  return Response(content=css, media_type="text/css")


# === POST/DELETE (только admin) ===
# Удаление иконки
@POST_router.delete("/icons/{filepath:path}")
def delete_icon(filepath: str):
  deleted = manager.delete_icon(filepath)
  return {"status": "deleted", "filepath": deleted}


@POST_router.post("/upload")
def upload_icon(file: UploadFile = File(...)):
  return {"status": "ok", "filename": manager.save_uploaded_svg(file)}


@POST_router.get("/config")
def get_config():
  return manager.read_config()


@POST_router.post("/config")
def update_config(data: dict = Body(...)):
  manager.update_config(data)
  manager.generate_fonts()
  return {"status": "ok"}


@POST_router.post("/reset")
def reset_config():
  manager.copy_start_config()
  return {"status": "reset"}


@POST_router.post("/generate")
def generate_font():
  manager.generate_fonts()
  return {"status": "generated"}


@POST_router.post("/icons/edit")
def edit_icon(filepath: str = Body(...), rotate: float = Body(0), flip: str = Body(None)):
  path = manager.get_icon_path(filepath)
  tree = ET.parse(path)
  root = tree.getroot()
  g = root.find(".//{http://www.w3.org/2000/svg}g")
  if g is None:
    raise HTTPException(status_code=400, detail="No <g> element")
  transforms = [g.attrib.get("transform", "")] if g.attrib.get("transform") else []
  if rotate:
    transforms.append(f"rotate({rotate},500,500)")
  if flip == "horizontal":
    transforms.append("scale(-1,1) translate(-1000,0)")
  elif flip == "vertical":
    transforms.append("scale(1,-1) translate(0,-1000)")
  g.attrib["transform"] = " ".join(transforms)
  tree.write(path, encoding="utf-8")
  return {"status": "edited", "filepath": filepath}


@POST_router.post("/icons/rename")
def rename_icon(data: dict = Body(...)):
  return manager.rename_icon(data["old_name"], data["new_name"])


# === Подключение роутеров ===
def add_route(app: FastAPI):
  app.include_router(GET_router)
  app.include_router(POST_router)
