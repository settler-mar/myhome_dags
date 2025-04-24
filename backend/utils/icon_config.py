import os
import json
import subprocess
from datetime import datetime
from shutil import copyfile
from xml.etree import ElementTree as ET
from utils.configs import config
from svgpathtools import parse_path, svg2paths
import tempfile
import textwrap

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
    self.icons_path = os.path.join(self.fonts_folder, "icons")
    self.config_csv_path = os.path.join(self.fonts_folder, "config.csv")
    self.config_csv_base = os.path.join(self.fonts_folder, "config_base.csv")
    self.log_path = os.path.join(self.fonts_folder, "actions.log")
    self.output_path = os.path.join(self.fonts_folder, "output")
    self.csv_path = os.path.join(self.output_path, "font.csv")
    self.uploaded_font = os.path.join(self.fonts_folder, "uploaded_font.svg")

    os.makedirs(self.fonts_folder, exist_ok=True)
    os.makedirs(self.output_path, exist_ok=True)

    if not os.path.exists(self.config_csv_path):
      if os.path.exists(self.config_csv_base):
        copyfile(self.config_csv_base, self.config_csv_path)
        self.log("copy config from base")
      else:
        with open(self.config_csv_path, "w", encoding="utf-8") as f:
          f.write("name,folder\n")
        self.log("create empty config")

  def log(self, action: str, payload: dict = None):
    with open(self.log_path, "a", encoding="utf-8") as f:
      line = f"{datetime.now().isoformat()} - {action}"
      if payload:
        line += f" - {json.dumps(payload, ensure_ascii=False)}"
      f.write(line + "\n")

  def read_config_csv(self):
    import csv
    result = []
    if not os.path.exists(self.config_csv_path):
      return []
    with open(self.config_csv_path, encoding="utf-8") as f:
      reader = csv.DictReader(f)
      for row in reader:
        result.append(row)
    return result

  def write_config_csv(self, data):
    import csv
    if 'icons' in data:
      data = data['icons']
    for row in data:
      if "folder" not in row or "name" not in row:
        raise HTTPException(status_code=500, detail="Invalid data format")
    with open(self.config_csv_path, "w", encoding="utf-8", newline='') as f:
      writer = csv.DictWriter(f, fieldnames=["name", "folder"])
      writer.writeheader()
      writer.writerows(data)
    self.log("update config.csv", {"count": len(data)})

  def get_font_name(self):
    csv_file = os.path.basename(self.config_csv_path)
    name = os.path.splitext(csv_file)[0]
    return name

  def get_font_path(self, ext: str):
    filename = f"{self.get_font_name()}.{ext}"
    path = os.path.join(self.output_path, filename)
    if not os.path.exists(path):
      raise HTTPException(status_code=404, detail="Font not generated")
    return path

  def get_css(self):
    font_name = self.get_font_name()
    ts = int(os.path.getmtime(self.get_font_path("woff2")))  # timestamp для обновления кеша
    css = f"""
@font-face {{
  font-family: '{font_name}';
  src: url('/api/fonts/font.woff2?t={ts}') format('woff2'),
       url('/api/fonts/font.woff?t={ts}') format('woff');
  font-weight: normal;
  font-style: normal;
}}
[class^='icon-'], [class*=' icon-'] {{
  font-family: '{font_name}' !important;
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
    if os.path.exists(self.csv_path):
      with open(self.csv_path, encoding="utf-8") as f:
        for line in f:
          if line.startswith("codepoint"):
            continue
          parts = line.strip().split(',')
          if len(parts) >= 3:
            _, name, unicode_val = parts
            unicode_hex = unicode_val.replace("\\ue", "\\e")
            css += f".icon-{name}::before {{ content: '{unicode_hex}'; }}\n"

    return css

  def generate_fonts(self):
    import shutil
    from xml.etree import ElementTree as ET

    config = self.read_config_csv()
    font_name = self.get_font_name()

    tmp_svg_dir = tempfile.mkdtemp()
    print(f"Temporary SVG directory: {tmp_svg_dir}")

    def normalize_svg_path(input_path, output_path):
      paths, attributes = svg2paths(input_path)
      if not paths:
        return False

      try:
        # Получаем bbox всех path'ов
        xmin, xmax, ymin, ymax = None, None, None, None
        for path in paths:
          pxmin, pxmax, pymin, pymax = path.bbox()
          if xmin is None:
            xmin, xmax, ymin, ymax = pxmin, pxmax, pymin, pymax
          else:
            xmin = min(xmin, pxmin)
            xmax = max(xmax, pxmax)
            ymin = min(ymin, pymin)
            ymax = max(ymax, pymax)

        width = xmax - xmin
        height = ymax - ymin

        # Центрирование по оси X
        shift_x = -xmin
        shift_y = -ymin

        # Преобразуем все path'ы
        d = ""
        for path in paths:
          path = path.translated(complex(shift_x, shift_y))
          d += path.d()

        svg_elem = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                              viewBox=f"0 0 {int(width)} {int(height)}")
        g_elem = ET.SubElement(svg_elem, "g", transform=f"scale(1 -1) translate(0 -{int(height)})")
        ET.SubElement(g_elem, "path", d=d)

        tree = ET.ElementTree(svg_elem)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return True
      except Exception as e:
        print(f"Failed to normalize {input_path}: {e}")
        return False

    mappings = []
    codepoint = CODEPOINT_START

    for row in config:
      name = row['name']
      folder = row['folder']
      src_path = os.path.join(self.icons_path, folder, f"{name}.svg")
      dst_path = os.path.join(tmp_svg_dir, f"{name}.svg")
      if not os.path.exists(src_path):
        continue
      if not normalize_svg_path(src_path, dst_path):
        continue
      mappings.append((codepoint, name, dst_path))
      codepoint += 1

    # Генерация fontforge-скрипта
    script = textwrap.dedent(f'''
        import fontforge
        import os

        font = fontforge.font()
        font.encoding = "UnicodeFull"
        font.fontname = "{font_name}"
        font.fullname = "{font_name}"
        font.familyname = "{font_name}"

        codepoint = {CODEPOINT_START}
        icons_dir = r"{tmp_svg_dir}"

        mappings = {[(cp, name) for cp, name, _ in mappings]}

        for code, name in mappings:
            path = os.path.join(icons_dir, name + ".svg")
            if not os.path.exists(path):
                continue
            glyph = font.createChar(code, name)
            glyph.importOutlines(path, ('removeoverlap', 'correctdir'))
            glyph.width = 1000

        output_path = r"{self.output_path}"
        font.generate(os.path.join(output_path, "{font_name}.ttf"))
        font.generate(os.path.join(output_path, "{font_name}.woff"))
        font.generate(os.path.join(output_path, "{font_name}.woff2"))
        font.generate(os.path.join(output_path, "{font_name}.eot"))
        font.generate(os.path.join(output_path, "{font_name}.svg"))

        with open(r"{self.csv_path}", "w", encoding="utf-8") as f:
            f.write("codepoint,name,unicode\\n")
            for code, name in mappings:
                f.write(f"{{code}},{{name}},\\\\u{{code:04x}}\\n")
    ''')

    process = subprocess.Popen(
      ["fontforge", "-script", "/dev/stdin"],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True
    )
    stdout, stderr = process.communicate(script)
    shutil.rmtree(tmp_svg_dir)

    if process.returncode != 0:
      raise HTTPException(status_code=500, detail=f"FontForge error:\n{stderr}")

    self.log("generate fonts")

  def get_icon_list(self):
    result = []
    root_path = self.icons_path
    for folder in os.listdir(root_path):
      folder_path = os.path.join(root_path, folder)
      if not os.path.isdir(folder_path):
        continue
      for file in os.listdir(folder_path):
        if file.lower().endswith(".svg"):
          name = os.path.splitext(file)[0]
          result.append({
            "name": name,
            "folder": folder,
            # "path": os.path.join(folder_path, file)
          })
    return result

  def list_icons(self):
    return self.get_icon_list()

  def get_icon_path(self, name: str, folder: str):
    if name.lower().endswith('.svg'):
      name = name[:-4]
    full_path = os.path.join(self.fonts_folder, "icons", folder, name + ".svg")
    if not os.path.exists(full_path):
      raise HTTPException(status_code=404, detail="File not found")
    return full_path

  def delete_icon(self, name: str, folder: str):
    path = self.get_icon_path(name, folder)
    os.remove(path)
    self.log("delete svg", {"folder": folder, "name": name})

    config = self.read_config_csv()
    new_config = [row for row in config if not (row['name'] == name and row['folder'] == folder)]
    if len(new_config) != len(config):
      self.write_config_csv(new_config)

    return path

  def rename_icon(self, old_name: str, new_name: str, folder: str):
    base = os.path.join(self.fonts_folder, "icons", folder)
    if old_name.lower().endswith('.svg'):
      old_name = old_name[:-4]
    if new_name.lower().endswith('.svg'):
      new_name = new_name[:-4]
    old_path = os.path.join(base, old_name + ".svg")
    new_path = os.path.join(base, new_name + ".svg")

    if not os.path.exists(old_path):
      raise HTTPException(status_code=404, detail="Original icon not found")
    if os.path.exists(new_path):
      raise HTTPException(status_code=400, detail="Target name already exists")

    os.rename(old_path, new_path)
    self.log("rename svg", {"folder": folder, "from": old_name, "to": new_name})

    config = self.read_config_csv()
    updated = False
    for row in config:
      if row['name'] == old_name and row['folder'] == folder:
        row['name'] = new_name
        updated = True
    if updated:
      self.write_config_csv(config)

    return {"from": old_name, "to": new_name, "folder": folder, "updated": updated}

  def _human_size(self, size_bytes):
    if size_bytes < 1024:
      return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
      return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
      return f"{size_bytes / (1024 ** 2):.1f} MB"
    return f"{size_bytes / (1024 ** 3):.1f} GB"

  def _clean_svg_for_font(self, file_stream_or_text, dest_path=None, calc_viewBox=False, calc_transform=False):
    from io import StringIO

    if isinstance(file_stream_or_text, str):
      file_stream = StringIO(file_stream_or_text)
    else:
      file_stream = file_stream_or_text

    ET.register_namespace('', "http://www.w3.org/2000/svg")
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(file_stream, parser=parser)
    root = tree.getroot()
    NS = {'svg': 'http://www.w3.org/2000/svg'}

    for tag in ["metadata", "style", "desc", "title"]:
      for el in root.findall(f".//svg:{tag}", NS):
        parent = el.getparent() or root
        parent.remove(el)

    def recursive_clean(elem):
      for attr in list(elem.attrib):
        if attr.startswith("id") or attr.startswith("class") or attr.startswith("data-") or \
            attr in {"style", "font-family", "font-weight", "font-style", "opacity"}:
          del elem.attrib[attr]
      for child in elem:
        recursive_clean(child)

    recursive_clean(root)

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
        vb_xmin, vb_ymin, vb_width, vb_height = map(int, viewBox.split())
        k_height = vb_height / ymax if ymax else 1
        k_width = vb_width / xmax if xmax else 1
        if abs(1 - k_height) > 0.15 or abs(1 - k_width) > 0.15:
          root.attrib["viewBox"] = f"{xmin} {ymin} {xmax} {ymax}"
    if calc_transform:
      viewBox = root.attrib.get("viewBox", "0 0 1000 1000")
      try:
        _, pos_y, _, height_val = map(int, viewBox.strip().split())
      except:
        height_val = 1000
        pos_y = 0
      for g in root.findall(".//svg:g", NS):
        t = g.attrib.get("transform")
        if t:
          g.attrib["transform"] = f"scale(1 -1) translate(0 -{height_val + pos_y * 2})"

    if dest_path:
      ET.ElementTree(root).write(dest_path, encoding="utf-8", xml_declaration=True, default_namespace=None)
    else:
      return ET.tostring(root, encoding="utf-8", method="xml")

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

  def save_uploaded_svg(self, file: UploadFile):
    original_name = file.filename
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in [".svg", ".woff", ".woff2"]:
      raise HTTPException(status_code=400, detail="Invalid file type. Only SVG, WOFF, WOFF2 are allowed.")
    base_name = os.path.splitext(original_name)[0]

    if ext in {".woff", ".woff2"}:
      target_folder = os.path.join(self.fonts_folder, "icons", base_name)
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

          safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', glyph_name.lower()) or f"glyph_{codepoint:04x}"

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
    # Проверка на SVG-шрифт
    first_bytes = file.file.read(1024).decode(errors="ignore")
    file.file.seek(0)

    if "<font" in first_bytes or "<glyph" in first_bytes:
      target_folder = os.path.join(self.fonts_folder, "icons", base_name)
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
    custom_folder = "custom"
    target_folder = os.path.join(self.fonts_folder, "icons", custom_folder)
    os.makedirs(target_folder, exist_ok=True)

    dest_path = os.path.join(target_folder, original_name)
    if os.path.exists(dest_path):
      base, ext = os.path.splitext(original_name)
      i = 1
      while True:
        new_name = f"{base}_{i}{ext}"
        dest_path = os.path.join(target_folder, new_name)
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
      "folder": custom_folder,
      "mode": "single",
      "size": self._human_size(size)
    }

  def auto_add_icons_from_names(self, icon_names: list[str]) -> int:
    if not config.get("auto_icon_finder", True):
      return 0

    config_data = self.read_config_csv()
    existing = set((row["folder"], row["name"]) for row in config_data)
    to_add = []

    for full_name in icon_names:
      if '/' in full_name:
        folder, name = full_name.split('/', 1)
        path = os.path.join(self.icons_path, folder, f"{name}.svg")
        if os.path.exists(path):
          key = (folder, name)
          if key not in existing:
            to_add.append({"folder": folder, "name": name})
            existing.add(key)
        continue

      # Поиск по всем папкам
      for root, _, files in os.walk(self.icons_path):
        for file in files:
          if not file.lower().endswith(".svg"):
            continue
          fname = os.path.splitext(file)[0]
          if fname != full_name:
            continue
          folder = os.path.relpath(root, self.icons_path)
          key = (folder, fname)
          if key not in existing:
            to_add.append({"folder": folder, "name": fname})
            existing.add(key)
          break
        else:
          continue
        break

    self.log('auto add icons', {
      "count": len(to_add),
      "icons": [f"{row['folder']}/{row['name']}" for row in to_add]
    })

    if to_add:
      config_data.extend(to_add)
      self.write_config_csv(config_data)
      self.generate_fonts()
      return len(to_add)

    return 0


manager = IconConfigManager()


@GET_router.get("/icons")
def list_icons():
  return manager.list_icons()


@GET_router.get("/icons/with-meta")
def icons_with_meta():
  config_data = manager.read_config_csv()
  config_set = set((row['name'], row['folder']) for row in config_data if 'name' in row and 'folder' in row)

  actual_icons = manager.get_icon_list()
  icon_set = set((i['name'], i['folder']) for i in actual_icons)

  all_keys = config_set.union(icon_set)

  merged = []
  for name, folder in sorted(all_keys):
    merged.append({
      "name": name,
      "folder": folder,
      "defined": (name, folder) in config_set,
      "exists": (name, folder) in icon_set
    })
  return merged


@GET_router.get("/icons/{folder}/{name}")
def get_icon(folder: str, name: str):
  path = manager.get_icon_path(name, folder)
  return FileResponse(path, media_type="image/svg+xml")


@GET_router.get("/font.{ext}")
def get_font(ext: str):
  return FileResponse(manager.get_font_path(ext), media_type="application/octet-stream")


@GET_router.get("/style.css")
def get_font_css():
  return Response(content=manager.get_css(), media_type="text/css")


@POST_router.post("/upload")
def upload_icon(file: UploadFile = File(...)):
  return {"status": "ok", **manager.save_uploaded_svg(file)}


@POST_router.post("/generate")
def generate_font():
  manager.generate_fonts()
  return {"status": "generated"}


@POST_router.post("/icons/edit")
def edit_icon(filepath: str = Body(...), rotate: float = Body(0), flip: str = Body(None)):
  path = os.path.join(manager.fonts_folder, "icons", filepath)
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
  return manager.rename_icon(data["old_name"], data["new_name"], data["folder"])


@POST_router.delete("/icons/{folder}/{name}")
def delete_icon(folder: str, name: str):
  manager.delete_icon(name, folder)
  return {"status": "deleted", "folder": folder, "name": name}


@POST_router.get("/config")
def get_config():
  return manager.read_config_csv()


@POST_router.post("/config")
def update_config(data: dict = Body(...)):
  manager.write_config_csv(data)
  manager.generate_fonts()
  return {"status": "ok"}


@GET_router.post("/icon/notfound")
def icon_notfound(data: dict = Body(...)):
  icons = data.get("icons", [])
  if not isinstance(icons, list):
    raise HTTPException(status_code=400, detail="Invalid payload")

  updated = manager.auto_add_icons_from_names(icons)
  return {"status": "ok", "updated": updated}


def add_route(app: FastAPI):
  app.include_router(GET_router)
  app.include_router(POST_router)
