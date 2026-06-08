import os
import csv
import threading
import webbrowser
import urllib.request
from kivy.config import Config

# Configuración de ventana
Config.set('graphics', 'width', '380')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.dropdown import DropDown
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.animation import Animation

Window.clearcolor = (0.90, 0.91, 0.94, 1)

# ---------------------------------------------------------------------------
# CONSTANTES DE DISEÑO  — modificar acá para ajuste global
# ---------------------------------------------------------------------------
ALTO_CAMPO   = 66
ALTO_BOTON   = 59
RADIO_CAMPO  = 18          # bordes redondeados campos
RADIO_BOTON  = 22          # bordes redondeados botones
RADIO_OPCION = 10          # bordes redondeados opciones desplegable
SPACING_UI   = 18          # espaciado vertical entre elementos
PADDING_UI   = [28, 70, 28, 18]

# ---------------------------------------------------------------------------
# CONFIGURACIÓN REMOTA
# ---------------------------------------------------------------------------
GITHUB_RAW    = "https://raw.githubusercontent.com/gabrielschvartz/Colnect-multifiltros/main/"
CSV_FILES     = ["paises.csv", "valores.csv"]
VERSION_FILE  = "version.txt"
VERSION_APP   = "1.0"          # versión actual de esta app
APK_URL       = "https://github.com/gabrielschvartz/Colnect-multifiltros/releases/latest/download/ColnectMultifiltros-release.apk"
TIMEOUT_SEG   = 6


def _leer_versiones_locales():
    """Devuelve (version_csv, version_app) guardadas localmente."""
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            datos = {}
            for linea in f:
                linea = linea.strip()
                if '=' in linea:
                    clave, valor = linea.split('=', 1)
                    datos[clave.strip().upper()] = valor.strip()
        return datos.get('CSV', '0'), datos.get('APP', '0')
    except FileNotFoundError:
        return "0", "0"


def _guardar_version_csv(nueva_version_csv):
    """Guarda la versión CSV manteniendo la versión APP."""
    _, ver_app = _leer_versiones_locales()
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f"CSV={nueva_version_csv}\nAPP={ver_app}\n")


def _descargar_archivo(nombre):
    url = GITHUB_RAW + nombre
    tmp = nombre + ".tmp"
    try:
        urllib.request.urlretrieve(url, tmp)
        os.replace(tmp, nombre)
        return True
    except Exception as e:
        print(f"[Updater] No se pudo descargar {nombre}: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def chequear_actualizaciones(callback_csv, callback_app):
    """
    Corre en hilo secundario. Descarga version.txt remoto y:
    - Llama callback_csv(hubo_actualizacion: bool) si los CSVs cambiaron
    - Llama callback_app(version_nueva: str) si hay nueva versión de la app,
      o callback_app(None) si está al día
    """
    def _tarea():
        try:
            url_ver = GITHUB_RAW + VERSION_FILE
            with urllib.request.urlopen(url_ver, timeout=TIMEOUT_SEG) as resp:
                datos = {}
                for linea in resp.read().decode().splitlines():
                    linea = linea.strip()
                    if '=' in linea:
                        clave, valor = linea.split('=', 1)
                        datos[clave.strip().upper()] = valor.strip()
            ver_csv_remota = datos.get('CSV', '0')
            ver_app_remota = datos.get('APP', '0')
        except Exception as e:
            print(f"[Updater] No se pudo obtener version.txt: {e}")
            Clock.schedule_once(lambda dt: callback_csv(False))
            Clock.schedule_once(lambda dt: callback_app(None))
            return

        ver_csv_local, _ = _leer_versiones_locales()

        # ── Chequeo versión app ──────────────────────────────────────────
        if ver_app_remota != "0" and ver_app_remota != VERSION_APP:
            print(f"[Updater] Nueva versión de app: {ver_app_remota} (actual: {VERSION_APP})")
            Clock.schedule_once(lambda dt: callback_app(ver_app_remota))
        else:
            Clock.schedule_once(lambda dt: callback_app(None))

        # ── Chequeo versión CSVs ─────────────────────────────────────────
        if ver_csv_remota == ver_csv_local:
            print(f"[Updater] CSVs al día (versión {ver_csv_local}).")
            Clock.schedule_once(lambda dt: callback_csv(False))
            return

        print(f"[Updater] Nueva versión CSV {ver_csv_remota}. Descargando…")
        ok = all(_descargar_archivo(f) for f in CSV_FILES)
        if ok:
            _guardar_version_csv(ver_csv_remota)
            print(f"[Updater] CSVs actualizados a versión {ver_csv_remota}.")
        Clock.schedule_once(lambda dt: callback_csv(ok))

    threading.Thread(target=_tarea, daemon=True).start()


# ---------------------------------------------------------------------------
# OPCIÓN DEL MENÚ DESPLEGABLE  — bordes redondeados + divisor completo
# ---------------------------------------------------------------------------
class OpcionMenu(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = [0, 0, 0, 0]
        self.background_normal = ''
        self.color = [0.15, 0.15, 0.20, 1]
        self.bold = True
        self.font_size = '17sp'
        self.halign = 'left'
        self.padding = [18, 0, 18, 0]   # reemplaza padding_x deprecado
        self.size_hint_y = None
        self.height = ALTO_CAMPO

        with self.canvas.before:
            # Fondo con ligero degradado simulado (dos capas)
            self.c_fondo = Color(0.97, 0.97, 1.0, 1)
            self.bg = RoundedRectangle(radius=[RADIO_OPCION])
            # Línea divisora completa (de borde a borde)
            self.c_linea = Color(0.78, 0.80, 0.86, 1)
            self.linea = Line(width=1.0)

        with self.canvas.after:
            # Destello superior (highlight) muy sutil
            Color(1, 1, 1, 0.45)
            self.luz = RoundedRectangle(radius=[RADIO_OPCION, RADIO_OPCION, 0, 0])

        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)

    def update_canvas(self, *args):
        # Fondo: color distinto al presionar
        if self.state == 'down':
            self.c_fondo.rgba = [0.88, 0.92, 1.0, 1]
        else:
            self.c_fondo.rgba = [0.97, 0.97, 1.0, 1]

        self.bg.pos  = self.pos
        self.bg.size = self.size

        # Línea divisora de borde izquierdo a borde derecho
        self.linea.points = [self.x, self.y, self.right, self.y]

        # Destello superior: ocupa toda la anchura, ~30% de la altura
        self.luz.pos  = (self.x, self.y + self.height * 0.68)
        self.luz.size = (self.width, self.height * 0.32)


# ---------------------------------------------------------------------------
# BOTÓN REDONDEADO  — sombra mejorada + efecto 3D más pronunciado
# ---------------------------------------------------------------------------
class BotonRedondeado(Button):
    def __init__(self, color_pastel, **kwargs):
        super().__init__(**kwargs)
        self.background_color = [0, 0, 0, 0]
        self.background_normal = ''
        self.color = [0.1, 0.1, 0.15, 1]
        self.bold = True
        self.font_size = '22sp'
        self.color_pastel = list(color_pastel)
        self.height = ALTO_BOTON
        self.size_hint_y = None

        # Cara oscura (base 3D)
        c_base = [min(c * 0.62, 1) for c in color_pastel] + [1]
        # Cara media (bisel)
        c_mid  = [min(c * 0.82, 1) for c in color_pastel] + [1]

        with self.canvas.before:
            # Capa 1: sombra difusa más grande y desplazada
            Color(0, 0, 0, 0.13)
            self.sombra2 = RoundedRectangle(radius=[RADIO_BOTON + 4])
            # Capa 2: sombra cercana más oscura
            Color(0, 0, 0, 0.18)
            self.sombra1 = RoundedRectangle(radius=[RADIO_BOTON])
            # Capa 3: base 3D (cara inferior)
            self.c_b3d = Color(rgba=c_base)
            self.base_3d = RoundedRectangle(radius=[RADIO_BOTON])
            # Capa 4: bisel medio
            self.c_mid = Color(rgba=c_mid)
            self.bisel = RoundedRectangle(radius=[RADIO_BOTON])
            # Capa 5: cara superior (color real)
            self.c = Color(rgba=list(color_pastel) + [1] if len(color_pastel) == 3 else list(color_pastel))
            self.rect = RoundedRectangle(radius=[RADIO_BOTON])
            # Capa 6: destello superior
            Color(1, 1, 1, 0.55)
            self.luz = RoundedRectangle(radius=[RADIO_BOTON, RADIO_BOTON, 4, 4])

        self.bind(pos=self.update_rect, size=self.update_rect, state=self.update_rect)

    def update_rect(self, *args):
        press = self.state == 'down'
        dy    = -3 if press else 0   # se hunde al presionar

        # Sombra difusa
        self.sombra2.pos  = (self.x + 2, self.y - 9)
        self.sombra2.size = (self.width - 4, self.height + 4)
        # Sombra cercana
        self.sombra1.pos  = (self.x + 1, self.y - 5)
        self.sombra1.size = self.size
        # Base 3D
        self.base_3d.pos  = (self.x, self.y - 4)
        self.base_3d.size = self.size
        # Bisel
        self.bisel.pos    = (self.x, self.y - 2 + dy)
        self.bisel.size   = self.size
        # Cara superior
        self.rect.pos     = (self.x, self.y + dy)
        self.rect.size    = self.size
        # Destello: 38% superior
        self.luz.pos      = (self.x + 2, self.y + dy + self.height * 0.52)
        self.luz.size     = (self.width - 4, self.height * 0.38)

    def on_disabled(self, *args):
        if self.disabled:
            self.c.rgba    = [0.78, 0.78, 0.80, 1]
            self.color     = [0.55, 0.55, 0.55, 1]
        else:
            cp = self.color_pastel
            self.c.rgba    = cp if len(cp) == 4 else cp + [1]
            self.color     = [0.1, 0.1, 0.15, 1]


# ---------------------------------------------------------------------------
# CAMPO BASE  — sombra interior + borde redondeado mejorado
# ---------------------------------------------------------------------------
class CampoBase(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color  = [0, 0, 0, 0]
        self.cursor_color      = [0.2, 0.4, 0.9, 1]
        self.cursor_width      = 2
        self.multiline         = False
        self.foreground_color  = [0.1, 0.1, 0.15, 1]
        self.hint_text_color   = [0.60, 0.62, 0.67, 1]
        self.font_size         = '20sp'
        self.bold              = True
        self.padding           = [18, 16, 18, 16]
        self.size_hint_y       = None
        self.height            = ALTO_CAMPO

        with self.canvas.before:
            # Sombra exterior difusa
            Color(0, 0, 0, 0.10)
            self.sombra = RoundedRectangle(radius=[RADIO_CAMPO + 3])
            # Sombra interior simulada (borde oscuro inferior/derecho)
            Color(0.68, 0.71, 0.76, 1)
            self.s_inner = RoundedRectangle(radius=[RADIO_CAMPO])
            # Destello superior (highlight)
            Color(1, 1, 1, 0.90)
            self.luz = RoundedRectangle(radius=[RADIO_CAMPO])
            # Fondo principal
            self.bg = Color(0.93, 0.95, 0.98, 1)
            self.rect = RoundedRectangle(radius=[RADIO_CAMPO])
            # Borde fino
            self.borde_color = Color(0.68, 0.70, 0.76, 1)
            self.borde = Line(width=1.4)

        self.bind(pos=self.update_rect, size=self.update_rect,
                  focus=self.actualizar_apariencia, text=self.actualizar_apariencia)

    def update_rect(self, *args):
        # Sombra exterior: más grande y desplazada hacia abajo
        self.sombra.pos   = (self.x + 2, self.y - 5)
        self.sombra.size  = (self.width - 4, self.height + 2)
        # Sombra interior: 1px desplazada abajo/derecha
        self.s_inner.pos  = (self.x + 1, self.y - 2)
        self.s_inner.size = self.size
        # Highlight: 1px desplazada arriba/izquierda
        self.luz.pos      = (self.x - 1, self.y + 2)
        self.luz.size     = self.size
        # Fondo exacto
        self.rect.pos     = self.pos
        self.rect.size    = self.size
        # Borde redondeado
        self.borde.rounded_rectangle = (self.x, self.y, self.width, self.height, RADIO_CAMPO)

    def actualizar_apariencia(self, *args):
        if getattr(self, 'es_desplegable', False):
            return
        if self.text:
            self.bg.rgba          = [0.87, 0.96, 0.88, 1]
            self.borde_color.rgba = [0.18, 0.58, 0.22, 1]
        elif self.focus:
            self.bg.rgba          = [0.88, 0.92, 0.99, 1]
            self.borde_color.rgba = [0.30, 0.50, 0.92, 1]
        else:
            self.bg.rgba          = [0.93, 0.95, 0.98, 1]
            self.borde_color.rgba = [0.68, 0.70, 0.76, 1]


# ---------------------------------------------------------------------------
# SELECTOR FILTRABLE
# ---------------------------------------------------------------------------
class SelectorFiltrable(CampoBase):
    def __init__(self, datos_dict, **kwargs):
        super().__init__(**kwargs)
        self.es_desplegable  = True
        self.datos_dict      = datos_dict
        self._seleccionando  = False

        # Dropdown con borde redondeado nativo de Kivy
        self.dropdown = DropDown(max_height=ALTO_CAMPO * 6)
        self.dropdown.bar_width          = 6
        self.dropdown.bar_color          = [0.45, 0.50, 0.70, 0.9]
        self.dropdown.bar_inactive_color = [0.70, 0.72, 0.80, 0.4]
        self.dropdown.scroll_type        = ['bars', 'content']

        # Borde verde pastel alrededor del contenedor del dropdown
        with self.dropdown.canvas.after:
            Color(0.45, 0.80, 0.50, 1)          # verde pastel
            self._dd_border = Line(width=2.0)

        self.dropdown.bind(
            pos=self._actualizar_borde_dd,
            size=self._actualizar_borde_dd,
        )

        self.dropdown.bind(
            on_select=lambda inst, x: self.seleccionar(x),
        )
        self.bind(text=self.al_escribir, focus=self.al_foco)

    def _actualizar_borde_dd(self, *args):
        dd = self.dropdown
        r  = RADIO_OPCION
        self._dd_border.rounded_rectangle = (
            dd.x, dd.y, dd.width, dd.height, r
        )

    def actualizar_apariencia(self, *args):
        texto = self.text.strip().lower()
        if not texto:
            if self.focus:
                self.bg.rgba          = [0.88, 0.92, 0.99, 1]
                self.borde_color.rgba = [0.30, 0.50, 0.92, 1]
            else:
                self.bg.rgba          = [0.93, 0.95, 0.98, 1]
                self.borde_color.rgba = [0.68, 0.70, 0.76, 1]
            return
        coincide = any(texto in k.lower() for k in self.datos_dict)
        if coincide:
            self.bg.rgba          = [0.87, 0.96, 0.88, 1]
            self.borde_color.rgba = [0.18, 0.58, 0.22, 1]
        else:
            self.bg.rgba          = [0.99, 0.87, 0.87, 1]
            self.borde_color.rgba = [0.80, 0.22, 0.22, 1]

    def al_foco(self, inst, foco):
        self.actualizar_apariencia()
        if foco and not self._seleccionando:
            self.filtrar()

    def al_escribir(self, *args):
        self.actualizar_apariencia()
        if not self._seleccionando:
            self.filtrar()

    def filtrar(self, *args):
        self.dropdown.clear_widgets()
        texto = self.text.lower()
        coincidencias = (
            list(self.datos_dict.keys()) if not texto
            else [k for k in self.datos_dict if texto in k.lower()]
        )
        for op in coincidencias[:30]:
            btn = OpcionMenu(text=op)
            btn.bind(on_release=lambda b: self.dropdown.select(b.text))
            self.dropdown.add_widget(btn)
        if coincidencias and self.focus and not self.dropdown.parent:
            self.dropdown.open(self)

    def seleccionar(self, texto):
        self._seleccionando = True
        self.text = texto
        self.actualizar_apariencia()
        Clock.schedule_once(lambda dt: setattr(self, '_seleccionando', False), 0.2)

    def actualizar_datos(self, nuevo_dict):
        self.datos_dict = nuevo_dict
        self.filtrar()


# ---------------------------------------------------------------------------
# LOGO ANIMADO  — fade-in + brillo pulsante + sombra coloreada
# ---------------------------------------------------------------------------
class LogoAnimado(BoxLayout):
    def __init__(self, source, **kwargs):
        super().__init__(size_hint=(1, None), height=195, **kwargs)
        self._pulso_anim = None

        self.img = Image(
            source=source,
            size_hint=(1, 1),
            fit_mode='contain',
            opacity=0,
        )
        self.add_widget(self.img)

        Clock.schedule_once(self._iniciar_efectos, 0.1)

    def _iniciar_efectos(self, dt):
        anim_img = Animation(opacity=1, duration=1.2, t='out_cubic')
        anim_img.bind(on_complete=lambda *a: self._iniciar_pulso())
        anim_img.start(self.img)

    def _iniciar_pulso(self):
        self._pulso_anim = (
            Animation(opacity=0.70, duration=2.0, t='in_out_sine') +
            Animation(opacity=1.00, duration=2.0, t='in_out_sine')
        )
        self._pulso_anim.repeat = True
        self._pulso_anim.start(self.img)



# ---------------------------------------------------------------------------
# DIÁLOGO DE ACTUALIZACIÓN
# ---------------------------------------------------------------------------
class DialogoActualizacion(BoxLayout):
    def __init__(self, version_nueva, callback_actualizar, callback_omitir, **kwargs):
        super().__init__(orientation='vertical', padding=30, spacing=16, **kwargs)

        with self.canvas.before:
            Color(0.15, 0.16, 0.20, 0.92)
            self.fondo = RoundedRectangle(radius=[20])
        self.bind(pos=self._upd, size=self._upd)

        self.add_widget(Label(
            text='🆕  Nueva versión disponible',
            font_size='20sp', bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None, height=40,
        ))
        self.add_widget(Label(
            text=f'Versión {version_nueva} disponible.\n¿Desea actualizar ahora?',
            font_size='16sp',
            color=(0.85, 0.88, 0.95, 1),
            size_hint_y=None, height=55,
            halign='center',
        ))

        fila = BoxLayout(orientation='horizontal', spacing=16, size_hint_y=None, height=ALTO_BOTON)
        btn_si = BotonRedondeado((0.62, 0.86, 0.65), text='Actualizar')
        btn_no = BotonRedondeado((0.75, 0.75, 0.80), text='Ahora no')
        btn_si.bind(on_press=lambda *a: callback_actualizar())
        btn_no.bind(on_press=lambda *a: callback_omitir())
        fila.add_widget(btn_si)
        fila.add_widget(btn_no)
        self.add_widget(fila)

    def _upd(self, *args):
        self.fondo.pos  = self.pos
        self.fondo.size = self.size


# ---------------------------------------------------------------------------
# PANTALLA DE CARGA
# ---------------------------------------------------------------------------
class PantallaCarga(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self._punto  = 0
        self._evento = None

        self.add_widget(Label(size_hint_y=0.35))
        self.lbl_icono = Label(text='🔄', font_size='52sp', size_hint_y=None, height=70)
        self.add_widget(self.lbl_icono)
        self.lbl_estado = Label(
            text='Verificando actualizaciones…',
            font_size='16sp', bold=True,
            color=(0.3, 0.3, 0.35, 1),
            size_hint_y=None, height=40,
        )
        self.add_widget(self.lbl_estado)
        self.lbl_puntos = Label(
            text='', font_size='20sp',
            color=(0.55, 0.55, 0.62, 1),
            size_hint_y=None, height=35,
        )
        self.add_widget(self.lbl_puntos)
        self.add_widget(Label(size_hint_y=0.35))
        self._evento = Clock.schedule_interval(self._animar, 0.45)

    def _animar(self, dt):
        self._punto = (self._punto + 1) % 4
        self.lbl_puntos.text = '[' + '=' * self._punto + '-' * (3 - self._punto) + ']'

    def set_mensaje(self, texto):
        self.lbl_estado.text = texto

    def detener(self):
        if self._evento:
            self._evento.cancel()
            self._evento = None


# ---------------------------------------------------------------------------
# APP PRINCIPAL
# ---------------------------------------------------------------------------
class ColnectApp(App):

    def build(self):
        self.root_layout = BoxLayout(orientation='vertical')
        self._pantalla_carga = PantallaCarga()
        self.root_layout.add_widget(self._pantalla_carga)
        self._csv_listo     = False
        self._app_chequeada = False
        self._version_nueva = None
        chequear_actualizaciones(
            callback_csv=self._on_csv_listo,
            callback_app=self._on_app_chequeada,
        )
        return self.root_layout

    # ------------------------------------------------------------------
    # Callbacks de actualización
    # ------------------------------------------------------------------
    def _on_csv_listo(self, hubo_actualizacion):
        self._csv_listo = True
        self._hubo_actualizacion_csv = hubo_actualizacion
        self._intentar_continuar()

    def _on_app_chequeada(self, version_nueva):
        self._app_chequeada = True
        self._version_nueva = version_nueva
        self._intentar_continuar()

    def _intentar_continuar(self):
        # Espera a que ambos callbacks hayan respondido
        if not (self._csv_listo and self._app_chequeada):
            return

        self._pantalla_carga.detener()
        self.paises  = self._leer_csv('paises.csv')
        self.valores = self._leer_csv('valores.csv')

        if not self.paises or not self.valores:
            self._pantalla_carga.set_mensaje(
                '⚠ No se encontraron archivos CSV.\nAgregá los archivos al directorio.'
            )
            return

        # Si hay nueva versión de la app, mostrar diálogo primero
        if self._version_nueva:
            self._mostrar_dialogo_actualizacion(self._version_nueva)
        elif self._hubo_actualizacion_csv:
            self._pantalla_carga.set_mensaje('✔ Datos actualizados')
            Clock.schedule_once(lambda dt: self._construir_ui(), 0.8)
        else:
            self._construir_ui()

    def _mostrar_dialogo_actualizacion(self, version_nueva):
        self.root_layout.clear_widgets()
        fondo = BoxLayout(orientation='vertical')
        with fondo.canvas.before:
            Color(*Window.clearcolor)
            self._fondo_rect = RoundedRectangle()
        fondo.bind(pos=lambda *a: setattr(self._fondo_rect, 'pos', fondo.pos),
                   size=lambda *a: setattr(self._fondo_rect, 'size', fondo.size))

        fondo.add_widget(Label(size_hint_y=0.3))
        dialogo = DialogoActualizacion(
            version_nueva=version_nueva,
            callback_actualizar=self._descargar_actualizacion,
            callback_omitir=self._construir_ui,
        )
        dialogo.size_hint = (0.9, None)
        dialogo.height = 220
        fondo.add_widget(dialogo)
        fondo.add_widget(Label(size_hint_y=0.3))
        self.root_layout.add_widget(fondo)

    def _descargar_actualizacion(self):
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass
                Intent         = autoclass('android.content.Intent')
                Uri            = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(APK_URL))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
            except Exception as e:
                print(f"[Updater] Error al abrir APK: {e}")
                webbrowser.open(APK_URL, new=0)
        else:
            webbrowser.open(APK_URL, new=0)

    @staticmethod
    def _leer_csv(nombre):
        if not os.path.exists(nombre):
            return {}
        with open(nombre, encoding='utf-8') as f:
            return {
                r[0].strip(): r[1].strip()
                for r in csv.reader(f, delimiter=';')
                if len(r) >= 2
            }

    def _construir_ui(self):
        self.root_layout.clear_widgets()

        layout = BoxLayout(
            orientation='vertical',
            padding=PADDING_UI,
            spacing=SPACING_UI,
        )

        # ── País ──────────────────────────────────────────────────────────
        layout.add_widget(Label(
            text='País', font_size='20sp', bold=True,
            color=(0.20, 0.22, 0.28, 1),
            size_hint_y=None, height=22, halign='left',
        ))
        self.txt_pais = SelectorFiltrable(self.paises, hint_text='Ejemplo: Argentina')
        self.txt_pais.bind(text=self.verificar_estado)
        layout.add_widget(self.txt_pais)

        # ── Valor facial ──────────────────────────────────────────────────
        layout.add_widget(Label(
            text='Valor facial', font_size='20sp', bold=True,
            color=(0.20, 0.22, 0.28, 1),
            size_hint_y=None, height=22, halign='left',
        ))
        self.txt_valor = SelectorFiltrable(self.valores, hint_text='Ejemplo: 1')
        self.txt_valor.bind(text=self.verificar_estado)
        layout.add_widget(self.txt_valor)

        # ── Año + Diámetro (en fila) ──────────────────────────────────────
        fila = BoxLayout(
            orientation='horizontal',
            spacing=16,
            size_hint_y=None,
            height=ALTO_CAMPO + 22 + SPACING_UI,   # campo + etiqueta + spacing igual al layout
        )
        self.txt_ano      = CampoBase(hint_text='Ejemplo: 1998', input_filter='int')
        self.txt_diametro = CampoBase(hint_text='Ejemplo: 22',   input_filter='int')

        for campo, etiqueta in [(self.txt_ano, 'Año'), (self.txt_diametro, 'Diámetro')]:
            campo.bind(text=self.verificar_estado)
            col = BoxLayout(orientation='vertical', spacing=SPACING_UI)
            col.add_widget(Label(
                text=etiqueta, font_size='20sp', bold=True,
                color=(0.20, 0.22, 0.28, 1),
                size_hint_y=None, height=22,
            ))
            col.add_widget(campo)
            fila.add_widget(col)

        layout.add_widget(fila)

        # ── Espaciado extra antes de botones ──────────────────────────────
        layout.add_widget(Label(size_hint_y=None, height=6))

        # ── Botones ───────────────────────────────────────────────────────
        fila_btn = BoxLayout(
            orientation='horizontal',
            spacing=20,
            size_hint_y=None,
            height=ALTO_BOTON,
        )
        self.btn_enviar = BotonRedondeado((0.62, 0.86, 0.65), text='Enviar')
        self.btn_enviar.bind(on_press=self.enviar)
        self.btn_borrar = BotonRedondeado((0.95, 0.60, 0.60), text='Borrar')
        self.btn_borrar.bind(on_press=self.borrar)
        fila_btn.add_widget(self.btn_enviar)
        fila_btn.add_widget(self.btn_borrar)
        layout.add_widget(fila_btn)

        # ── Logo ──────────────────────────────────────────────────────────
        layout.add_widget(LogoAnimado(source='colnect_logo_255.png'))

        # Espaciador flexible: absorbe el espacio sobrante hacia abajo
        layout.add_widget(Label(size_hint_y=1))

        self.root_layout.add_widget(layout)
        self.verificar_estado()

    # ------------------------------------------------------------------
    def verificar_estado(self, *args):
        pais_txt  = self.txt_pais.text
        valor_txt = self.txt_valor.text
        pais_ok   = (pais_txt  == "") or (pais_txt  in self.paises)
        valor_ok  = (valor_txt == "") or (valor_txt in self.valores)
        filtro    = bool(pais_txt or valor_txt or self.txt_ano.text)

        self.btn_enviar.disabled = not (filtro and pais_ok and valor_ok)
        self.btn_borrar.disabled = not any([
            pais_txt, valor_txt, self.txt_ano.text, self.txt_diametro.text
        ])

    def borrar(self, inst):
        self.txt_pais.text = self.txt_valor.text = \
            self.txt_ano.text = self.txt_diametro.text = ""
        self.verificar_estado()

    def _construir_url(self):
        url = (
            "https://colnect.com/es/coins/series"
            if self.txt_ano.text
            else "https://colnect.com/es/coins/list"
        )
        if self.txt_pais.text  in self.paises:  url += f"/country/{self.paises[self.txt_pais.text]}"
        if self.txt_valor.text in self.valores:  url += f"/face_value/{self.valores[self.txt_valor.text]}"
        if self.txt_ano.text:                    url += f"/mint_year/{self.txt_ano.text}"
        if self.txt_diametro.text:               url += f"/width/{self.txt_diametro.text}"
        return url

    def _abrir_android(self, url):
        try:
            from jnius import autoclass
            Intent         = autoclass('android.content.Intent')
            Uri            = autoclass('android.net.Uri')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            # Reutiliza tarea existente en lugar de abrir una nueva
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            # Fallback: navegador estándar si algo falla
            print(f"[Intent] Error al abrir con Intent, usando webbrowser: {e}")
            webbrowser.open(url, new=0)

    def enviar(self, inst):
        from kivy.utils import platform
        url = self._construir_url()
        if platform == 'android':
            self._abrir_android(url)
        else:
            webbrowser.open(url, new=0)


if __name__ == '__main__':
    ColnectApp().run()
